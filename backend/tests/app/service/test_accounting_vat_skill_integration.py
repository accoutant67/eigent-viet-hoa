"""Exercise VAT Skill discovery, package files, role map, and access rules."""

import json
import shutil
from pathlib import Path

import pytest

from app.agent.toolkit import skill_toolkit
from app.service import skill_config_service, skill_service

pytestmark = pytest.mark.unit
SKILL_NAME = "accounting-vat-return"
BUNDLED_SKILL = (
    Path(__file__).resolve().parents[4]
    / "resources"
    / "example-skills"
    / SKILL_NAME
)


def test_vat_skill_is_discovered_once_and_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (BUNDLED_SKILL / "SKILL.md").is_file()
    examples = tmp_path / "bundled" / "example-skills"
    examples.mkdir(parents=True)
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
    files = {
        item["path"] for item in skill_service.skill_list_files(SKILL_NAME)
    }
    assert {
        "SKILL.md",
        "roles.json",
        "legal/form_catalog.json",
        "scripts/vat_return_draft.py",
    } <= files

    roles = json.loads(
        (installed / SKILL_NAME / "roles.json").read_text(encoding="utf-8")
    )
    role_ids = [item["role_id"] for item in roles["roles"]]
    assert len(role_ids) == len(set(role_ids))
    assert set(role_ids) == {
        "HD01",
        "HD02",
        "HD03",
        "HD04",
        "TK01",
        "TK05",
        "BM01",
        "BM02",
        "BM03",
        "PL01",
        "PL02",
        "PL03",
        "PL04",
        "KTT03",
    }
    assert roles["agent_registration"] == "none"
    assert roles["execution_model"].startswith("one Eigent Skill pipeline")
    assert all(item.get("implementation_status") for item in roles["roles"])

    config = skill_config_service.skill_config_init("synthetic_vat_user")
    assert config["skills"][SKILL_NAME]["enabled"] is True
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
