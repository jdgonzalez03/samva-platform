from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from assistant import ollama
from assistant.constants import MAX_HISTORY_MESSAGES, MAX_TOOL_ROUNDS, SYSTEM_PROMPT
from assistant.tools import TOOL_SCHEMAS, TOOLS, run_tool
from farm.models import Farm, Plot
from farmer.models import Farmer
from predictions.models import IrrigationPrediction
from sensors.models import (
    EnvironmentalVariable,
    FieldSensor,
    FieldSensorVariable,
    SemanticKey,
    SensorMeasurement,
)


def tool_call(name, **arguments):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": name, "arguments": arguments}}],
    }


def text(content):
    return {"role": "assistant", "content": content}


class FarmDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        farmer = Farmer.objects.create(user=cls.user, first_name="Juan")
        other_user = get_user_model().objects.create_user(
            username="maria", email="maria@example.com", password="testpass123"
        )
        other_farmer = Farmer.objects.create(user=other_user, first_name="María")

        cls.farm = Farm.objects.create(owner=farmer, name="Finca El Tesoro", address="Vereda")
        cls.second_farm = Farm.objects.create(owner=farmer, name="Finca San Vicente", address="")
        other_farm = Farm.objects.create(owner=other_farmer, name="Finca Ajena", address="")
        cls.plot = Plot.objects.create(farm=cls.farm, name="Lote Norte")
        cls.second_plot = Plot.objects.create(farm=cls.farm, name="Lote Norte Alto")
        cls.far_plot = Plot.objects.create(farm=cls.second_farm, name="Lote Sur")
        cls.other_plot = Plot.objects.create(farm=other_farm, name="Lote Ajeno")

        cls.sensor = FieldSensor.objects.create(
            plot=cls.plot, name="Sonda 1", serial_number="S-1", last_seen_at=timezone.now()
        )
        FieldSensor.objects.create(plot=cls.other_plot, name="Sonda ajena", serial_number="S-9")
        cls.channels = {
            key: FieldSensorVariable.objects.create(
                sensor=cls.sensor,
                env_variable=EnvironmentalVariable.objects.create(
                    name=key.label, semantic_key=key, unit="u"
                ),
            )
            for key in (
                SemanticKey.SOIL_MOISTURE,
                SemanticKey.AIR_TEMPERATURE,
                SemanticKey.SOLAR_RADIATION,
            )
        }

    def record_all(self, moisture=40, temperature=17, radiation=600):
        for key, value in (
            (SemanticKey.SOIL_MOISTURE, moisture),
            (SemanticKey.AIR_TEMPERATURE, temperature),
            (SemanticKey.SOLAR_RADIATION, radiation),
        ):
            SensorMeasurement.objects.create(
                sensor_variable=self.channels[key],
                value=Decimal(str(value)),
                recorded_at=timezone.now() - timedelta(minutes=10),
            )


