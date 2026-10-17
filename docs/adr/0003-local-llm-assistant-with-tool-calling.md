# ADR 0003: A chat assistant on a local LLM that answers through tool calls

- **Status**: Accepted
- **Date**: 2026-10-06
- **Scope**: `backend/assistant/`, `frontend/layers/assistant/`, the `ollama` service in `backend/docker-compose.yml` and `docker-compose.yml`

## Context

The platform's only AI technique so far is the fuzzy-logic irrigation model (`predictions`). Getting an answer out of it — or out of any other view — means knowing where it lives: pick the farm, open "Predicciones", choose the plot, press calculate. Farmers ask simpler questions: *how many farms do I have?*, *what is the irrigation prescription for Lote El Rodeo?*, *is any sensor down?*.

A chat assistant fits those questions, with three constraints:

- **The data is the farmer's.** Readings, plots and predictions must not leave the server for a third-party API, and the assistant must only see what the logged-in user owns.
- **It must not invent figures.** An irrigation time or a sensor status has to come from the same code the views use, never from the model's weights.
- **Light enough for the planned deployment** (a Raspberry Pi 5 with 8 GB RAM, see ADR 0002) and quick to build.

## Decision

A new Django app, `assistant`, and a new Nuxt layer, `assistant`, both independent of `predictions` (the app only *calls* its `create_irrigation_prediction`).

```
Nuxt /dashboard/assistant ──POST /api/assistant/chat/ {messages}──▶ AssistantChatAPIView
                                                                     │  assistant/utils.py: answer()
                                                                     ▼
                             ┌───────────── Ollama /api/chat (llama3.2:3b, tools) ◀──┐
                             │ tool_calls                                              │ role: tool
                             ▼                                                         │
                  assistant/tools.py: run_tool(user, name, args) ──────────────────────┘
                  list_farms · list_plots · get_plot_conditions · list_sensors
                  get_latest_irrigation · calculate_irrigation
```

1. **Ollama serves the model, in its own compose service.** `ollama/ollama` with a named volume for the weights; the model is pulled once with `make assistant-model`. `OLLAMA_URL` and `OLLAMA_MODEL` are settings, so the backend can point at a native Ollama (GPU) or swap the model without code changes.
2. **`llama3.2:3b` by default.** It supports tool calling, weighs ~2 GB quantised and answers in Spanish. Smaller models (1B) pick the wrong tool or invent arguments too often; 7–8B ones do not fit comfortably next to PostGIS on the Pi.
3. **Facts only through tools.** The system prompt forbids answering farm questions from memory. Every tool runs as the requesting user: querysets go through `farm__owner__user=user`, so another farmer's plot is "not found" — the same rule as `get_owned_or_404`. Tools reuse the view code (`build_conditions`, `FieldSensorSerializer`, `create_irrigation_prediction`), so a chat answer and a page show the same number.
4. **Names, not ids.** Small models copy what the user typed ("el rodeo"), so a plot/farm argument is matched by id, exact name or a unique partial name; an ambiguous or unknown name returns an `error` listing the options, which the model reads and explains.
5. **Tool failures are data, not exceptions.** Unknown tools, missing or invented arguments and domain errors (no recent readings) become `{"error": …}` for the model. Only an unreachable model or a missing download is an HTTP error (503).
6. **A bounded loop.** After `MAX_TOOL_ROUNDS` rounds of tool calls the model is asked once more *without* tools, which forces a text reply.
7. **Stateless backend.** The client sends the whole conversation each turn; the server trims it to the last `MAX_HISTORY_MESSAGES` and stores nothing. Leaving the page or logging out starts a fresh chat. The client also sends the interface language, and the system prompt states it as the reply language: left to infer it from the question, the model followed the Spanish names in the tool results and answered an English question in Spanish.
8. **Transparency in the UI.** The response lists every tool the model ran with its arguments and result; the chat shows them as collapsible rows ("Consultó tus fincas"), and a write tool (`calculate_irrigation`) invalidates the Vue Query cache so the other views show the new prescription.
9. **No new Python dependency.** The client is one `requests.post` to `/api/chat` (`assistant/ollama.py`); `requests` is already pinned.

## Alternatives considered

- **A hosted LLM API (OpenAI, Anthropic, Gemini).** Better answers and faster, but sends farm data to a third party, needs an API key and internet for every question, and has a per-token cost.
- **LangChain / LlamaIndex agents.** Standard agent loop, but a large dependency tree for six tools and one loop of ~30 lines.
- **The official `ollama` Python client.** Typed responses, but adds `httpx` and `pydantic` for a single endpoint.
- **Streaming tokens to the browser (SSE).** Better perceived latency, but tool calls arrive mid-stream and the dev/prod stacks would need streaming-aware proxies; left for later.
- **Persisting conversations.** Useful for history and evaluation, but needs a model, retention rules and privacy decisions; not needed for a first version.

## Consequences

- One new service (`ollama`, ~2 GB of weights in a volume, ~3 GB RAM while loaded; `OLLAMA_KEEP_ALIVE` unloads it after 30 min idle).
- Latency depends on the hardware. Inside Docker the model runs on CPU only: on the development Mac (Apple Silicon, under memory pressure) one model call took 28–40 s in the container and 0.5–3.3 s on a native Ollama using the GPU — so on macOS point `OLLAMA_URL` at `http://host.docker.internal:11434`. A turn with one tool call makes two model calls. gunicorn (`--timeout 180`), nginx (`proxy_read_timeout 180s` on `/api/assistant/`) and the client timeout (`OLLAMA_TIMEOUT_SECONDS`) are raised accordingly, and the endpoint is throttled per user (`assistant_chat`).
- A 3B model still misreads questions now and then; the page says so, and every figure it gives can be checked in the tool rows.
- Adding a capability means adding a function and its JSON schema in `assistant/tools.py` (a test pins that both lists match) and a label in the layer's locale files.
