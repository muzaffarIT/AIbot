"""Text-chat (LLM) integrations.

The chat stack is deliberately provider-agnostic:

    ChatModel registry  →  adapter ("kie_chat" / "kie_codex")  →  KieChatClient

Today every model routes through KIE.ai, but adding a direct provider later
(Anthropic, OpenAI, OpenRouter…) only means: register a new adapter in
`kie_chat.py`'s dispatch and add rows to `chat_models.CHAT_MODELS`.
"""
