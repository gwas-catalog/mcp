#!/usr/bin/env -S uv run
# /// script
# dependencies = ["nox"]
# ///

from __future__ import annotations

import nox

# Use uv for environment creation and package installation
nox.options.default_venv_backend = "uv"
nox.options.sessions = ["lint", "tests"]


@nox.session
def tests(session):
    session.install(".")

    # Install test tooling
    session.install("pytest", "coverage", "pytest-asyncio")

    # Run tests under coverage
    session.run("coverage", "run", "-m", "pytest", "tests")

    # Coverage report (terminal)
    session.run(
        "coverage",
        "report",
        "-m",
        "--fail-under",
        "90",
    )


@nox.session
def lint(session):
    # Install workspace packages (so type checking resolves imports)
    session.install(".")

    # manually install pydantic (this is OK, remember the web app)
    session.install("pydantic")

    # Lint + format + typing tools
    session.install("ruff", "ty")

    # Format check (fails if reformatting needed)
    session.run("ruff", "format", "--check", ".")

    # Lint
    session.run("ruff", "check", ".")

    # Type checking
    # session.run("ty", "check", "src")


@nox.session(venv_backend="none")
def build_image(session: nox.Session) -> None:
    """Build a dev or release image."""
    if not session.posargs:
        session.error("Specify a version, e.g.: nox -s build_image -- 1.0.4")
    session.run("python", "scripts/publish_image.py", *session.posargs, external=True)


@nox.session(venv_backend="none")
def helm(session: nox.Session) -> None:
    """Validate both Helm environments and startup-probe compatibility paths."""
    for environment, kube_version in (("dev", "1.19.0"), ("prod", "1.20.0")):
        values = f"deployment/helm/values-{environment}.yaml"
        session.run("helm", "lint", "deployment/helm", "-f", values, external=True)
        session.run(
            "helm",
            "template",
            "ci-check",
            "deployment/helm",
            "-f",
            values,
            "--kube-version",
            kube_version,
            external=True,
            silent=True,
        )


if __name__ == "__main__":
    nox.main()
