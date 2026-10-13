"""llama.cpp ``llama-server``: OpenAI-compatible; ``response_format`` json_schema maps to a grammar."""
from ai.providers.local.openai_compatible import OpenAICompatibleProvider


class LlamaCppProvider(OpenAICompatibleProvider):
    runtime = "llama.cpp"

    def __init__(self, *, base_url: str, model: str, **kwargs) -> None:
        super().__init__(base_url=base_url, model=model, name=kwargs.pop("name", "llamacpp"), **kwargs)
