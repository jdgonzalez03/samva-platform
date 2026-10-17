import json

from assistant import ollama
from assistant.constants import (
    DEFAULT_LANGUAGE,
    LANGUAGE_RULE,
    LANGUAGES,
    MAX_TOOL_ROUNDS,
    SYSTEM_PROMPT,
)
from assistant.tools import TOOL_SCHEMAS, run_tool


def _arguments(call):
    arguments = call["function"].get("arguments") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return {}
    return arguments if isinstance(arguments, dict) else {}


def system_prompt(language):
    return f"{SYSTEM_PROMPT}\n{LANGUAGE_RULE.format(language=LANGUAGES[language])}"


def answer(user, history, language=DEFAULT_LANGUAGE):
    """Reply to the last user message of `history`, letting the model call the tools.

    Returns `(reply, tool_calls)`, where `tool_calls` lists every tool the model ran with its
    arguments and result, in order, so the client can show where the answer came from.
    """
    messages = [{"role": "system", "content": system_prompt(language)}, *history]
    tool_calls = []

    for _ in range(MAX_TOOL_ROUNDS):
        message = ollama.chat(messages, TOOL_SCHEMAS)
        calls = message.get("tool_calls") or []
        if not calls:
            return message.get("content", "").strip(), tool_calls

        messages.append(message)
        for call in calls:
            name = call["function"]["name"]
            arguments = _arguments(call)
            result = run_tool(user, name, arguments)
            tool_calls.append({"name": name, "arguments": arguments, "result": result})
            messages.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    message = ollama.chat(messages)
    return message.get("content", "").strip(), tool_calls
