from django.urls import path

from assistant.api import AssistantChatAPIView

app_name = "assistant"

urlpatterns = [
    path("chat/", AssistantChatAPIView.as_view(), name="chat"),
]
