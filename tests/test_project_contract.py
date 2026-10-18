from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_governance_documents_exist() -> None:
    """The project must keep its operating contract beside the source tree."""

    for relative_path in ("AGENTS.md", "agent.md", "医院信息系统课程设计开发方案.md"):
        assert (ROOT / relative_path).is_file(), (
            f"missing required document: {relative_path}"
        )


def test_agents_contract_mentions_business_invariants() -> None:
    content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    for phrase in (
        "号源不能小于 0",
        "收费单创建、处方状态更新和库存扣减",
        "未登录返回 401",
    ):
        assert phrase in content, f"AGENTS.md is missing required invariant: {phrase}"


def test_delivery_contract_files_have_expected_locations() -> None:
    """Keep the planned delivery entry points stable for future implementation."""

    expected_paths = (
        ".github/workflows/ci.yml",
        "docker-compose.yml",
        "docs/test-report.md",
        "docs/ci-cd.md",
    )
    for relative_path in expected_paths:
        assert (ROOT / relative_path).is_file(), (
            f"missing delivery file: {relative_path}"
        )
