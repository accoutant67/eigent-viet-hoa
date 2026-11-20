"""Exercise the real bundled accounting Skill through Eigent's Skill service."""

import shutil
from pathlib import Path

import pytest

from app.agent.toolkit import skill_toolkit
from app.service import skill_config_service, skill_service

pytestmark = pytest.mark.unit

SKILL_NAME = "accounting-workbook-audit"
BUNDLED_SKILL = (
    Path(__file__).resolve().parents[4]
    / "resources"
    / "example-skills"
    / SKILL_NAME
)


def test_accounting_skill_is_discovered_once_and_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (BUNDLED_SKILL / "SKILL.md").is_file()
    examples = tmp_path / "bundled" / "example-skills"
    shutil.copytree(BUNDLED_SKILL, examples / SKILL_NAME)
    installed = tmp_path / "home" / ".eigent" / "skills"
    monkeypatch.setenv(skill_service.EXAMPLE_SKILLS_ENV, str(examples))
    monkeypatch.setattr(skill_service, "SKILLS_ROOT", installed)
    monkeypatch.setattr(
        skill_config_service, "EIGENT_ROOT", tmp_path / "home" / ".eigent"
    )

    found = [
        item
        for item in skill_service.skills_scan()
        if item["name"] == SKILL_NAME
    ]
    assert len(found) == 1
    assert found[0]["isExample"] is True
    assert found[0]["skillDirName"] == SKILL_NAME
    assert (installed / SKILL_NAME / "scripts" / "audit_workbook.py").is_file()
    assert {
        item["path"] for item in skill_service.skill_list_files(SKILL_NAME)
    } >= {
        "SKILL.md",
        "scripts/audit_workbook.py",
    }

    config = skill_config_service.skill_config_init("synthetic_smoke_user")
    entry = config["skills"][SKILL_NAME]
    assert entry["enabled"] is True
    assert entry["isExample"] is True

    restricted = {
        SKILL_NAME: {
            "enabled": True,
            "scope": {"isGlobal": False, "selectedAgents": ["single_agent"]},
        }
    }
    assert skill_toolkit._is_agent_allowed(
        SKILL_NAME, "single_agent", restricted
    )
    assert not skill_toolkit._is_agent_allowed(
        SKILL_NAME, "developer_agent", restricted
    )
    restricted[SKILL_NAME]["enabled"] = False
    assert (
        skill_toolkit._build_allowed_skills(restricted, "single_agent")
        == set()
    )
