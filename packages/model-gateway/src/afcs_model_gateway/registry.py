from __future__ import annotations

from afcs_model_gateway.provider import LanguageModelProvider


class ModelProviderRegistry:
    """Registry of named LLM providers.

    Providers are registered by a short name (e.g. "mock", "openai", "anthropic")
    and retrieved for use by the language renderer or other components.
    """

    def __init__(self) -> None:
        self._providers: dict[str, LanguageModelProvider] = {}

    def register(self, name: str, provider: LanguageModelProvider) -> None:
        """Register a provider under *name*.

        Raises ``ValueError`` if *name* is already registered.
        """
        if name in self._providers:
            msg = f"Provider '{name}' is already registered"
            raise ValueError(msg)
        self._providers[name] = provider

    def get(self, name: str) -> LanguageModelProvider:
        """Retrieve a registered provider by name.

        Raises ``KeyError`` if *name* is not registered.
        """
        if name not in self._providers:
            msg = f"No provider registered under '{name}'"
            raise KeyError(msg)
        return self._providers[name]

    @property
    def registered_names(self) -> list[str]:
        return list(self._providers.keys())
