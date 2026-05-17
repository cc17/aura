"""Shanghai university admission data (mock, 2023).

Contains ~30 records covering 985/211/一本/二本 tiers for Shanghai-area universities.
Scores are realistic estimates aligned with the 2023 一分一段表.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdmissionRecord:
    university: str
    major: str
    province: str
    year: int
    subject_type: str
    min_score: int
    min_rank: int
    tier: str  # "985", "211", "一本", "二本"
    city: str


_RECORDS: list[AdmissionRecord] = [
    # ── 985 院校 ──
    AdmissionRecord("复旦大学", "计算机科学与技术", "上海", 2023, "综合", 598, 705, "985", "上海"),
    AdmissionRecord("复旦大学", "经济学", "上海", 2023, "综合", 596, 828, "985", "上海"),
    AdmissionRecord("上海交通大学", "电子信息工程", "上海", 2023, "综合", 597, 770, "985", "上海"),
    AdmissionRecord("上海交通大学", "临床医学", "上海", 2023, "综合", 600, 591, "985", "上海"),
    AdmissionRecord("同济大学", "建筑学", "上海", 2023, "综合", 585, 1780, "985", "上海"),
    AdmissionRecord("同济大学", "土木工程", "上海", 2023, "综合", 580, 2393, "985", "上海"),
    AdmissionRecord("华东师范大学", "心理学", "上海", 2023, "综合", 582, 2134, "985", "上海"),
    AdmissionRecord("华东师范大学", "教育学", "上海", 2023, "综合", 578, 2668, "985", "上海"),
    # ── 211 院校 ──
    AdmissionRecord("上海财经大学", "金融学", "上海", 2023, "综合", 580, 2393, "211", "上海"),
    AdmissionRecord("上海财经大学", "会计学", "上海", 2023, "综合", 577, 2821, "211", "上海"),
    AdmissionRecord("上海外国语大学", "英语", "上海", 2023, "综合", 573, 3404, "211", "上海"),
    AdmissionRecord("华东理工大学", "化学工程与工艺", "上海", 2023, "综合", 565, 4750, "211", "上海"),
    AdmissionRecord("东华大学", "服装设计与工程", "上海", 2023, "综合", 555, 6649, "211", "上海"),
    AdmissionRecord("上海大学", "机械工程", "上海", 2023, "综合", 563, 5080, "211", "上海"),
    AdmissionRecord("上海大学", "新闻传播学", "上海", 2023, "综合", 560, 5664, "211", "上海"),
    # ── 一本院校 ──
    AdmissionRecord("上海理工大学", "光电信息科学与工程", "上海", 2023, "综合", 542, 9418, "一本", "上海"),
    AdmissionRecord("上海理工大学", "机械设计制造及其自动化", "上海", 2023, "综合", 538, 10340, "一本", "上海"),
    AdmissionRecord("上海师范大学", "汉语言文学", "上海", 2023, "综合", 532, 11739, "一本", "上海"),
    AdmissionRecord("上海师范大学", "数学与应用数学", "上海", 2023, "综合", 528, 12669, "一本", "上海"),
    AdmissionRecord("上海中医药大学", "中医学", "上海", 2023, "综合", 550, 7651, "一本", "上海"),
    AdmissionRecord("上海海事大学", "航海技术", "上海", 2023, "综合", 520, 14672, "一本", "上海"),
    AdmissionRecord("上海海事大学", "物流管理", "上海", 2023, "综合", 515, 15916, "一本", "上海"),
    AdmissionRecord("上海对外经贸大学", "国际经济与贸易", "上海", 2023, "综合", 540, 9864, "一本", "上海"),
    # ── 二本院校 ──
    AdmissionRecord("上海应用技术大学", "材料科学与工程", "上海", 2023, "综合", 498, 20181, "二本", "上海"),
    AdmissionRecord("上海电力大学", "电气工程及其自动化", "上海", 2023, "综合", 510, 17139, "二本", "上海"),
    AdmissionRecord("上海第二工业大学", "智能制造工程", "上海", 2023, "综合", 495, 20893, "二本", "上海"),
    AdmissionRecord("上海商学院", "电子商务", "上海", 2023, "综合", 490, 22166, "二本", "上海"),
    AdmissionRecord("上海工程技术大学", "车辆工程", "上海", 2023, "综合", 505, 18398, "二本", "上海"),
    AdmissionRecord("上海工程技术大学", "飞行器制造工程", "上海", 2023, "综合", 502, 19158, "二本", "上海"),
    AdmissionRecord("上海健康医学院", "护理学", "上海", 2023, "综合", 485, 23334, "二本", "上海"),
    AdmissionRecord("上海立信会计金融学院", "审计学", "上海", 2023, "综合", 508, 17631, "二本", "上海"),
]


def find_schools_by_score_range(
    province: str,
    subject_type: str,
    min_score: int,
    max_score: int,
    *,
    year: int | None = None,
    city: str | None = None,
    tier: str | None = None,
    major_keyword: str | None = None,
) -> list[AdmissionRecord]:
    """Filter admission records by score range and optional criteria.

    Returns records sorted by min_score descending (best schools first).
    """
    results: list[AdmissionRecord] = []

    for rec in _RECORDS:
        if rec.province != province:
            continue
        if rec.subject_type != subject_type:
            continue
        if not (min_score <= rec.min_score <= max_score):
            continue
        if year is not None and rec.year != year:
            continue
        if city is not None and city not in rec.city:
            continue
        if tier is not None and rec.tier != tier:
            continue
        if major_keyword is not None and major_keyword not in rec.major:
            continue
        results.append(rec)

    results.sort(key=lambda r: r.min_score, reverse=True)
    return results
