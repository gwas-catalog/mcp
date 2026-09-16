"""Release metadata stays consistent across packaging formats."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


def test_helm_app_version_matches_package_version():
    package = tomllib.loads(Path("pyproject.toml").read_text())
    chart = Path("deployment/helm/Chart.yaml").read_text()
    app_version = re.search(r'^appVersion: "(.+)"$', chart, re.MULTILINE)

    assert app_version is not None
    assert app_version.group(1) == package["project"]["version"]
