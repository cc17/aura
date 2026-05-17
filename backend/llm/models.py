from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str


AVAILABLE_MODELS: list[ModelInfo] = [
    ModelInfo(id="openai/doubao-1-5-pro-32k-250115", name="Doubao 1.5 Pro 32K", provider="ByteDance"),
]
