"""Province-to-gaokao-model mapping.

China has three gaokao models with different subject type systems:
- 3+3:     综合 (single type, auto-fill)
- 3+1+2:   物理类 / 历史类 (must ask student)
- 传统:     理科 / 文科 (must ask student)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GaokaoModel:
    name: str                          # "3+3", "3+1+2", "传统"
    subject_types: tuple[str, ...]     # valid subject_type values
    default: str | None                # auto-fill value if only one option


_3_PLUS_3 = GaokaoModel(
    name="3+3（新高考综合改革）",
    subject_types=("综合",),
    default="综合",
)

_3_PLUS_1_PLUS_2 = GaokaoModel(
    name="3+1+2（新高考）",
    subject_types=("物理类", "历史类"),
    default=None,
)

_TRADITIONAL = GaokaoModel(
    name="传统文理分科",
    subject_types=("理科", "文科"),
    default=None,
)

# Mapping: province name → GaokaoModel
PROVINCE_MODELS: dict[str, GaokaoModel] = {
    # ── 3+3 ──
    "上海": _3_PLUS_3,
    "浙江": _3_PLUS_3,
    "北京": _3_PLUS_3,
    "天津": _3_PLUS_3,
    "山东": _3_PLUS_3,
    "海南": _3_PLUS_3,
    # ── 3+1+2 ──
    "河北": _3_PLUS_1_PLUS_2,
    "辽宁": _3_PLUS_1_PLUS_2,
    "江苏": _3_PLUS_1_PLUS_2,
    "福建": _3_PLUS_1_PLUS_2,
    "湖北": _3_PLUS_1_PLUS_2,
    "湖南": _3_PLUS_1_PLUS_2,
    "广东": _3_PLUS_1_PLUS_2,
    "重庆": _3_PLUS_1_PLUS_2,
    "黑龙江": _3_PLUS_1_PLUS_2,
    "甘肃": _3_PLUS_1_PLUS_2,
    "吉林": _3_PLUS_1_PLUS_2,
    "安徽": _3_PLUS_1_PLUS_2,
    "江西": _3_PLUS_1_PLUS_2,
    "贵州": _3_PLUS_1_PLUS_2,
    "广西": _3_PLUS_1_PLUS_2,
    # ── 传统文理分科 ──
    "河南": _TRADITIONAL,
    "四川": _TRADITIONAL,
    "云南": _TRADITIONAL,
    "山西": _TRADITIONAL,
    "陕西": _TRADITIONAL,
    "内蒙古": _TRADITIONAL,
    "宁夏": _TRADITIONAL,
    "青海": _TRADITIONAL,
    "西藏": _TRADITIONAL,
    "新疆": _TRADITIONAL,
}


def get_gaokao_model(province: str) -> GaokaoModel | None:
    """Return the gaokao model for a province, or None if unknown."""
    return PROVINCE_MODELS.get(province)


def infer_subject_type(province: str, subject_type: str | None = None) -> str | None:
    """Try to determine subject_type for a province.

    - If subject_type is already provided and valid, return it as-is.
    - If the province uses 3+3 (only one option), auto-fill.
    - Otherwise return None (caller must ask the student).
    """
    model = PROVINCE_MODELS.get(province)
    if model is None:
        return subject_type or None

    # Already provided — validate
    if subject_type:
        if subject_type in model.subject_types:
            return subject_type
        # Remap legacy values: 理科/文科 → 物理类/历史类 for 3+1+2
        if model.name.startswith("3+1+2"):
            legacy_map = {"理科": "物理类", "文科": "历史类"}
            return legacy_map.get(subject_type, subject_type)
        return subject_type

    # Not provided — auto-fill if only one option
    return model.default
