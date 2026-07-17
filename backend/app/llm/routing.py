from app.core.config import ProviderType, settings
from app.llm.base import LLMProvider
from app.llm.providers.azure_openai import AzureOpenAIProvider
from app.llm.providers.local import LocalProvider
from app.llm.providers.openai import OpenAIProvider


def build_provider() -> LLMProvider:
    if settings.llm_provider is ProviderType.OPENAI:
        return OpenAIProvider()
    if settings.llm_provider is ProviderType.AZURE_OPENAI:
        return AzureOpenAIProvider()
    return LocalProvider()
