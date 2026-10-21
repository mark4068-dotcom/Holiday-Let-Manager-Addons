"""Validate tracked JSON and release version contracts."""
import json
import re
import subprocess
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
tracked = subprocess.check_output(
    ["git", "ls-files", "-z"], cwd=ROOT
).decode().split("\0")
for name in tracked:
    if name.endswith(".json"):
        json.loads((ROOT / name).read_text())
for config in ROOT.glob("*/config.yaml"):
    data = yaml.safe_load(config.read_text())
    version = str(data["version"])
    package = config.with_name("package.json")
    if package.exists():
        assert json.loads(package.read_text())["version"] == version, config
        lock = json.loads(package.with_name("package-lock.json").read_text())
        assert lock["version"] == version, package
        assert lock["packages"][""]["version"] == version, package
    docker = config.with_name("Dockerfile")
    if docker.exists():
        text = docker.read_text()
        match = re.search(r"^ARG BUILD_VERSION=(.+)$", text, re.M)
        if match:
            assert match[1] == version, docker
        assert ":latest" not in text, docker
        assert "@sha256:" in text, docker
project = ROOT / "pyproject.toml"
if project.exists():
    metadata = tomllib.loads(project.read_text()).get("project", {})
    if "version" in metadata:
        for manifest in ROOT.glob("**/custom_components/*/manifest.json"):
            if ".venv" in manifest.parts:
                continue
            actual = json.loads(manifest.read_text())["version"]
            assert actual == metadata["version"], manifest
for workflow in (ROOT / ".github").rglob("*.yml"):
    yaml.safe_load(workflow.read_text())
print("JSON, workflows and release versions validated")
