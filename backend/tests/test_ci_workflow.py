"""Regression tests for TECH-02: CI workflow integration and static validation.

Verifies:
1. .github/workflows/ci.yml exists and parses as valid YAML.
2. Required triggers (push, pull_request) and concurrency controls are present.
3. Jobs are defined for both backend and frontend.
4. Working directories match actual workspace directories.
5. Critical quality checks are invoked (backend pytest, frontend lint, test, build).
6. Timeouts are explicitly configured.
7. No secrets or credentials are hardcoded.
"""

from pathlib import Path
import pytest

try:
    import yaml
except ImportError:
    yaml = None


def get_workflow_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_file_exists():
    """Verify that .github/workflows/ci.yml is present in the repository."""
    workflow_path = get_workflow_path()
    assert workflow_path.is_file(), f"CI workflow file not found at {workflow_path}"


def test_ci_workflow_yaml_structure():
    """Verify that ci.yml has valid syntax and expected top-level keys."""
    workflow_path = get_workflow_path()
    content = workflow_path.read_text(encoding="utf-8")

    if yaml is not None:
        data = yaml.safe_load(content)
        assert isinstance(data, dict), "Workflow YAML must parse as a dictionary"
        assert "name" in data
        assert "on" in data
        assert "jobs" in data

        # Check triggers
        triggers = data["on"]
        assert "push" in triggers
        assert "pull_request" in triggers

        # Check jobs
        jobs = data["jobs"]
        assert "backend-test" in jobs
        assert "frontend-test" in jobs
        assert "frontend-e2e" in jobs

        # Check backend job
        b_job = jobs["backend-test"]
        assert b_job.get("timeout-minutes", 0) > 0
        assert b_job.get("defaults", {}).get("run", {}).get("working-directory") == "backend"

        # Check frontend job
        f_job = jobs["frontend-test"]
        assert f_job.get("timeout-minutes", 0) > 0
        assert f_job.get("defaults", {}).get("run", {}).get("working-directory") == "frontend"

        # Verify artifact upload in frontend-test
        f_steps = f_job.get("steps", [])
        upload_steps = [s for s in f_steps if "upload-artifact" in s.get("uses", "")]
        assert len(upload_steps) == 1, "frontend-test must upload production build artifact"
        upload_with = upload_steps[0].get("with", {})
        assert upload_with.get("name") == "frontend-dist"
        assert upload_with.get("path") == "frontend/dist"

        # Check frontend E2E job
        e2e_job = jobs["frontend-e2e"]
        assert e2e_job.get("timeout-minutes", 0) > 0
        assert e2e_job.get("defaults", {}).get("run", {}).get("working-directory") == "frontend"
        assert e2e_job.get("needs") == ["frontend-test"]

        # Verify artifact download in frontend-e2e
        e2e_steps = e2e_job.get("steps", [])
        download_steps = [s for s in e2e_steps if "download-artifact" in s.get("uses", "")]
        assert len(download_steps) == 1, "frontend-e2e must download production build artifact"
        download_with = download_steps[0].get("with", {})
        assert download_with.get("name") == "frontend-dist"
        assert download_with.get("path") == "frontend/dist"
    else:
        # Fallback string validation if PyYAML is not installed
        assert "name: CI" in content
        assert "backend-test:" in content
        assert "frontend-test:" in content
        assert "frontend-e2e:" in content
        assert "working-directory: backend" in content
        assert "working-directory: frontend" in content
        assert "upload-artifact" in content
        assert "download-artifact" in content
        assert "frontend-dist" in content


def test_ci_workflow_invokes_critical_commands():
    """Verify that CI workflow invokes backend pytest, frontend lint, test, build, artifact transfer, and E2E tests."""
    workflow_path = get_workflow_path()
    content = workflow_path.read_text(encoding="utf-8")

    assert "pytest tests" in content
    assert "npm run lint" in content
    assert "npm test" in content
    assert "npm run build" in content
    assert "upload-artifact" in content
    assert "download-artifact" in content
    assert "frontend-dist" in content
    assert "npm run test:e2e" in content
    assert "cancel-in-progress: true" in content


def test_ci_workflow_no_duplicate_e2e_build():
    """Verify that frontend-e2e does not execute a duplicate npm run build step."""
    workflow_path = get_workflow_path()
    content = workflow_path.read_text(encoding="utf-8")

    if yaml is not None:
        data = yaml.safe_load(content)
        e2e_job = data["jobs"]["frontend-e2e"]
        e2e_steps = e2e_job.get("steps", [])
        for step in e2e_steps:
            run_cmd = step.get("run", "")
            assert "npm run build" not in run_cmd, (
                f"frontend-e2e contains redundant build step '{step.get('name')}': {run_cmd}"
            )
    else:
        # Fallback check
        e2e_section = content.split("frontend-e2e:")[-1]
        assert "npm run build" not in e2e_section


def test_ci_workflow_does_not_leak_real_secrets():
    """Verify that CI workflow does not hardcode live API keys or credentials."""
    workflow_path = get_workflow_path()
    content = workflow_path.read_text(encoding="utf-8")

    # Ensure no live AIza... Google API keys exist
    assert "AIza" not in content
    # Ensure any dummy keys are clearly designated as mock
    if "GOOGLE_API_KEY" in content:
        assert "mock" in content.lower()
