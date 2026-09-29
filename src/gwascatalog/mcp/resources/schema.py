"""GWAS Catalog OpenAPI schema resource."""

from __future__ import annotations

import logging
from importlib import resources as importlib_resources

import httpx

from gwascatalog.mcp.constants import HTTP_PROXY, HTTP_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

_SCHEMA_URL = "https://www.ebi.ac.uk/gwas/rest/api/v2/rest-api-doc.yaml"


def _read_bundled_schema() -> str:
    return (
        importlib_resources.files("gwascatalog.mcp.data")
        .joinpath("rest-api-doc.yaml")
        .read_text("utf-8")
    )


async def fetch_schema() -> str:
    """Return the GWAS Catalog REST API v2 OpenAPI schema as YAML."""
    if HTTP_PROXY is None:
        logger.info("No proxy is set")
    else:
        logger.info(f"{HTTP_PROXY=}")

    try:
        async with httpx.AsyncClient(
            proxy=HTTP_PROXY, headers={"User-Agent": USER_AGENT}
        ) as client:
            response = await client.get(
                _SCHEMA_URL, timeout=HTTP_TIMEOUT, follow_redirects=True
            )
            response.raise_for_status()
            return response.text
    except Exception:
        logger.exception(
            f"Failed to fetch schema from {_SCHEMA_URL}; using bundled data"
        )
        return _read_bundled_schema()
