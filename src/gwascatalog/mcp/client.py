"""Async GWAS Catalog API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

import httpx

from gwascatalog.mcp.constants import USER_AGENT

_STUDY_SORT_FIELDS = {"accession_id": "accession_Id"}

if TYPE_CHECKING:
    from gwascatalog.mcp.models import (
        GetAssociationsParams,
        GetStudiesParams,
        GetTraitsParams,
    )


class NotFoundError(RuntimeError):
    """Raised when the GWAS Catalog API returns 404 for a resource."""


class FetchResult(TypedDict):
    """Normalized result from a GWAS Catalog API list/detail endpoint.

    items: list of raw JSON objects (one item for single-ID lookups).
    page:  raw pagination dict from the API, or None for single-ID lookups.
    """

    items: list[dict[str, Any]]
    page: dict[str, Any] | None


class GwasCatalogClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.get(path, params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundError(f"Resource not found (404) for {path}") from exc
            raise RuntimeError(
                f"GWAS API request failed ({exc.response.status_code})"
                f" for {path}: {exc.response.text}"
            ) from exc
        return response.json()

    async def get_studies(self, params: GetStudiesParams) -> FetchResult:
        if params.accession_id is not None:
            try:
                data = await self.get(f"/v2/studies/{params.accession_id}")
            except NotFoundError:
                return FetchResult(items=[], page=None)
            return FetchResult(items=[data], page=None)
        query = params.model_dump(exclude_none=True)
        if query.get("sort") in _STUDY_SORT_FIELDS:
            query["sort"] = _STUDY_SORT_FIELDS[query["sort"]]
        data = await self.get("/v2/studies", params=query)
        return FetchResult(
            items=data.get("_embedded", {}).get("studies", []),
            page=data.get("page"),
        )

    async def get_study_ancestries(self, accession_id: str) -> list[dict[str, Any]]:
        data = await self.get(f"/v2/studies/{accession_id}/ancestries")
        return data.get("_embedded", {}).get("ancestries", [])

    async def get_associations(self, params: GetAssociationsParams) -> FetchResult:
        if params.association_id is not None:
            try:
                data = await self.get(f"/v2/associations/{params.association_id}")
            except NotFoundError:
                return FetchResult(items=[], page=None)
            return FetchResult(items=[data], page=None)
        query = params.model_dump(exclude_none=True)
        if query.get("sort") == "risk_frequency" and query.get("direction") == "asc":
            # ponytail: current REST API returns 500 for this valid MCP query.
            del query["direction"]
        data = await self.get("/v2/associations", params=query)
        return FetchResult(
            items=data.get("_embedded", {}).get("associations", []),
            page=data.get("page"),
        )

    async def get_association_loci(self, association_id: int) -> list[dict[str, Any]]:
        data = await self.get(f"/v2/associations/{association_id}/loci")
        return data.get("_embedded", {}).get("loci", [])

    async def get_efo_traits(self, params: GetTraitsParams) -> FetchResult:
        if params.efo_id is not None:
            try:
                data = await self.get(f"/v2/efo-traits/{params.efo_id}")
            except NotFoundError:
                return FetchResult(items=[], page=None)
            return FetchResult(items=[data], page=None)
        query = params.model_dump(exclude_none=True)
        data = await self.get("/v2/efo-traits", params=query)
        return FetchResult(
            items=data.get("_embedded", {}).get("efo_traits", []),
            page=data.get("page"),
        )
