from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_uses_tagged_trusted_publishing():
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert 'tags: ["v*"]' in workflow
    assert 'environment: pypi' in workflow
    assert 'id-token: write' in workflow
    assert 'pypa/gh-action-pypi-publish@release/v1' in workflow
    assert 'PYPI_TOKEN' not in workflow
    assert 'password:' not in workflow


def test_release_workflow_validates_version_and_publishes_release_assets():
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert 'Verify tag matches package version' in workflow
    assert 'python -m build' in workflow
    assert 'actions/upload-artifact@v4' in workflow
    assert 'actions/download-artifact@v4' in workflow
    assert 'needs: pypi-publish' in workflow
    assert 'gh release create' in workflow
    assert 'dist/*' in workflow
