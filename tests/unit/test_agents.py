"""Agent 團隊定義的回歸測試：frontmatter 合法、路由表完整、指令引用的 agent 都存在。"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
AGENTS = sorted((ROOT / ".claude" / "agents").glob("*.md"))
VALID_TOOLS = {"Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebSearch", "WebFetch"}


def frontmatter(path: Path) -> dict:
    m = re.match(r"\A---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert m, f"{path.name} 缺少 frontmatter"
    return yaml.safe_load(m.group(1))


def test_team_covers_every_pipeline_stage():
    names = {p.stem for p in AGENTS}
    assert names == {
        "keyword-strategist", "content-architect", "bilingual-writer", "quality-gatekeeper",
        "monetization-optimizer", "site-release-engineer", "growth-analyst", "tdd-guardian",
    }


@pytest.mark.parametrize("path", AGENTS, ids=lambda p: p.stem)
def test_agent_frontmatter_valid(path):
    meta = frontmatter(path)
    assert meta["name"] == path.stem
    assert len(meta["description"]) >= 40
    tools = {t.strip() for t in meta["tools"].split(",")}
    assert tools <= VALID_TOOLS, tools - VALID_TOOLS


def test_gatekeeper_cannot_edit_content():
    """獨立審查員只審不改，避免自己改自己評。"""
    tools = frontmatter(ROOT / ".claude" / "agents" / "quality-gatekeeper.md")["tools"]
    assert "Write" not in tools and "Edit" not in tools


def test_routing_table_lists_every_agent():
    guide = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    for path in AGENTS:
        assert f"`{path.stem}`" in guide, f"CLAUDE.md 路由表缺少 {path.stem}"


@pytest.mark.parametrize("command", sorted((ROOT / ".claude" / "commands").glob("*.md")), ids=lambda p: p.stem)
def test_commands_only_reference_existing_agents(command):
    names = {p.stem for p in AGENTS}
    referenced = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", command.read_text(encoding="utf-8")))
    agent_like = {r for r in referenced if r.endswith(("strategist", "architect", "writer", "gatekeeper",
                                                       "optimizer", "engineer", "analyst", "guardian"))}
    assert agent_like and agent_like <= names
