"""Property tests for plan-ml-experiment asset templates."""

import re
from pathlib import Path
from typing import Any, Iterable, List, Tuple

import pytest
import yaml


WORKSPACE = Path(__file__).resolve().parents[1]
ASSETS_ROOT = WORKSPACE / ".agents" / "skills" / "plan-ml-experiment" / "assets"
YAML_TEMPLATES = sorted(ASSETS_ROOT.glob("*.yaml"))
MARKDOWN_TEMPLATES = sorted(ASSETS_ROOT.glob("*.md"))
PLACEHOLDER = re.compile(r"<[^<>\n]+>")
JOB_REQUIRED_KEYS = {"job_id", "type", "entrypoint", "parameters", "resources"}
PLAN_REQUIRED_FIELDS = {
    "experiment_id",
    "status",
    "primary_metric",
    "success_criteria",
    "jobs",
    "approval",
}
PLAN_REQUIRED_SECTIONS = {
    "Research Objective",
    "Baseline",
    "Design Rationale",
    "Agent-Determined Defaults",
    "Risks and Limitations",
}


def _strings(value: Any) -> Iterable[str]:
    """Yield every string contained in a nested YAML value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, nested_value in value.items():
            yield from _strings(key)
            yield from _strings(nested_value)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _assert_placeholders_are_angle_bracketed(text: str) -> None:
    """Ensure template placeholder delimiters are balanced and non-empty."""
    placeholders = PLACEHOLDER.findall(text)
    assert placeholders, "template must contain at least one angle-bracketed placeholder"

    text_without_placeholders = PLACEHOLDER.sub("", text)
    assert "<" not in text_without_placeholders
    assert ">" not in text_without_placeholders


def _parse_frontmatter(text: str) -> Tuple[Any, str]:
    """Return parsed YAML frontmatter and the Markdown body."""
    lines = text.splitlines()
    assert lines and lines[0] == "---", "template must begin with a frontmatter delimiter"

    try:
        closing_delimiter = lines.index("---", 1)
    except ValueError:
        pytest.fail("template must close its YAML frontmatter with '---'")

    frontmatter_text = "\n".join(lines[1:closing_delimiter])
    body = "\n".join(lines[closing_delimiter + 1 :]).strip()
    return yaml.safe_load(frontmatter_text), body


@pytest.mark.parametrize("template_path", YAML_TEMPLATES, ids=lambda path: path.name)
def test_property_4_yaml_templates_are_valid_and_structured(template_path: Path) -> None:
    """Property 4: every YAML asset parses and has the job-template structure.

    **Validates: Requirements 3.3, 3.4, 10.3**
    """
    document = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    assert isinstance(document, dict)
    assert JOB_REQUIRED_KEYS <= document.keys()
    assert document["type"] in {"train", "evaluate"}
    assert isinstance(document["entrypoint"], str) and document["entrypoint"]
    assert isinstance(document["parameters"], dict)
    assert isinstance(document["resources"], dict)

    template_text = template_path.read_text(encoding="utf-8")
    _assert_placeholders_are_angle_bracketed(template_text)
    assert any(PLACEHOLDER.search(value) for value in _strings(document))


def test_property_4_discovers_yaml_templates() -> None:
    """Guard Property 4 against passing vacuously when assets are missing."""
    assert YAML_TEMPLATES, f"no YAML templates found in {ASSETS_ROOT}"


@pytest.mark.parametrize("template_path", MARKDOWN_TEMPLATES, ids=lambda path: path.name)
def test_property_5_markdown_templates_have_valid_frontmatter_and_body(
    template_path: Path,
) -> None:
    """Property 5: every Markdown asset has valid frontmatter and structure.

    **Validates: Requirements 3.2, 10.4**
    """
    template_text = template_path.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(template_text)

    assert isinstance(frontmatter, dict)
    assert PLAN_REQUIRED_FIELDS <= frontmatter.keys()
    assert isinstance(frontmatter["primary_metric"], dict)
    assert {"name", "direction"} <= frontmatter["primary_metric"].keys()
    success_criteria = frontmatter["success_criteria"]
    assert isinstance(success_criteria, (dict, list))
    assert success_criteria
    if isinstance(success_criteria, dict):
        assert {"metric", "comparison", "operator", "threshold"} <= success_criteria.keys()
    assert isinstance(frontmatter["jobs"], list)
    assert frontmatter["jobs"]
    assert isinstance(frontmatter["approval"], dict)
    approval = frontmatter["approval"]
    assert "status" in approval
    if "requested_at" in approval:
        assert PLACEHOLDER.search(approval["requested_at"])
    else:
        assert {"approved_by", "approved_at", "approved_commit"} <= approval.keys()
        assert approval["status"] == "pending"
        assert all(
            approval[field] is None
            for field in ("approved_by", "approved_at", "approved_commit")
        )

    _assert_placeholders_are_angle_bracketed(template_text)
    assert all(
        PLACEHOLDER.search(value)
        for value in (
            frontmatter["experiment_id"],
            frontmatter["primary_metric"]["name"],
        )
    )

    headings: List[str] = re.findall(r"^## (.+)$", body, flags=re.MULTILINE)
    heading_set = set(headings)
    legacy_sections_present = PLAN_REQUIRED_SECTIONS <= heading_set
    phase4_sections_present = (
        {"Agent-Determined Defaults", "Purpose", "Evidence-Backed Baseline", "Design", "Risks and Limitations"}
        <= heading_set
        and re.search(r"^### Rationale$", body, flags=re.MULTILINE) is not None
    )
    assert legacy_sections_present or phase4_sections_present
    assert body, "template must contain Markdown after its frontmatter"


def test_property_5_discovers_markdown_templates() -> None:
    """Guard Property 5 against passing vacuously when assets are missing."""
    assert MARKDOWN_TEMPLATES, f"no Markdown templates found in {ASSETS_ROOT}"
