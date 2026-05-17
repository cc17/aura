from backend.llm.models import AVAILABLE_MODELS


def test_available_models_not_empty():
    assert len(AVAILABLE_MODELS) > 0


def test_model_has_required_fields():
    for model in AVAILABLE_MODELS:
        assert model.id
        assert model.name
        assert model.provider
