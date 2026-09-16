"""GWAS Catalog MCP server."""

from __future__ import annotations

import argparse
import logging
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Literal

from gwascatalog.mcp.telemetry import (
    init_telemetry,
    record_list_request,
    record_resource_access,
    record_tool_call,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import httpx

from gwascatalog.mcp.client import GwasCatalogClient
from gwascatalog.mcp.config import Settings
from gwascatalog.mcp.constants import (
    COHORT_SEARCH_GUIDANCE,
    GWASCATALOG_MCP_INSTRUCTIONS,
    TRAIT_SEARCH_GUIDANCE,
)
from gwascatalog.mcp.models import (
    URI,
    AccessionId,
    AncestralGroup,
    AssociationId,
    AssociationResult,
    AssociationSortKeyField,
    Cohort,
    DiseaseTrait,
    EfoId,
    EfoTrait,
    FullPValueSet,
    GetAssociationsParams,
    GetStudiesParams,
    GetTraitsParams,
    GxE,
    MappedGene,
    PageField,
    PubmedId,
    RsId,
    ShowChildTrait,
    SizeField,
    SortDirectionField,
    StudyResult,
    StudySortKeyField,
    ToolResponse,
    TraitResult,
    TraitSortKeyField,
)
from gwascatalog.mcp.resources import (
    fetch_cohorts,
    fetch_schema,
    read_ancestry_labels,
    read_variant_consequences,
)
from gwascatalog.mcp.tools import get_associations, get_studies, get_traits
from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

logger = logging.getLogger(__name__)
settings = Settings()
_MCP_BROWSER_FALLBACK_HTML = b"""<!doctype html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>GWAS Catalog MCP endpoint</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      margin: 0;
      font: 16px/1.5 system-ui, sans-serif;
      display: grid;
      min-height: 100vh;
      place-items: center;
    }
    main { max-width: 42rem; padding: 2rem; }
  </style>
</head>
<body>
  <main>
    <h1>GWAS Catalog MCP endpoint</h1>
    <p>
      This is a Model Context Protocol endpoint for agents and agentic IDEs
      such as Codex or Claude Code. It is not a normal web page.
    </p>
    <p>
      For human-readable information, visit the
      <a href="https://github.com/EBISPOT/gwas-mcp">documentation</a>.
    </p>
  </main>
</body>
</html>
"""
MCP_TOOL_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


@asynccontextmanager
async def lifespan(_: MCPServer) -> AsyncIterator[dict[str, Any]]:
    client = GwasCatalogClient(settings.api_base_url, settings.timeout_seconds)
    try:
        yield {"client": client}
    finally:
        await client.close()


mcp = MCPServer(
    name="gwascatalog",
    instructions=GWASCATALOG_MCP_INSTRUCTIONS,
    lifespan=lifespan,
)


def _get_client(ctx: Context) -> GwasCatalogClient:
    return ctx.request_context.lifespan_context["client"]


def _is_browser_navigation(scope: dict[str, Any], path: str) -> bool:
    if scope.get("type") != "http":
        return False
    if scope.get("method") not in {"GET", "HEAD"}:
        return False
    if scope.get("path") != path:
        return False

    headers = {
        key.decode("latin-1").lower(): value.decode("latin-1").lower()
        for key, value in scope.get("headers", [])
    }
    return (
        "text/html" in headers.get("accept", "")
        or headers.get("sec-fetch-dest") == "document"
        or headers.get("sec-fetch-mode") == "navigate"
    )


def _with_browser_fallback(app: Any, path: str) -> Any:
    async def wrapped(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if not _is_browser_navigation(scope, path):
            await app(scope, receive, send)
            return

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/html; charset=utf-8"),
                    (b"content-length", str(len(_MCP_BROWSER_FALLBACK_HTML)).encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b""
                if scope.get("method") == "HEAD"
                else _MCP_BROWSER_FALLBACK_HTML,
            }
        )

    return wrapped


def streamable_http_app() -> Any:
    return _with_browser_fallback(
        mcp.streamable_http_app(
            host=settings.host,
            streamable_http_path=settings.streamable_http_path,
            stateless_http=True,
        ),
        settings.streamable_http_path,
    )


# ---- Listing telemetry ----

_original_list_tools = mcp.list_tools
_original_list_resources = mcp.list_resources


async def _instrumented_list_tools() -> list:
    record_list_request("tools")
    return await _original_list_tools()


async def _instrumented_list_resources() -> list:
    record_list_request("resources")
    return await _original_list_resources()


mcp.list_tools = _instrumented_list_tools
mcp.list_resources = _instrumented_list_resources


# ---- Resources ----


_RESOURCE_INDEX = """\
GWAS Catalog MCP — resource index
==================================

Capabilities (human GWAS data):

Traits (EFO traits): gwascatalog_get_traits
Studies (GWAS studies): gwascatalog_get_studies
Associations (variant-trait): gwascatalog_get_associations

## Use tools first

Resources contain static reference lists and are usually not required for
typical GWAS queries.

The MCP tools query live GWAS Catalog data and should be your first choice:

- gwascatalog_get_traits
  Returns: EFO trait metadata
  Query by: EFO ID, trait name, mapped gene, PubMed ID, URI
- gwascatalog_get_studies
  Returns: GWAS study metadata
  Query by: study accession, trait, gene, ancestry, cohort, PubMed ID
- gwascatalog_get_associations
  Returns: SNP-trait association records
  Query by: association ID, trait, gene, variant, study accession, PubMed ID

Load a resource only when you need a controlled vocabulary or valid identifier.

Examples:
- checking valid ancestry labels
- validating cohort identifiers
- verifying variant consequence terms

## Typical workflows:

1. Find traits using gwascatalog_get_traits
2. Find related studies using gwascatalog_get_studies with the returned trait

or

1. Find traits using gwascatalog_get_traits
2. Retrieve SNP associations using gwascatalog_get_associations with the returned trait

## When presenting results

* When summarising a study, include ancestry information to provide context for the
study population.

## Available resources

- gwascatalog://docs/index
    Use when: first accessing the MCP to understand available resources
    Content: This index of resources and usage guidance
- gwascatalog://docs/terms-of-use
    Use when: checking terms that govern GWAS Catalog and data usage
    Content: Link to the current EMBL-EBI Terms of Use
- gwascatalog://reference/cohorts
    Use when: validating cohort identifiers
    Content: PGS Catalog cohort IDs and names
- gwascatalog://ancestry-labels
    Use when: validating ancestry group labels
    Content: Ancestry categories, descriptions, and example sub-populations
- gwascatalog://reference/variant-consequences
    Use when: validating variant consequence terms
    Content: Sequence Ontology terms, accessions, display names, and IMPACT ratings
- gwascatalog://reference/openapi-schema
    Use when: building custom integrations or processing large datasets outside MCP
    Content: OpenAPI schema for GWAS Catalog REST API v2

## Custom integrations

If you need to query or process very large amounts of GWAS Catalog data, then write
a custom integration with the GWAS Catalog REST API.

Use gwascatalog://reference/openapi-schema only for building external integrations
or processing very large datasets outside MCP.

Normal analysis tasks should use MCP tools.
"""


@mcp.resource(
    "gwascatalog://docs/index",
    name="index",
    title="GWAS Catalog MCP Resource Index",
    description=(
        "Compact index of all available resources with brief descriptions. "
        "Read this first to decide which resource (if any) to load. "
        "Prefer MCP tools over resources for live data queries."
    ),
    mime_type="text/plain",
)
async def gwascatalog_index() -> str:
    record_resource_access("index")
    logger.info("Returning index resource")
    return _RESOURCE_INDEX


@mcp.resource(
    "gwascatalog://docs/terms-of-use",
    name="terms_of_use",
    title="EMBL-EBI Terms of Use",
    description="Current terms governing GWAS Catalog and data usage.",
    mime_type="text/plain",
)
async def gwascatalog_terms_of_use() -> str:
    record_resource_access("terms_of_use")
    return "https://www.ebi.ac.uk/about/terms-of-use/\n"


@mcp.resource(
    "gwascatalog://reference/cohorts",
    name="cohorts",
    title="GWAS Catalog Cohorts",
    description=(
        "Controlled vocabulary of cohort identifiers and names from the GWAS Catalog. "
    ),
    mime_type="application/json",
)
async def gwascatalog_cohorts() -> dict:
    record_resource_access("cohorts")
    return await fetch_cohorts()


@mcp.resource(
    "gwascatalog://ancestry-labels",
    name="ancestry_labels",
    title="GWAS Catalog Ancestry Labels",
    description=(
        "Ancestry categories used to classify study participants in the GWAS Catalog, "
        "from Morales et al. 2018 (doi:10.1186/s13059-018-1396-2). "
        "Includes broad ancestral group labels, descriptions, "
        "and example sub-populations."
    ),
    mime_type="application/json",
)
async def gwascatalog_ancestry_labels() -> dict:
    record_resource_access("ancestry_labels")
    return read_ancestry_labels()


@mcp.resource(
    "gwascatalog://reference/variant-consequences",
    name="variant_consequences",
    title="Ensembl Variant Consequences",
    description=(
        "Sequence Ontology (SO) consequence terms used to annotate variant effects "
        "on transcripts, ordered by severity. Sourced from Ensembl. "
        "Includes SO term, accession, display name, and IMPACT rating."
    ),
    mime_type="application/json",
)
async def gwascatalog_variant_consequences() -> dict:
    record_resource_access("variant_consequences")
    return read_variant_consequences()


@mcp.resource(
    "gwascatalog://reference/openapi-schema",
    name="openapi_schema",
    title="GWAS Catalog REST API v2 OpenAPI Schema",
    description=(
        "Full OpenAPI specification for the GWAS Catalog REST API v2, in YAML format. "
        "Use this only if you need to understand endpoint structure, "
        "request parameters, or response shapes beyond what the MCP tools expose. "
    ),
    mime_type="text/yaml",
)
async def gwascatalog_openapi_schema() -> str:
    record_resource_access("openapi_schema")
    return await fetch_schema()


# ---- Traits tool ----

TERMS_OF_USE_GUIDANCE = """
Terms of use: gwascatalog://docs/terms-of-use
"""


TRAIT_TOOL_DESCRPTION = f"""
Search and browse Experimental Factor Ontology (EFO) terms in the GWAS Catalog.

For an overview of available tools, workflows, and reference resources see:
gwascatalog://docs/index

{TERMS_OF_USE_GUIDANCE}

This tool can be helpful to explore the traits present in the GWAS Catalog. If
the trait is present in the GWAS Catalog, there will be studies
and associations linked with it.

Trait search guidance:

If an efo_id doesn't appear in the GWAS Catalog, try searching with efo_trait instead.

This will do simple text matching to return any traits that include the term.

efo_id is most precise and will return a single result generally.

CAUTION: Trait synonyms are not matched when searching efo_trait. For example:

- MONDO_0005148 is equivalent to "type 2 diabetes mellitus"
- Searching efo_trait with "type 2 diabetes mellitus" will return a result including
MONDO_0005148
- However, searching efo_trait with "adult-onset diabetes" (which is a MONDO_0005148
synonym) will not return any results

In this case try searching more general terms to find traits (e.g. "type 2 diabetes")
before filtering them.
"""


@mcp.tool(annotations=MCP_TOOL_ANNOTATIONS, description=TRAIT_TOOL_DESCRPTION)
async def gwascatalog_get_traits(
    ctx: Context,
    efo_id: EfoId | None = None,
    efo_trait: EfoTrait | None = None,
    mapped_gene: MappedGene | None = None,
    pubmed_id: PubmedId | None = None,
    uri: URI | None = None,
    page: PageField = 0,
    size: SizeField = 10,
    sort: TraitSortKeyField | None = None,
    direction: SortDirectionField = "asc",
) -> ToolResponse[TraitResult]:
    params = GetTraitsParams(
        efo_id=efo_id,
        efo_trait=efo_trait,
        mapped_gene=mapped_gene,
        pubmed_id=pubmed_id,
        uri=uri,
        page=page,
        size=size,
        sort=sort,
        direction=direction,
    )
    t0 = time.perf_counter()
    try:
        result = await get_traits(client=_get_client(ctx), params=params)
    except httpx.HTTPError:
        record_tool_call(
            "get_traits",
            result_count=0,
            duration_s=time.perf_counter() - t0,
            error_type="upstream",
        )
        raise
    except Exception:
        logger.exception("gwascatalog_get_traits internal error")
        record_tool_call(
            "get_traits",
            result_count=0,
            duration_s=time.perf_counter() - t0,
            error_type="internal",
        )
        raise
    record_tool_call(
        "get_traits", result_count=len(result.data), duration_s=time.perf_counter() - t0
    )
    return result


# ---- Studies tool ----

STUDY_TOOL_DESCRIPTION = f"""
Find GWAS Catalog studies by trait, ancestry, gene, or accession.

For an overview of available tools, workflows, and reference resources see:
gwascatalog://docs/index

{TERMS_OF_USE_GUIDANCE}

Trait search guidance:

{TRAIT_SEARCH_GUIDANCE}

Cohort search guidance:

{COHORT_SEARCH_GUIDANCE}
"""


@mcp.tool(annotations=MCP_TOOL_ANNOTATIONS, description=STUDY_TOOL_DESCRIPTION)
async def gwascatalog_get_studies(
    ctx: Context,
    accession_id: AccessionId | None = None,
    efo_trait: EfoTrait | None = None,
    efo_id: EfoId | None = None,
    disease_trait: DiseaseTrait | None = None,
    mapped_gene: MappedGene | None = None,
    pubmed_id: PubmedId | None = None,
    ancestral_group: AncestralGroup | None = None,
    cohort_id: Cohort | None = None,
    full_pvalue_set: FullPValueSet | None = None,
    gxe: GxE | None = None,
    show_child_trait: ShowChildTrait | None = None,
    page: PageField = 0,
    size: SizeField = 10,
    sort: StudySortKeyField | None = None,
    direction: SortDirectionField = "asc",
) -> ToolResponse[StudyResult]:
    params = GetStudiesParams(
        accession_id=accession_id,
        efo_trait=efo_trait,
        efo_id=efo_id,
        disease_trait=disease_trait,
        mapped_gene=mapped_gene,
        pubmed_id=pubmed_id,
        ancestral_group=ancestral_group,
        cohort=cohort_id,
        full_pvalue_set=full_pvalue_set,
        gxe=gxe,
        show_child_trait=show_child_trait,
        page=page,
        size=size,
        sort=sort,
        direction=direction,
    )

    t0 = time.perf_counter()
    try:
        result = await get_studies(client=_get_client(ctx), params=params)
    except httpx.HTTPError:
        record_tool_call(
            "get_studies",
            result_count=0,
            duration_s=time.perf_counter() - t0,
            error_type="upstream",
        )
        raise
    except Exception:
        logger.exception("gwascatalog_get_studies internal error")
        record_tool_call(
            "get_studies",
            result_count=0,
            duration_s=time.perf_counter() - t0,
            error_type="internal",
        )
        raise
    record_tool_call(
        "get_studies",
        result_count=len(result.data),
        duration_s=time.perf_counter() - t0,
    )
    return result


# ---- Associations tool ----

ASSOCATION_TOOL_DESCRIPTION = f"""
Find variant-trait associations with statistical details from the GWAS Catalog.

For an overview of available tools, workflows, and reference resources see:
gwascatalog://docs/index

{TERMS_OF_USE_GUIDANCE}

Result sorting guidance:

1. To identify the most statistically significant results, sort by pvalue ascending.
2. To identify the largest positive effects, sort by or_value descending.
3. To identify the strongest protective effects (odds ratios below 1), sort by or_value
ascending.

Trait search guidance:

{TRAIT_SEARCH_GUIDANCE}
"""


@mcp.tool(annotations=MCP_TOOL_ANNOTATIONS, description=ASSOCATION_TOOL_DESCRIPTION)
async def gwascatalog_get_associations(
    ctx: Context,
    association_id: AssociationId | None = None,
    efo_trait: EfoTrait | None = None,
    efo_id: EfoId | None = None,
    rs_id: RsId | None = None,
    mapped_gene: MappedGene | None = None,
    accession_id: AccessionId | None = None,
    pubmed_id: PubmedId | None = None,
    full_pvalue_set: FullPValueSet | None = None,
    show_child_trait: ShowChildTrait | None = None,
    page: PageField = 0,
    size: SizeField = 10,
    sort: AssociationSortKeyField | None = None,
    # desc default suggested for snp count
    direction: SortDirectionField = "desc",
) -> ToolResponse[AssociationResult]:
    params = GetAssociationsParams(
        association_id=association_id,
        efo_trait=efo_trait,
        efo_id=efo_id,
        rs_id=rs_id,
        mapped_gene=mapped_gene,
        accession_id=accession_id,
        pubmed_id=pubmed_id,
        full_pvalue_set=full_pvalue_set,
        show_child_trait=show_child_trait,
        page=page,
        size=size,
        sort=sort,
        direction=direction,
    )

    t0 = time.perf_counter()
    try:
        result = await get_associations(
            client=_get_client(ctx),
            params=params,
        )
    except httpx.HTTPError:
        record_tool_call(
            "get_associations",
            result_count=0,
            duration_s=time.perf_counter() - t0,
            error_type="upstream",
        )
        raise
    except Exception:
        logger.exception("gwascatalog_get_associations internal error")
        record_tool_call(
            "get_associations",
            result_count=0,
            duration_s=time.perf_counter() - t0,
            error_type="internal",
        )
        raise
    record_tool_call(
        "get_associations",
        result_count=len(result.data),
        duration_s=time.perf_counter() - t0,
    )
    return result


# ---- CLI ----


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GWAS Catalog MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="Transport mode: stdio or streamable HTTP.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host address to bind to. Use 0.0.0.0 for containers.",
    )
    parser.add_argument(
        "--port",
        default=None,
        help="Port to bind to. Defaults to 8000.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    transport: Literal["streamable-http", "stdio"] = (
        "streamable-http" if args.transport == "http" else "stdio"
    )

    if transport == "streamable-http":
        logger.info("Starting telemetry server")
        init_telemetry()

    logger.info(
        "Starting MCP server: transport=%s host=%s port=%s",
        transport,
        settings.host,
        settings.port,
    )
    if transport == "stdio":
        mcp.run(transport=transport)
        return

    import uvicorn

    uvicorn.run(
        streamable_http_app(),
        host=settings.host,
        port=settings.port,
        log_level=mcp.settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
