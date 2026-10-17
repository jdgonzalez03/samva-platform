from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from assistant.ollama import AssistantUnavailable
from assistant.serializers import (
    AssistantUnavailableSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
)
from assistant.utils import answer


class AssistantChatAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "assistant_chat"

    @extend_schema(
        request=ChatRequestSerializer,
        responses={
            200: ChatResponseSerializer,
            503: OpenApiResponse(AssistantUnavailableSerializer),
        },
    )
    def post(self, request):
        params = ChatRequestSerializer(data=request.data)
        params.is_valid(raise_exception=True)

        try:
            reply, tool_calls = answer(
                request.user,
                params.validated_data["messages"],
                params.validated_data["language"],
            )
        except AssistantUnavailable as error:
            return Response({"detail": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(ChatResponseSerializer({"reply": reply, "tool_calls": tool_calls}).data)