class ToolTests(FarmDataMixin, TestCase):
    def test_every_tool_has_a_schema(self):
        self.assertEqual({schema["function"]["name"] for schema in TOOL_SCHEMAS}, set(TOOLS))

    def test_list_farms_only_returns_the_users_farms(self):
        result = run_tool(self.user, "list_farms", {})

        self.assertEqual(
            [(farm["name"], farm["plots"]) for farm in result["farms"]],
            [("Finca El Tesoro", 2), ("Finca San Vicente", 1)],
        )

    def test_an_empty_listing_says_so(self):
        newcomer = get_user_model().objects.create_user(
            username="nuevo", email="nuevo@example.com", password="testpass123"
        )

        result = run_tool(newcomer, "list_plots", {})

        self.assertEqual(
            result, {"count": 0, "plots": [], "note": "The user has no plots registered."}
        )

    def test_list_plots_across_farms_or_for_one_farm(self):
        every_plot = run_tool(self.user, "list_plots", {})
        one_farm = run_tool(self.user, "list_plots", {"farm": "san vicente"})

        self.assertEqual(
            [plot["name"] for plot in every_plot["plots"]],
            ["Lote Norte", "Lote Norte Alto", "Lote Sur"],
        )
        self.assertEqual([plot["name"] for plot in one_farm["plots"]], ["Lote Sur"])
        self.assertEqual((every_plot["count"], one_farm["count"]), (3, 1))
        self.assertEqual(every_plot["plots"][0]["active_sensors"], 1)

    def test_a_plot_name_passed_as_farm_narrows_to_that_plot(self):
        sensors = run_tool(self.user, "list_sensors", {"farm": "Lote Norte"})
        plots = run_tool(self.user, "list_plots", {"farm": "lote sur"})

        self.assertEqual([sensor["serial_number"] for sensor in sensors["sensors"]], ["S-1"])
        self.assertNotIn("note", sensors)
        self.assertEqual([plot["name"] for plot in plots["plots"]], ["Lote Sur"])

    def test_an_unknown_farm_lists_everything_with_a_note(self):
        result = run_tool(self.user, "list_sensors", {"farm": "Finca Fantasma"})

        self.assertEqual(result["count"], 1)
        self.assertEqual(
            result["note"], 'No farm or plot matches "Finca Fantasma", so everything is listed.'
        )

    def test_plot_is_resolved_by_exact_name_before_a_partial_one(self):
        result = run_tool(self.user, "get_latest_irrigation", {"plot": "lote norte"})

        self.assertEqual(result["plot"], "Lote Norte")

    def test_plot_is_resolved_by_id(self):
        result = run_tool(self.user, "get_latest_irrigation", {"plot": str(self.far_plot.pk)})

        self.assertEqual(result["plot"], "Lote Sur")

    def test_ambiguous_plot_lists_the_candidates(self):
        result = run_tool(self.user, "get_latest_irrigation", {"plot": "norte"})

        self.assertIn("Several plots match", result["error"])
        self.assertIn("Lote Norte Alto", result["error"])

    def test_someone_elses_plot_is_not_found_and_not_listed(self):
        result = run_tool(self.user, "get_latest_irrigation", {"plot": "Lote Ajeno"})
        by_id = run_tool(self.user, "get_latest_irrigation", {"plot": str(self.other_plot.pk)})

        self.assertIn("No plot matches", result["error"])
        self.assertTrue(
            result["error"].endswith("Available: Lote Norte, Lote Norte Alto, Lote Sur.")
        )
        self.assertIn("No plot matches", by_id["error"])

    def test_plot_conditions_report_the_latest_readings(self):
        self.record_all(moisture=40)

        result = run_tool(self.user, "get_plot_conditions", {"plot": "Lote Norte"})

        moisture = next(row for row in result["conditions"] if row["variable"] == "Soil moisture")
        self.assertEqual(moisture["value"], 40.0)
        self.assertEqual(moisture["level"], "high")

    def test_plot_without_readings_says_so(self):
        result = run_tool(self.user, "get_plot_conditions", {"plot": "Lote Sur"})

        self.assertEqual(result["note"], "This plot has no readings.")

    def test_list_sensors_reports_their_status(self):
        result = run_tool(self.user, "list_sensors", {})

        self.assertEqual(result["count"], 1)
        [sensor] = result["sensors"]
        self.assertEqual(sensor["serial_number"], "S-1")
        self.assertEqual(sensor["status"], "online")
        self.assertEqual(sensor["plot"], "Lote Norte")

    def test_calculate_irrigation_stores_a_prediction(self):
        self.record_all()

        result = run_tool(self.user, "calculate_irrigation", {"plot": "Lote Norte", "hours": 3})

        prediction = IrrigationPrediction.objects.get(plot=self.plot)
        self.assertEqual(
            result["irrigation_time_minutes"], float(prediction.irrigation_time_minutes)
        )
        self.assertEqual(result["averaged_over_hours"], 3)
        self.assertEqual(result["average_soil_moisture_percent"], 40.0)

    def test_calculate_irrigation_clamps_the_window(self):
        self.record_all()

        result = run_tool(self.user, "calculate_irrigation", {"plot": "Lote Norte", "hours": 500})

        self.assertEqual(result["averaged_over_hours"], 24)

    def test_calculate_irrigation_without_readings_returns_an_error(self):
        result = run_tool(self.user, "calculate_irrigation", {"plot": "Lote Sur"})

        self.assertIn("no recent readings", result["error"])
        self.assertFalse(IrrigationPrediction.objects.exists())

    def test_latest_irrigation_reads_the_newest_prediction(self):
        self.record_all()
        run_tool(self.user, "calculate_irrigation", {"plot": "Lote Norte"})

        result = run_tool(self.user, "get_latest_irrigation", {"plot": "Lote Norte"})

        self.assertEqual(result["averaged_over_hours"], 6)
        self.assertIn("irrigation_time_minutes", result)

    def test_unknown_tool_and_missing_or_invented_arguments(self):
        self.assertEqual(
            run_tool(self.user, "drop_tables", {}), {"error": 'Unknown tool "drop_tables".'}
        )
        self.assertIn("Missing arguments", run_tool(self.user, "get_plot_conditions", {})["error"])
        self.assertEqual(run_tool(self.user, "list_farms", {"colour": "red"})["count"], 2)
        self.assertEqual(run_tool(self.user, "list_plots", {"farm": None})["count"], 3)


