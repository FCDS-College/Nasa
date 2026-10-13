"""vLLM on the L40S (or any GPU host on the same network): OpenAI-compatible, structured outputs."""
from ai.providers.local.openai_compatible import OpenAICompatibleProvider


class VllmProvider(OpenAICompatibleProvider):
    runtime = "vllm"

    def __init__(self, *, base_url: str, model: str, **kwargs) -> None:
        super().__init__(base_url=base_url, model=model, name=kwargs.pop("name", "vllm"), **kwargs)
