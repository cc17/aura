"""Gaokao data layer — score-to-rank, universities, requirements, and province models."""

from backend.data.gaokao.province_models import (
    PROVINCE_MODELS,
    GaokaoModel,
    get_gaokao_model,
    infer_subject_type,
)
from backend.data.gaokao.requirement_data import (
    AdmissionRequirement,
    get_requirements,
)
from backend.data.gaokao.score_rank_table import (
    CURRENT_YEAR,
    REFERENCE_YEARS,
    SUPPORTED_PROVINCES,
    get_rank_for_score,
    get_score_for_rank,
)
from backend.data.gaokao.university_data import (
    AdmissionRecord,
    find_schools_by_score_range,
)

__all__ = [
    "CURRENT_YEAR",
    "GaokaoModel",
    "PROVINCE_MODELS",
    "REFERENCE_YEARS",
    "SUPPORTED_PROVINCES",
    "AdmissionRecord",
    "AdmissionRequirement",
    "find_schools_by_score_range",
    "get_gaokao_model",
    "get_rank_for_score",
    "get_requirements",
    "get_score_for_rank",
    "infer_subject_type",
]
