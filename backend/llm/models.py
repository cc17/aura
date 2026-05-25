from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str


AVAILABLE_MODELS: list[ModelInfo] = [
    ModelInfo(id="openai/deepseek-v3-2-251201", name="DeepSeek V3", provider="ByteDance"),
]
