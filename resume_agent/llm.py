from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from resume_agent.config import settings


@lru_cache(maxsize=4)
def get_chat_model(provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """Provider-agnostic LangChain ChatModel factory.

    Defaults come from Settings/env so the backend can be swapped without code changes.
    """
    provider = provider or settings.llm_provider
    model = model or settings.llm_model

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, temperature=0)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=0)

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}")
