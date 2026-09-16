"""Guard CI jobs from appearing without their required inputs."""

from __future__ import annotations

from pathlib import Path


def test_production_deploy_is_tag_only():
    pipeline = Path(".gitlab-ci.yml").read_text()

    assert "deploy_production_tag:" not in pipeline
    assert "CI_COMMIT_TAG =~ /^v" in pipeline


def test_ci_uses_helm_3():
    pipeline = Path(".gitlab-ci.yml").read_text()

    assert "dtzar/helm-kubectl:3.19.1" in pipeline
    assert "dtzar/helm-kubectl:4." not in pipeline
