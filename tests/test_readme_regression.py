"""Regression tests protecting the README presentation layer.

A previous Git merge dropped the cover image, the concise workflow
diagram, and the open-source integration matrix from the default
repository homepage. These tests fail loudly if that happens again.

They are offline, dependency-free, and read repository files only.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

README_EN = REPO_ROOT / "README.md"
README_ZH = REPO_ROOT / "README.zh-CN.md"
INTEGRATIONS_DOC = REPO_ROOT / "docs" / "integrations.md"

COVER_PATH = "assets/smartmoney-cub-harness-cover.png"
SAFETY_DECLARATION = "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"

CONFLICT_MARKER_RE = re.compile(r"^(<{7}( |$)|={7}$|>{7}( |$))", re.MULTILINE)

# Projects allowed to claim `runtime-integrated` must have runtime code
# and tests inside this repository. Keep this map in sync with reality.
RUNTIME_EVIDENCE = {
    "tradingagents": (
        REPO_ROOT / "src" / "smartmoney_cub_harness" / "tradingagents_adapter.py",
        REPO_ROOT / "tests" / "test_tradingagents_adapter.py",
    ),
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_english_readme_restores_cover_and_language_switch():
    readme = read(README_EN)
    assert COVER_PATH in readme, "default homepage must show the existing cover image"
    assert "README.zh-CN.md" in readme, "default homepage must link to the Chinese README"
    assert SAFETY_DECLARATION in readme


def test_english_readme_has_concise_workflow_diagram():
    readme = read(README_EN)
    assert "## How SmartMoney-Cub Works" in readme
    assert readme.count("```mermaid") >= 2, (
        "README.md needs both the concise workflow diagram and the detailed core loop"
    )


def test_english_readme_has_integration_matrix_and_doc_entry():
    readme = read(README_EN)
    assert "## Open-Source Integration Matrix" in readme
    assert "docs/integrations.md" in readme


def test_chinese_readme_restores_cover_and_language_switch():
    readme = read(README_ZH)
    assert COVER_PATH in readme
    assert "(README.md)" in readme, "Chinese README must link back to the English README"
    assert SAFETY_DECLARATION in readme


def test_chinese_readme_has_concise_workflow_diagram():
    readme = read(README_ZH)
    assert "## SmartMoney-Cub 如何工作" in readme
    assert "```mermaid" in readme


def test_chinese_readme_has_integration_matrix_and_doc_entry():
    readme = read(README_ZH)
    assert "优秀开源项目集成矩阵" in readme
    assert "docs/integrations.md" in readme


def test_no_merge_conflict_markers_in_presentation_files():
    files = [README_EN, README_ZH, *sorted((REPO_ROOT / "docs").glob("*.md"))]
    for path in files:
        assert not CONFLICT_MARKER_RE.search(read(path)), f"conflict marker in {path.name}"


def test_cover_asset_exists_and_is_not_empty():
    cover = REPO_ROOT / COVER_PATH
    assert cover.is_file(), "cover image referenced by both READMEs must exist"
    assert cover.stat().st_size > 0


def test_runtime_integrated_claims_are_backed_by_code_and_tests():
    """Any matrix row claiming `runtime-integrated` must map to real runtime
    code and tests in this repository. Plans and manifests do not count."""
    for path in (README_EN, README_ZH, INTEGRATIONS_DOC):
        for line in read(path).splitlines():
            if "runtime-integrated" not in line:
                continue
            stripped = line.lstrip()
            if not stripped.startswith("|"):
                # prose may mention the status
                continue
            if re.match(r"\|\s*`runtime-integrated`\s*\|", stripped):
                # status-vocabulary definition row, not a project claim
                continue
            # A table row making the claim must name a known project with evidence.
            lowered = line.lower()
            evidence = [v for k, v in RUNTIME_EVIDENCE.items() if k in lowered]
            assert evidence, (
                f"{path.name} claims runtime-integrated without registered evidence: {line}"
            )
            for code_path, test_path in evidence:
                assert code_path.is_file(), f"missing runtime code {code_path}"
                assert test_path.is_file(), f"missing runtime test {test_path}"


def test_integration_statuses_in_readmes_use_shared_vocabulary():
    """READMEs may only use statuses defined in docs/integrations.md so the
    condensed matrix cannot drift into invented labels."""
    vocabulary = {
        "recommended-companion",
        "reserved-slot",
        "documented-adapter",
        "optional-bridge",
        "runtime-integrated",
    }
    doc = read(INTEGRATIONS_DOC)
    for status in vocabulary:
        assert f"`{status}`" in doc, f"docs/integrations.md must define `{status}`"

    status_re = re.compile(r"`([a-z]+(?:-[a-z]+)+)`")
    known_non_status = {"read-only", "local-first", "human-in-the-loop", "toy-only", "after-close"}
    for path in (README_EN, README_ZH):
        in_matrix = False
        for line in read(path).splitlines():
            if line.startswith("## "):
                in_matrix = "Integration Matrix" in line or "集成矩阵" in line
                continue
            if not in_matrix or not line.lstrip().startswith("|"):
                continue
            for token in status_re.findall(line):
                if token in known_non_status:
                    continue
                if token.count("-") >= 1 and any(
                    token.startswith(prefix)
                    for prefix in ("recommended", "reserved", "documented", "optional", "runtime", "catalog", "adapter")
                ):
                    assert token in vocabulary, (
                        f"{path.name} uses undefined integration status `{token}`"
                    )