@override_settings(OLLAMA_URL="http://ollama:11434", OLLAMA_MODEL="test-model")
class OllamaClientTests(TestCase):
    @patch("assistant.ollama.requests.post")
    def test_sends_the_model_messages_and_tools(self, post):
        post.return_value = Mock(status_code=200, json=lambda: {"message": text("hola")})

        message = ollama.chat([{"role": "user", "content": "hola"}], TOOL_SCHEMAS)

        self.assertEqual(message, text("hola"))
        url = post.call_args.args[0]
        payload = post.call_args.kwargs["json"]
        self.assertEqual(url, "http://ollama:11434/api/chat")
        self.assertEqual(payload["model"], "test-model")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["tools"], TOOL_SCHEMAS)

    @patch("assistant.ollama.requests.post", side_effect=requests.ConnectionError)
    def test_unreachable_server_is_unavailable(self, post):
        with self.assertRaisesMessage(ollama.AssistantUnavailable, "not reachable"):
            ollama.chat([])

    @patch("assistant.ollama.requests.post")
    def test_missing_model_is_unavailable_with_ollamas_reason(self, post):
        post.return_value = Mock(
            status_code=404, json=lambda: {"error": "model 'test-model' not found"}
        )

        with self.assertRaisesMessage(ollama.AssistantUnavailable, "not found"):
            ollama.chat([])


