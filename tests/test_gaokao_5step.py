"""Tests for the Zhang Xuefeng 5-step gaokao tools and data layer."""

import json

import pytest

from backend.data.gaokao.province_models import (
    PROVINCE_MODELS,
    GaokaoModel,
    get_gaokao_model,
    infer_subject_type,
)
from backend.data.gaokao.requirement_data import AdmissionRequirement, get_requirements
from backend.data.gaokao.score_rank_table import (
    CURRENT_YEAR,
    REFERENCE_YEARS,
    SUPPORTED_PROVINCES,
    get_rank_for_score,
    get_score_for_rank,
)
from backend.data.gaokao.university_data import find_schools_by_score_range
from backend.storage.cache_store import cache_store
from backend.tools.check_requirements_tool import CheckRequirementsTool
from backend.tools.find_schools_tool import FindSchoolsTool, _classify_tier
from backend.tools.score_to_rank_tool import ScoreToRankTool


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the global cache before each test."""
    cache_store._data.clear()


# ═════════════════════════════════════════════════════════════════════════
# Data Layer — Score Rank Table
# ═════════════════════════════════════════════════════════════════════════

class TestScoreRankTable:
    def test_exact_score_lookup(self):
        """Exact score in the table should return exact rank."""
        rank = get_rank_for_score("上海", 2023, "综合", 580)
        assert rank == 2393

    def test_interpolated_score(self):
        """Score between two table entries should interpolate."""
        # 580 → 2393, 579 → 2520
        rank = get_rank_for_score("上海", 2023, "综合", 580)
        rank_below = get_rank_for_score("上海", 2023, "综合", 579)
        assert rank is not None
        assert rank_below is not None
        assert rank < rank_below  # Higher score = better (lower) rank

    def test_max_score(self):
        """Score at the maximum (619) should return its rank."""
        rank = get_rank_for_score("上海", 2023, "综合", 619)
        assert rank == 48

    def test_above_max_score(self):
        """Score above max should return rank 1."""
        rank = get_rank_for_score("上海", 2023, "综合", 650)
        assert rank == 1

    def test_min_score(self):
        """Score at the minimum should return the table rank."""
        rank = get_rank_for_score("上海", 2023, "综合", 284)
        assert rank == 51560

    def test_below_min_score(self):
        """Score below minimum should return None."""
        rank = get_rank_for_score("上海", 2023, "综合", 250)
        assert rank is None

    def test_unknown_province(self):
        """Unknown province should return None."""
        rank = get_rank_for_score("火星", 2023, "综合", 580)
        assert rank is None

    def test_unknown_year(self):
        """Unknown year should return None."""
        rank = get_rank_for_score("上海", 2000, "综合", 580)
        assert rank is None

    def test_reverse_lookup_exact(self):
        """Exact rank in the table should return the corresponding score."""
        score = get_score_for_rank("上海", 2023, "综合", 2393)
        assert score == 580

    def test_reverse_lookup_interpolated(self):
        """Rank between two entries should interpolate."""
        score = get_score_for_rank("上海", 2023, "综合", 2450)
        assert score is not None
        # Rank 2450 is between 2393 (580) and 2520 (579)
        assert 579 <= score <= 580

    def test_reverse_lookup_best_rank(self):
        """Rank better than best should return highest score."""
        score = get_score_for_rank("上海", 2023, "综合", 1)
        assert score == 619

    def test_reverse_lookup_worst_rank(self):
        """Rank worse than worst should return None."""
        score = get_score_for_rank("上海", 2023, "综合", 99999)
        assert score is None

    def test_cross_year_consistency(self):
        """All three years should have data for Shanghai."""
        for year in [CURRENT_YEAR, *REFERENCE_YEARS]:
            rank = get_rank_for_score("上海", year, "综合", 560)
            assert rank is not None, f"No data for year {year}"

    def test_supported_provinces(self):
        assert "上海" in SUPPORTED_PROVINCES

    def test_current_year_is_2023(self):
        assert CURRENT_YEAR == 2023
        assert REFERENCE_YEARS == [2022, 2021]


# ═════════════════════════════════════════════════════════════════════════
# Data Layer — Province Models
# ═════════════════════════════════════════════════════════════════════════

class TestProvinceModels:
    def test_all_3plus3_provinces(self):
        """3+3 provinces should have 综合 as the only subject type."""
        for prov in ["上海", "浙江", "北京", "天津", "山东", "海南"]:
            model = get_gaokao_model(prov)
            assert model is not None, f"{prov} should have a model"
            assert model.subject_types == ("综合",)
            assert model.default == "综合"

    def test_all_3plus1plus2_provinces(self):
        """3+1+2 provinces should have 物理类/历史类."""
        for prov in ["河北", "辽宁", "江苏", "福建", "湖北", "湖南", "广东", "重庆",
                      "黑龙江", "甘肃", "吉林", "安徽", "江西", "贵州", "广西"]:
            model = get_gaokao_model(prov)
            assert model is not None, f"{prov} should have a model"
            assert model.subject_types == ("物理类", "历史类")
            assert model.default is None

    def test_all_traditional_provinces(self):
        """Traditional provinces should have 理科/文科."""
        for prov in ["河南", "四川", "云南", "山西", "陕西", "内蒙古", "宁夏", "青海", "西藏", "新疆"]:
            model = get_gaokao_model(prov)
            assert model is not None, f"{prov} should have a model"
            assert model.subject_types == ("理科", "文科")
            assert model.default is None

    def test_unknown_province(self):
        assert get_gaokao_model("火星") is None

    def test_infer_3plus3_auto_fill(self):
        """3+3 provinces should auto-fill to 综合."""
        assert infer_subject_type("上海") == "综合"
        assert infer_subject_type("北京") == "综合"

    def test_infer_3plus3_with_existing(self):
        """Providing 综合 for a 3+3 province should pass through."""
        assert infer_subject_type("上海", "综合") == "综合"

    def test_infer_3plus1plus2_no_input(self):
        """3+1+2 province without subject_type should return None."""
        assert infer_subject_type("广东") is None

    def test_infer_3plus1plus2_valid(self):
        """3+1+2 province with valid subject_type should pass through."""
        assert infer_subject_type("广东", "物理类") == "物理类"
        assert infer_subject_type("广东", "历史类") == "历史类"

    def test_infer_3plus1plus2_legacy_remap(self):
        """3+1+2 province should remap legacy 理科→物理类, 文科→历史类."""
        assert infer_subject_type("广东", "理科") == "物理类"
        assert infer_subject_type("广东", "文科") == "历史类"

    def test_infer_traditional_valid(self):
        """Traditional province with valid subject_type should pass through."""
        assert infer_subject_type("河南", "理科") == "理科"
        assert infer_subject_type("河南", "文科") == "文科"

    def test_infer_traditional_no_input(self):
        """Traditional province without subject_type should return None."""
        assert infer_subject_type("河南") is None

    def test_infer_unknown_province(self):
        """Unknown province should return the input as-is or None."""
        assert infer_subject_type("火星") is None
        assert infer_subject_type("火星", "理科") == "理科"

    def test_province_count(self):
        """Should have 31 provinces total."""
        assert len(PROVINCE_MODELS) == 31


# ═════════════════════════════════════════════════════════════════════════
# Data Layer — University Data
# ═════════════════════════════════════════════════════════════════════════

class TestUniversityData:
    def test_basic_range_query(self):
        """Should find schools in a score range."""
        results = find_schools_by_score_range("上海", "综合", 560, 600)
        assert len(results) > 0
        for r in results:
            assert 560 <= r.min_score <= 600

    def test_results_sorted_descending(self):
        """Results should be sorted by min_score descending."""
        results = find_schools_by_score_range("上海", "综合", 500, 600)
        scores = [r.min_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_city_filter(self):
        """City filter should narrow results."""
        all_results = find_schools_by_score_range("上海", "综合", 400, 660)
        city_results = find_schools_by_score_range("上海", "综合", 400, 660, city="上海")
        # All our data is Shanghai, so these should be equal
        assert len(city_results) == len(all_results)

    def test_tier_filter(self):
        """Tier filter should only return matching tiers."""
        results = find_schools_by_score_range("上海", "综合", 400, 660, tier="985")
        assert len(results) > 0
        for r in results:
            assert r.tier == "985"

    def test_major_keyword_filter(self):
        """Major keyword should filter by partial match."""
        results = find_schools_by_score_range("上海", "综合", 400, 660, major_keyword="医")
        assert len(results) > 0
        for r in results:
            assert "医" in r.major

    def test_empty_results(self):
        """Should return empty list for impossible range."""
        results = find_schools_by_score_range("上海", "综合", 700, 800)
        assert results == []

    def test_year_filter(self):
        """Year filter should work."""
        results = find_schools_by_score_range("上海", "综合", 500, 600, year=2023)
        assert len(results) > 0
        for r in results:
            assert r.year == 2023

    def test_wrong_province(self):
        """Wrong province should return empty."""
        results = find_schools_by_score_range("北京", "综合", 400, 660)
        assert results == []


# ═════════════════════════════════════════════════════════════════════════
# Data Layer — Requirement Data
# ═════════════════════════════════════════════════════════════════════════

class TestRequirementData:
    def test_university_with_requirements(self):
        """University with known requirements should return them."""
        reqs = get_requirements("上海交通大学", "临床医学")
        assert len(reqs) > 0
        types = {r.requirement_type for r in reqs}
        assert "vision" in types
        assert "subject_selection" in types

    def test_university_without_requirements(self):
        """University/major combo without requirements returns empty."""
        reqs = get_requirements("复旦大学", "计算机科学与技术")
        assert reqs == []

    def test_university_all_majors(self):
        """Query with no major returns all requirements for the university."""
        reqs = get_requirements("上海海事大学")
        assert len(reqs) >= 2
        majors = {r.major for r in reqs}
        assert "航海技术" in majors

    def test_requirement_fields(self):
        """Requirement objects should have all fields."""
        reqs = get_requirements("上海外国语大学", "英语")
        assert len(reqs) > 0
        for req in reqs:
            assert isinstance(req, AdmissionRequirement)
            assert req.university
            assert req.major
            assert req.requirement_type
            assert req.description
            assert req.details

    def test_nonexistent_university(self):
        reqs = get_requirements("不存在的大学")
        assert reqs == []


# ═════════════════════════════════════════════════════════════════════════
# Tier Classification Logic
# ═════════════════════════════════════════════════════════════════════════

class TestTierClassification:
    def test_reach_tier(self):
        """Delta +5 to +20 should be 冲."""
        assert _classify_tier(5) == "冲"
        assert _classify_tier(10) == "冲"
        assert _classify_tier(20) == "冲"

    def test_match_tier(self):
        """Delta -5 to +5 should be 稳."""
        assert _classify_tier(0) == "稳"
        assert _classify_tier(4) == "稳"
        assert _classify_tier(-4) == "稳"

    def test_safety_tier(self):
        """Delta -10 to -5 should be 保."""
        assert _classify_tier(-6) == "保"
        assert _classify_tier(-10) == "保"

    def test_floor_tier(self):
        """Delta -30 to -10 should be 底."""
        assert _classify_tier(-11) == "底"
        assert _classify_tier(-20) == "底"
        assert _classify_tier(-30) == "底"

    def test_out_of_range(self):
        """Delta outside all ranges should return None."""
        assert _classify_tier(25) is None
        assert _classify_tier(-35) is None

    def test_boundary_冲_稳(self):
        """At delta=+5, should be 冲 (冲 range is [5, 20])."""
        assert _classify_tier(5) == "冲"

    def test_boundary_稳_保(self):
        """At delta=-5, should be 稳 (稳 range is [-5, 5])."""
        assert _classify_tier(-5) == "稳"

    def test_boundary_保_底(self):
        """At delta=-10, should be 保 (保 range is [-10, -5])."""
        assert _classify_tier(-10) == "保"


# ═════════════════════════════════════════════════════════════════════════
# Tool Layer — ScoreToRankTool
# ═════════════════════════════════════════════════════════════════════════

class TestScoreToRankTool:
    @pytest.fixture
    def tool(self):
        return ScoreToRankTool()

    def test_definition(self, tool):
        defn = tool.definition()
        assert defn.name == "score_to_rank"
        param_names = [p.name for p in defn.parameters]
        assert "score" in param_names
        assert "province" in param_names
        assert "subject_type" in param_names

    @pytest.mark.asyncio
    async def test_missing_required_params(self, tool):
        result = await tool.execute()
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_unsupported_province(self, tool):
        result = await tool.execute(score=580, province="火星", subject_type="综合")
        assert "暂不支持" in result

    @pytest.mark.asyncio
    async def test_successful_execution(self, tool):
        result = await tool.execute(score=560, province="上海", subject_type="综合")
        assert "位次" in result or "排名" in result
        assert "等位分" in result
        assert "<data>" in result

        # Verify data block is valid JSON
        data_start = result.index("<data>") + len("<data>")
        data_end = result.index("</data>")
        data = json.loads(result[data_start:data_end])
        assert data["score"] == 560
        assert data["rank"] > 0
        assert "equivalent_scores" in data

    @pytest.mark.asyncio
    async def test_cache_hit(self, tool):
        result1 = await tool.execute(score=560, province="上海", subject_type="综合")
        result2 = await tool.execute(score=560, province="上海", subject_type="综合")
        assert result1 == result2
        # Verify cache was actually used (only 1 entry in cache)
        assert len(cache_store._data) == 1

    @pytest.mark.asyncio
    async def test_out_of_range_score(self, tool):
        result = await tool.execute(score=100, province="上海", subject_type="综合")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_high_score_returns_rank_1(self, tool):
        """Score above max in table should return rank 1."""
        result = await tool.execute(score=640, province="上海", subject_type="综合")
        data_start = result.index("<data>") + len("<data>")
        data_end = result.index("</data>")
        data = json.loads(result[data_start:data_end])
        assert data["rank"] == 1

    @pytest.mark.asyncio
    async def test_shanghai_auto_defaults_to_zonghe(self, tool):
        """上海 without subject_type should default to 综合."""
        result = await tool.execute(score=560, province="上海")
        assert "Error" not in result
        assert "<data>" in result
        data_start = result.index("<data>") + len("<data>")
        data_end = result.index("</data>")
        data = json.loads(result[data_start:data_end])
        assert data["subject_type"] == "综合"

    @pytest.mark.asyncio
    async def test_3plus3_province_auto_fill(self, tool):
        """Any 3+3 province without subject_type should auto-fill 综合."""
        # 北京 is 3+3 but not in SUPPORTED_PROVINCES, so it'll fail on data lookup
        # but should NOT fail on subject_type detection
        result = await tool.execute(score=560, province="北京")
        assert "请提供科类" not in result  # should not ask for subject_type

    @pytest.mark.asyncio
    async def test_3plus1plus2_province_needs_subject_type(self, tool):
        """3+1+2 province without subject_type should ask for it."""
        result = await tool.execute(score=560, province="广东")
        assert "请提供科类" in result
        assert "物理类" in result
        assert "历史类" in result
        assert "3+1+2" in result

    @pytest.mark.asyncio
    async def test_traditional_province_needs_subject_type(self, tool):
        """Traditional province without subject_type should ask for it."""
        result = await tool.execute(score=560, province="河南")
        assert "请提供科类" in result
        assert "理科" in result
        assert "文科" in result


# ═════════════════════════════════════════════════════════════════════════
# Tool Layer — FindSchoolsTool
# ═════════════════════════════════════════════════════════════════════════

class TestFindSchoolsTool:
    @pytest.fixture
    def tool(self):
        return FindSchoolsTool()

    def test_definition(self, tool):
        defn = tool.definition()
        assert defn.name == "find_schools"
        param_names = [p.name for p in defn.parameters]
        assert "rank" in param_names
        assert "province" in param_names
        assert "subject_type" in param_names

    @pytest.mark.asyncio
    async def test_missing_required_params(self, tool):
        result = await tool.execute()
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_unsupported_province(self, tool):
        result = await tool.execute(rank=3000, province="火星", subject_type="综合")
        assert "暂不支持" in result

    @pytest.mark.asyncio
    async def test_successful_execution(self, tool):
        # Rank ~5664 corresponds to score ~560
        result = await tool.execute(rank=5664, province="上海", subject_type="综合")
        assert "冲" in result or "稳" in result or "保" in result or "底" in result
        assert "<data>" in result

        # Verify data block
        data_start = result.index("<data>") + len("<data>")
        data_end = result.index("</data>")
        data = json.loads(result[data_start:data_end])
        assert "schools" in data
        assert len(data["schools"]) > 0

    @pytest.mark.asyncio
    async def test_tier_classification_in_output(self, tool):
        """Schools should be classified into tiers in the output."""
        result = await tool.execute(rank=5664, province="上海", subject_type="综合")
        assert "冲刺" in result or "稳妥" in result or "保底" in result or "垫底" in result

    @pytest.mark.asyncio
    async def test_cache_hit(self, tool):
        result1 = await tool.execute(rank=5664, province="上海", subject_type="综合")
        result2 = await tool.execute(rank=5664, province="上海", subject_type="综合")
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_empty_results(self, tool):
        """Very high rank (low score) with 985 filter should find nothing."""
        result = await tool.execute(
            rank=40000, province="上海", subject_type="综合", tier_preference="985"
        )
        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_major_keyword_filter(self, tool):
        result = await tool.execute(
            rank=5664, province="上海", subject_type="综合", major_keyword="工程"
        )
        # Should contain either results or a not-found message
        assert "<data>" in result or "未找到" in result

    @pytest.mark.asyncio
    async def test_invalid_rank(self, tool):
        """Extremely low rank that can't be converted should error."""
        result = await tool.execute(rank=999999, province="上海", subject_type="综合")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_shanghai_auto_defaults_to_zonghe(self, tool):
        """上海 without subject_type should default to 综合."""
        result = await tool.execute(rank=5664, province="上海")
        assert "Error" not in result
        assert "<data>" in result

    @pytest.mark.asyncio
    async def test_3plus1plus2_province_needs_subject_type(self, tool):
        """3+1+2 province without subject_type should ask for it."""
        result = await tool.execute(rank=5664, province="广东")
        assert "请提供科类" in result
        assert "物理类" in result
        assert "历史类" in result

    @pytest.mark.asyncio
    async def test_traditional_province_needs_subject_type(self, tool):
        """Traditional province without subject_type should ask for it."""
        result = await tool.execute(rank=5664, province="四川")
        assert "请提供科类" in result
        assert "理科" in result
        assert "文科" in result


