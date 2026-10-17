import requests
from django.conf import settings


class AssistantUnavailable(Exception):
    pass


def chat(messages, tools=None):
    """Send one non-streaming chat turn to Ollama and return its `message`."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        # Low temperature keeps tool selection and argument copying predictable.
        "options": {"temperature": 0.2},
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
    }
    if tools:
        payload["tools"] = tools

    try:
        response = requests.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json=payload,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise AssistantUnavailable("The language model service is not reachable.") from error

    if response.status_code != 200:
        # Ollama answers a model that was never pulled with 404 and `{"error": ...}`.
        raise AssistantUnavailable(_error_detail(response))

    return response.json()["message"]


def _error_detail(response):
    try:
        return response.json().get("error") or response.text
    except ValueError:
        return response.text
