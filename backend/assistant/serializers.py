from rest_framework import serializers

from assistant.constants import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    MAX_HISTORY_MESSAGES,
    MAX_MESSAGE_LENGTH,
)


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=MAX_MESSAGE_LENGTH, trim_whitespace=True)


class ChatRequestSerializer(serializers.Serializer):
    messages = ChatMessageSerializer(many=True, allow_empty=False)
    language = serializers.ChoiceField(choices=list(LANGUAGES), default=DEFAULT_LANGUAGE)

    def validate_messages(self, messages):
        if messages[-1]["role"] != "user":
            raise serializers.ValidationError("The last message must come from the user.")
        # The client sends the whole conversation; only its tail reaches the model so a long
        # chat cannot outgrow the model's context window.
        return messages[-MAX_HISTORY_MESSAGES:]


class ToolCallSerializer(serializers.Serializer):
    name = serializers.CharField()
    arguments = serializers.DictField()
    result = serializers.JSONField()


class ChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField(allow_blank=True)
    tool_calls = ToolCallSerializer(many=True)


class AssistantUnavailableSerializer(serializers.Serializer):
    detail = serializers.CharField()
