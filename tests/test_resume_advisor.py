"""Tests for the resume advisor tool."""

import json

import pytest

from backend.tools.resume_advisor_tool import ResumeAdvisorTool

SAMPLE_RESUME = """
John Doe
Software Engineer

## Summary
Experienced software engineer with 5 years building scalable web applications.

## Experience
Senior Engineer at TechCorp (2020–present)
- Led migration of monolith to microservices serving 500k daily active users
- Reduced API latency by 40% through caching layer optimisation
- Built CI/CD pipeline cutting deploy time from 2 hours to 15 minutes
- Managed team of 6 engineers delivering $2M project on time

Software Engineer at StartupX (2018–2020)
- Developed backend APIs serving 100k requests/day
- Increased test coverage from 30% to 85%

## Skills
Python, Go, Kubernetes, PostgreSQL, AWS, Docker, CI/CD

## Education
BSc Computer Science, MIT, 2018
"""

MINIMAL_RESUME = "John Doe. Works at a company. Does some stuff."


@pytest.mark.asyncio
async def test_ats_score_returned():
    tool = ResumeAdvisorTool()
    result = await tool.execute(resume_text=SAMPLE_RESUME, target_role="Software Engineer Python")
    data = json.loads(result)
    assert "ats_score" in data
    assert 0 <= data["ats_score"] <= 100


@pytest.mark.asyncio
async def test_section_scores_present():
    tool = ResumeAdvisorTool()
    result = await tool.execute(resume_text=SAMPLE_RESUME)
    data = json.loads(result)
    assert "section_scores" in data
    assert isinstance(data["section_scores"], dict)


@pytest.mark.asyncio
async def test_good_resume_has_strengths():
    tool = ResumeAdvisorTool()
    result = await tool.execute(resume_text=SAMPLE_RESUME)
    data = json.loads(result)
    assert len(data["strengths"]) > 0


@pytest.mark.asyncio
async def test_minimal_resume_has_improvements():
    tool = ResumeAdvisorTool()
    result = await tool.execute(resume_text=MINIMAL_RESUME)
    data = json.loads(result)
    assert len(data["improvements"]) > 0


@pytest.mark.asyncio
async def test_empty_resume_returns_error():
    tool = ResumeAdvisorTool()
    result = await tool.execute(resume_text="   ")
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_missing_keywords_for_target_role():
    tool = ResumeAdvisorTool()
    result = await tool.execute(resume_text=MINIMAL_RESUME, target_role="machine learning tensorflow")
    data = json.loads(result)
    # "tensorflow" not in the minimal resume
    assert "tensorflow" in data.get("missing_keywords", [])


@pytest.mark.asyncio
async def test_action_verb_count():
    tool = ResumeAdvisorTool()
    result = await tool.execute(resume_text=SAMPLE_RESUME)
    data = json.loads(result)
    assert data["action_verb_count"] >= 3  # SAMPLE_RESUME has many verbs


@pytest.mark.asyncio
async def test_definition_name():
    tool = ResumeAdvisorTool()
    assert tool.definition().name == "resume_advisor"
