import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
SCRIPT_NAMES = {
    "clean_start",
    "onboard",
    "run",
    "run_tests",
    "full_test",
    "tidy",
    "check",
    "package",
}


def test_project_workflow_scripts_are_present_and_executable() -> None:
    for script_name in SCRIPT_NAMES:
        script = PROJECT_ROOT / script_name
        assert script.is_file(), f"missing project script: {script_name}"
        assert os.access(script, os.X_OK), f"script is not executable: {script_name}"
        assert script.read_text().startswith("#!/usr/bin/env bash\n")
