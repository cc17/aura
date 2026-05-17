"""Special admission requirements for Shanghai universities (mock data).

Covers: vision, subject score, language, gender, physical exam, and subject selection.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdmissionRequirement:
    university: str
    major: str
    requirement_type: str  # "vision", "subject_score", "language", "gender", "physical", "subject_selection"
    description: str
    details: str


_REQUIREMENTS: list[AdmissionRequirement] = [
    # Vision requirements
    AdmissionRequirement(
        "上海交通大学", "临床医学", "vision",
        "色觉要求", "色盲、色弱考生不予录取",
    ),
    AdmissionRequirement(
        "上海中医药大学", "中医学", "vision",
        "色觉要求", "色盲考生不予录取；色弱考生不建议报考",
    ),
    # Subject score requirements
    AdmissionRequirement(
        "上海外国语大学", "英语", "subject_score",
        "单科成绩要求", "高考英语单科成绩不低于 120 分",
    ),
    AdmissionRequirement(
        "复旦大学", "经济学", "subject_score",
        "单科成绩要求", "高考数学单科成绩不低于 130 分（建议）",
    ),
    # Language requirements
    AdmissionRequirement(
        "上海外国语大学", "英语", "language",
        "语种要求", "仅招收英语语种考生",
    ),
    # Subject selection (上海 3+3 选科)
    AdmissionRequirement(
        "上海交通大学", "临床医学", "subject_selection",
        "选科要求", "必选物理和化学",
    ),
    AdmissionRequirement(
        "同济大学", "建筑学", "subject_selection",
        "选科要求", "必选物理",
    ),
    AdmissionRequirement(
        "华东理工大学", "化学工程与工艺", "subject_selection",
        "选科要求", "必选化学",
    ),
    AdmissionRequirement(
        "同济大学", "土木工程", "subject_selection",
        "选科要求", "必选物理",
    ),
    # Physical exam
    AdmissionRequirement(
        "上海海事大学", "航海技术", "physical",
        "体检要求", "身高男生不低于 165cm，女生不低于 160cm；双眼裸眼视力不低于 4.7",
    ),
    # Gender
    AdmissionRequirement(
        "上海海事大学", "航海技术", "gender",
        "性别要求", "仅招收男生（航海类专业行业惯例）",
    ),
    AdmissionRequirement(
        "上海健康医学院", "护理学", "gender",
        "性别说明", "男女兼收，男生比例不超过 15%",
    ),
]


def get_requirements(
    university: str, major: str | None = None
) -> list[AdmissionRequirement]:
    """Return admission requirements for a university (optionally filtered by major)."""
    results: list[AdmissionRequirement] = []
    for req in _REQUIREMENTS:
        if req.university != university:
            continue
        if major is not None and req.major != major:
            continue
        results.append(req)
    return results
