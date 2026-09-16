"""Study result model."""

from __future__ import annotations

from pydantic import Field

from gwascatalog.mcp.models.results.ancestry import AncestryResult
from gwascatalog.mcp.models.results.baseresult import BaseResult
from gwascatalog.mcp.models.results.traits import TraitResult


class StudyResult(BaseResult):
    """A single GWAS study result with ancestry details."""

    accession_id: str
    initial_sample_size: str | None = None
    replication_sample_size: str | None = None
    gxe: bool | None = None
    gxg: bool | None = None
    snp_count: int | None = None
    full_summary_stats_available: bool | None = None
    full_summary_stats: str | None = None
    terms_of_license: str | None = None
    pubmed_id: int | None = None
    platforms: str | None = None
    disease_trait: str | None = None
    genotyping_technologies: list[str] = Field(default_factory=list)
    efo_traits: list[TraitResult] = Field(default_factory=list)
    discovery_ancestry: list[str] = Field(default_factory=list)
    replication_ancestry: list[str] = Field(default_factory=list)
    cohort: list[str] = Field(default_factory=list)
    ancestries: list[AncestryResult] = Field(default_factory=list)