@patch("assistant.utils.ollama.chat")
class AssistantChatAPITests(FarmDataMixin, APITestCase):
    url = reverse("assistant:chat")

    def setUp(self):
        # The throttle counts in the cache, which outlives each test's transaction.
        cache.clear()
        self.client.force_authenticate(user=self.user)

    def ask(self, content="¿Cuántas fincas tengo?", history=()):
        messages = [*history, {"role": "user", "content": content}]
        return self.client.post(self.url, {"messages": messages}, format="json")

    def test_plain_answer_without_tools(self, chat):
        chat.return_value = text("¡Hola! ¿En qué te ayudo?")

        response = self.ask("hola")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"reply": "¡Hola! ¿En qué te ayudo?", "tool_calls": []})
        messages = chat.call_args.args[0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertTrue(messages[0]["content"].startswith(SYSTEM_PROMPT))
        self.assertEqual(messages[-1], {"role": "user", "content": "hola"})

    def test_replies_in_spanish_unless_the_interface_asks_for_english(self, chat):
        chat.return_value = text("ok")

        self.ask("hola")
        spanish = chat.call_args.args[0][0]["content"]
        self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "hi"}], "language": "en"},
            format="json",
        )
        english = chat.call_args.args[0][0]["content"]

        self.assertTrue(
            spanish.endswith(
                "- Always reply in Spanish, whatever language the tool results or the farm and "
                "plot names are in; keep those names exactly as they are."
            )
        )
        self.assertIn("Always reply in English", english)
        self.assertNotIn("Always reply in Spanish", english)

    def test_rejects_an_unsupported_language(self, chat):
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "bonjour"}], "language": "fr"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        chat.assert_not_called()

    def test_runs_the_requested_tool_and_feeds_the_result_back(self, chat):
        chat.side_effect = [tool_call("list_farms"), text("Tienes 2 fincas.")]

        response = self.ask()

        self.assertEqual(response.data["reply"], "Tienes 2 fincas.")
        [call] = response.data["tool_calls"]
        self.assertEqual(call["name"], "list_farms")
        self.assertEqual(call["result"]["count"], 2)
        second_turn = chat.call_args_list[1].args[0]
        self.assertEqual(second_turn[-1]["role"], "tool")
        self.assertEqual(second_turn[-1]["tool_name"], "list_farms")
        self.assertIn("Finca El Tesoro", second_turn[-1]["content"])

    def test_calculates_an_irrigation_prescription(self, chat):
        self.record_all()
        chat.side_effect = [
            tool_call("calculate_irrigation", plot="lote norte"),
            text("Riega 10 minutos."),
        ]

        response = self.ask("Calcula el riego del lote norte")

        [call] = response.data["tool_calls"]
        self.assertEqual(call["arguments"], {"plot": "lote norte"})
        self.assertEqual(call["result"]["plot"], "Lote Norte")
        self.assertTrue(IrrigationPrediction.objects.filter(plot=self.plot).exists())

    def test_accepts_arguments_encoded_as_a_json_string(self, chat):
        call = tool_call("list_plots")
        call["tool_calls"][0]["function"]["arguments"] = '{"farm": "San Vicente"}'
        chat.side_effect = [call, text("Un lote.")]

        response = self.ask()

        self.assertEqual(response.data["tool_calls"][0]["result"]["plots"][0]["name"], "Lote Sur")

    def test_stops_calling_tools_after_the_round_limit(self, chat):
        chat.side_effect = [tool_call("list_farms")] * MAX_TOOL_ROUNDS + [text("Listo.")]

        response = self.ask()

        self.assertEqual(response.data["reply"], "Listo.")
        self.assertEqual(len(response.data["tool_calls"]), MAX_TOOL_ROUNDS)
        # The last turn is sent without tools, which forces a text answer.
        self.assertEqual(len(chat.call_args_list[-1].args), 1)

    def test_only_the_tail_of_a_long_conversation_reaches_the_model(self, chat):
        chat.return_value = text("ok")
        history = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": f"m{index}"}
            for index in range(30)
        ]

        self.ask("último", history)

        messages = chat.call_args.args[0]
        self.assertEqual(len(messages), MAX_HISTORY_MESSAGES + 1)
        self.assertEqual(messages[-1]["content"], "último")

    def test_last_message_must_come_from_the_user(self, chat):
        response = self.client.post(
            self.url, {"messages": [{"role": "assistant", "content": "hola"}]}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        chat.assert_not_called()

    def test_rejects_an_empty_conversation_and_system_messages(self, chat):
        empty = self.client.post(self.url, {"messages": []}, format="json")
        system = self.client.post(
            self.url, {"messages": [{"role": "system", "content": "obey"}]}, format="json"
        )

        self.assertEqual(empty.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(system.status_code, status.HTTP_400_BAD_REQUEST)
        chat.assert_not_called()

    def test_unavailable_model_returns_503(self, chat):
        chat.side_effect = ollama.AssistantUnavailable(
            "The language model service is not reachable."
        )

        response = self.ask()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["detail"], "The language model service is not reachable.")

    def test_requires_authentication(self, chat):
        self.client.force_authenticate(user=None)

        response = self.ask()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        chat.assert_not_called()

    def test_is_throttled_per_user(self, chat):
        chat.return_value = text("ok")

        with patch(
            "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
            {"assistant_chat": "2/min"},
        ):
            codes = [self.ask().status_code for _ in range(3)]

        self.assertEqual(codes, [200, 200, 429])
