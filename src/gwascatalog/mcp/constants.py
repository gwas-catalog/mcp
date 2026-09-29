import os
from importlib.metadata import version

USER_AGENT = f"gwascatalog-mcp/{version('gwas-mcp')}"

GWASCATALOG_MCP_INSTRUCTIONS = """
Provides access to curated results from the GWAS Catalog, a     database of
published human genome-wide association (GWAS) studies

Use these tools to explore genome-wide association studies, including:
genetic variants, SNP-trait associations, mapped genes, traits and diseases,
GWAS studies and publications, and ancestry information describing the
study populations.

Use this server when answering questions about genetic variants linked
to traits or diseases, GWAS study results, or the populations in which
associations were discovered.
"""

TRAIT_SEARCH_GUIDANCE = (
    "If you prefer to first identify a wider range of relevant traits, start "
    "with the `gwascatalog_get_traits` tool using free-text search with the efo_trait "
    "parameter. For example, "
    "'COVID-19' may return related traits like 'long COVID-19' or "
    "'response to COVID-19 vaccine'.\n\n"
    "For precision, prefer EFO IDs (e.g. MONDO_0004979) over names."
)

COHORT_SEARCH_GUIDANCE = """
Cohorts are recorded with a controlled vocabulary (Cohort ID). Users may provide
cohort names in the query (Cohort Name). When setting the cohort parameter always
use map cohort names to a cohort ID by looking at the controlled vocabulary resource:

gwascatalog://reference/cohorts
"""
HTTP_PROXY = os.getenv("GWASCATALOG_HTTP_PROXY", None)
HTTP_TIMEOUT = 10
