"""
LLM provider abstraction for easy switching between Ollama and OpenAI.
"""

from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from config import settings


def get_llm(
    temperature: float = 0.7,
    model: Optional[str] = None,
    streaming: bool = False
) -> BaseChatModel:
    """
    Get a chat model based on configuration.

    Args:
        temperature: Model temperature (0-1)
        model: Override default model from config
        streaming: Enable streaming responses

    Returns:
        Configured chat model instance
    """
    if settings.llm_provider == "ollama":
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=model or settings.ollama_model,
            temperature=temperature,
            streaming=streaming,
        )
    elif settings.llm_provider == "openai":
        return ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=model or settings.openai_model,
            temperature=temperature,
            streaming=streaming,
            # Ensure tool responses are properly formatted for strict OpenAI API compatibility (e.g., DeepSeek)
            model_kwargs={"tool_choice": "auto"},
        )
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def get_routing_llm() -> BaseChatModel:
    """
    Get a fast, lightweight model for routing decisions.
    Uses the configured model but with lower temperature.
    """
    return get_llm(temperature=0.3, streaming=False)


def get_agent_llm(temperature: float = 0.7) -> BaseChatModel:
    """
    Get a model for agent reasoning and responses.
    Uses the configured model with specified temperature.
    """
    return get_llm(temperature=temperature, streaming=False)