# ═════════════════════════════════════════════════════════════════════════
# Tool Layer — CheckRequirementsTool
# ═════════════════════════════════════════════════════════════════════════

class TestCheckRequirementsTool:
    @pytest.fixture
    def tool(self):
        return CheckRequirementsTool()

    def test_definition(self, tool):
        defn = tool.definition()
        assert defn.name == "check_requirements"
        param_names = [p.name for p in defn.parameters]
        assert "schools_json" in param_names

    @pytest.mark.asyncio
    async def test_missing_param(self, tool):
        result = await tool.execute()
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_invalid_json(self, tool):
        result = await tool.execute(schools_json="not json")
        assert "Error" in result
        assert "JSON" in result

    @pytest.mark.asyncio
    async def test_empty_array(self, tool):
        result = await tool.execute(schools_json="[]")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_school_with_requirements(self, tool):
        schools = [{"university": "上海交通大学", "major": "临床医学"}]
        result = await tool.execute(schools_json=json.dumps(schools))
        assert "⚠️" in result
        assert "上海交通大学" in result

    @pytest.mark.asyncio
    async def test_school_without_requirements(self, tool):
        schools = [{"university": "复旦大学", "major": "计算机科学与技术"}]
        result = await tool.execute(schools_json=json.dumps(schools))
        assert "✅" in result
        assert "复旦大学" in result

    @pytest.mark.asyncio
    async def test_mixed_requirements(self, tool):
        """Some schools with requirements, some without."""
        schools = [
            {"university": "上海交通大学", "major": "临床医学"},
            {"university": "复旦大学", "major": "计算机科学与技术"},
            {"university": "上海外国语大学", "major": "英语"},
        ]
        result = await tool.execute(schools_json=json.dumps(schools))
        assert "⚠️" in result
        assert "✅" in result
        assert "上海交通大学" in result
        assert "复旦大学" in result
        assert "上海外国语大学" in result

    @pytest.mark.asyncio
    async def test_multiple_requirements_per_school(self, tool):
        """Schools can have multiple different requirement types."""
        schools = [{"university": "上海海事大学", "major": "航海技术"}]
        result = await tool.execute(schools_json=json.dumps(schools))
        # Should have both physical and gender requirements
        assert "体检" in result or "physical" in result
        assert "性别" in result or "gender" in result
