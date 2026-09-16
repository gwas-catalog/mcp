"""Unit tests for GWAS Catalog MCP tools."""

from __future__ import annotations

from gwascatalog.mcp.server import (
    gwascatalog_get_associations,
    gwascatalog_get_studies,
    gwascatalog_get_traits,
)

# ---- Traits tests ----


async def test_get_traits_list(mock_ctx, mock_client):
    mock_client.get_efo_traits.return_value = {
        "items": [
            {
                "efo_trait": "celiac disease",
                "uri": "http://www.ebi.ac.uk/efo/EFO_0001060",
                "efo_id": "EFO_0001060",
            },
            {
                "efo_trait": "type 2 diabetes mellitus",
                "uri": "http://www.ebi.ac.uk/efo/EFO_0001360",
                "efo_id": "EFO_0001360",
            },
        ],
        "page": {
            "size": 10,
            "totalElements": 2,
            "totalPages": 1,
            "number": 0,
        },
    }

    result = await gwascatalog_get_traits(mock_ctx, efo_trait="diabetes")
    assert len(result.data) == 2
    assert result.data[0].efo_id == "EFO_0001060"
    assert result.data[1].efo_id == "EFO_0001360"
    assert result.pagination.total_results == 2
    assert result.pagination.truncated is False


async def test_get_traits_detail(mock_ctx, mock_client):
    mock_client.get_efo_traits.return_value = {
        "items": [
            {
                "efo_trait": "celiac disease",
                "uri": "http://www.ebi.ac.uk/efo/EFO_0001060",
                "efo_id": "EFO_0001060",
            },
        ],
        "page": None,
    }

    result = await gwascatalog_get_traits(
        mock_ctx,
        efo_id="EFO_0001060",
    )
    assert len(result.data) == 1
    assert result.data[0].efo_id == "EFO_0001060"
    assert result.data[0].efo_trait == "celiac disease"
    assert result.pagination.total_results == 1
    assert result.pagination.truncated is False


async def test_get_traits_empty(mock_ctx, mock_client):
    mock_client.get_efo_traits.return_value = {
        "items": [],
        "page": {
            "size": 10,
            "totalElements": 0,
            "totalPages": 0,
            "number": 0,
        },
    }

    result = await gwascatalog_get_traits(
        mock_ctx,
        efo_trait="nonexistent_xyz",
    )
    assert result.data == []
    assert result.pagination.total_results == 0
    assert result.pagination.truncated is False
    assert len(result.suggestions) > 0
    assert any("No results" in s for s in result.suggestions)


# ---- Studies tests ----


async def test_get_studies_list(mock_ctx, mock_client):
    mock_client.get_studies.return_value = {
        "items": [
            {
                "accession_id": "GCST000854",
                "initial_sample_size": "4,533 cases",
                "disease_trait": "Celiac disease",
                "pubmed_id": 21399633,
                "full_summary_stats": "https://ftp.example/GCST000854",
                "terms_of_license": "https://creativecommons.org/publicdomain/zero/1.0/",
                "efo_traits": [
                    {
                        "efo_id": "EFO_0001060",
                        "efo_trait": "celiac disease",
                    }
                ],
                "discovery_ancestry": ["4533 European (U.K.)"],
            }
        ],
        "page": {
            "size": 10,
            "totalElements": 1,
            "totalPages": 1,
            "number": 0,
        },
    }

    mock_client.get_study_ancestries.return_value = []

    result = await gwascatalog_get_studies(
        mock_ctx,
        efo_trait="celiac disease",
    )
    assert len(result.data) == 1
    assert result.data[0].accession_id == "GCST000854"
    assert result.data[0].disease_trait == "Celiac disease"
    assert result.data[0].full_summary_stats == "https://ftp.example/GCST000854"
    assert (
        result.data[0].terms_of_license
        == "https://creativecommons.org/publicdomain/zero/1.0/"
    )
    assert result.pagination.total_results == 1
    assert result.pagination.truncated is False


async def test_get_studies_detail(mock_ctx, mock_client):
    mock_client.get_studies.return_value = {
        "items": [
            {
                "accession_id": "GCST000854",
                "initial_sample_size": "4,533 cases",
                "disease_trait": "Celiac disease",
                "pubmed_id": 21399633,
                "efo_traits": [
                    {
                        "efo_id": "EFO_0001060",
                        "efo_trait": "celiac disease",
                    }
                ],
                "discovery_ancestry": ["4533 European (U.K.)"],
            }
        ],
        "page": None,
    }
    mock_client.get_study_ancestries.return_value = [
        {
            "type": "initial",
            "number_of_individuals": 4533,
            "ancestral_groups": [{"ancestral_group": "European"}],
            "country_of_origin": [],
            "country_of_recruitment": [{"country_name": "U.K."}],
        }
    ]

    result = await gwascatalog_get_studies(
        mock_ctx,
        accession_id="GCST000854",
    )
    assert len(result.data) == 1
    assert result.data[0].accession_id == "GCST000854"
    assert result.data[0].disease_trait == "Celiac disease"
    assert result.data[0].ancestries[0].ancestral_groups == ["European"]
    assert result.pagination.total_results == 1
    assert result.pagination.truncated is False


async def test_get_studies_empty(mock_ctx, mock_client):
    mock_client.get_studies.return_value = {
        "items": [],
        "page": {
            "size": 10,
            "totalElements": 0,
            "totalPages": 0,
            "number": 0,
        },
    }

    result = await gwascatalog_get_studies(
        mock_ctx,
        efo_trait="nonexistent_xyz",
    )
    assert result.data == []
    assert result.pagination.total_results == 0
    assert result.pagination.truncated is False
    assert len(result.suggestions) > 0
    assert any("No results" in s for s in result.suggestions)
    assert any("gwascatalog_get_traits" in s for s in result.suggestions)


# ---- Associations tests ----


async def test_get_associations_list(mock_ctx, mock_client):
    mock_client.get_associations.return_value = {
        "items": [
            {
                "association_id": 188116214,
                "risk_frequency": "0.28",
                "p_value": 2e-13,
                "beta": "0.25 unit decrease",
                "range": "[0.18-0.33]",
                "mapped_genes": ["HLA-DPB2"],
                "locations": ["6:33114046"],
                "efo_traits": [
                    {
                        "efo_id": "EFO_0001060",
                        "efo_trait": "celiac disease",
                    }
                ],
                "accession_id": "GCST90468120",
                "snp_effect_allele": ["rs9277626-G"],
            }
        ],
        "page": {
            "size": 10,
            "totalElements": 1,
            "totalPages": 1,
            "number": 0,
        },
    }

    result = await gwascatalog_get_associations(
        mock_ctx,
        efo_trait="celiac disease",
    )
    assert len(result.data) == 1
    r = result.data[0]
    assert r.association_id == 188116214
    assert "HLA-DPB2" in r.mapped_genes
    assert r.p_value == 2e-13
    assert result.pagination.total_results == 1
    assert result.pagination.truncated is False


async def test_get_associations_detail(mock_ctx, mock_client):
    mock_client.get_associations.return_value = {
        "items": [
            {
                "association_id": 188116214,
                "risk_frequency": "0.28",
                "p_value": 2e-13,
                "beta": "0.25 unit decrease",
                "range": "[0.18-0.33]",
                "mapped_genes": ["HLA-DPB2"],
                "locations": ["6:33114046"],
                "efo_traits": [
                    {
                        "efo_id": "EFO_0001060",
                        "efo_trait": "celiac disease",
                    }
                ],
                "accession_id": "GCST90468120",
                "snp_effect_allele": ["rs9277626-G"],
            }
        ],
        "page": None,
    }

    result = await gwascatalog_get_associations(
        mock_ctx,
        association_id=188116214,
    )
    assert len(result.data) == 1
    r = result.data[0]
    assert r.association_id == 188116214
    assert "HLA-DPB2" in r.mapped_genes
    assert result.pagination.total_results == 1
    assert result.pagination.truncated is False


async def test_get_associations_allows_null_beta(mock_ctx, mock_client):
    mock_client.get_associations.return_value = {
        "items": [
            {
                "association_id": 188116214,
                "risk_frequency": "0.28",
                "p_value": 2e-13,
                "beta": None,
                "range": "[0.18-0.33]",
                "mapped_genes": ["HLA-DPB2"],
                "locations": ["6:33114046"],
                "efo_traits": [
                    {
                        "efo_id": "EFO_0001060",
                        "efo_trait": "celiac disease",
                    }
                ],
                "accession_id": "GCST90468120",
                "snp_effect_allele": ["rs9277626-G"],
            }
        ],
        "page": None,
    }

    result = await gwascatalog_get_associations(
        mock_ctx,
        association_id=188116214,
    )
    assert len(result.data) == 1
    assert result.data[0].beta is None


async def test_get_associations_empty(mock_ctx, mock_client):
    mock_client.get_associations.return_value = {
        "items": [],
        "page": {
            "size": 10,
            "totalElements": 0,
            "totalPages": 0,
            "number": 0,
        },
    }

    result = await gwascatalog_get_associations(
        mock_ctx,
        efo_trait="nonexistent_xyz",
    )
    assert result.data == []
    assert result.pagination.total_results == 0
    assert result.pagination.truncated is False
    assert len(result.suggestions) > 0
    assert any("No results" in s for s in result.suggestions)
    assert any("gwascatalog_get_traits" in s for s in result.suggestions)


# ---- Not found (404) tests ----


async def test_get_traits_not_found(mock_ctx, mock_client):
    mock_client.get_efo_traits.return_value = {
        "items": [],
        "page": None,
    }

    result = await gwascatalog_get_traits(mock_ctx, efo_id="EFO_9999999")
    assert result.data == []
    assert result.pagination.total_results == 0
    assert result.message == "No results found in the GWAS Catalog."


async def test_get_studies_not_found(mock_ctx, mock_client):
    mock_client.get_studies.return_value = {
        "items": [],
        "page": None,
    }

    result = await gwascatalog_get_studies(mock_ctx, accession_id="GCST999999")
    assert result.data == []
    assert result.pagination.total_results == 0
    assert result.message == "No results found in the GWAS Catalog."


async def test_get_associations_not_found(mock_ctx, mock_client):
    mock_client.get_associations.return_value = {
        "items": [],
        "page": None,
    }

    result = await gwascatalog_get_associations(mock_ctx, association_id="999999999")
    assert result.data == []
    assert result.pagination.total_results == 0
    assert result.message == "No results found in the GWAS Catalog."


# ---- Truncation suggestions tests ----


async def test_get_traits_truncated_suggestions(mock_ctx, mock_client):
    mock_client.get_efo_traits.return_value = {
        "items": [
            {
                "efo_trait": "trait 1",
                "uri": "http://example.com/1",
                "efo_id": "EFO_0000001",
            },
        ],
        "page": {
            "size": 1,
            "totalElements": 100,
            "totalPages": 100,
            "number": 0,
        },
    }

    result = await gwascatalog_get_traits(mock_ctx)
    assert result.pagination.truncated is True
    assert len(result.suggestions) > 0
    assert any("truncated" in s.lower() for s in result.suggestions)
    assert any("page=1" in s for s in result.suggestions)


async def test_get_studies_truncated_suggestions(mock_ctx, mock_client):
    mock_client.get_studies.return_value = {
        "items": [
            {
                "accession_id": "GCST000001",
                "disease_trait": "Test",
            }
        ],
        "page": {
            "size": 1,
            "totalElements": 500,
            "totalPages": 500,
            "number": 0,
        },
    }
    mock_client.get_study_ancestries.return_value = []

    result = await gwascatalog_get_studies(mock_ctx)
    assert result.pagination.truncated is True
    assert any("truncated" in s.lower() for s in result.suggestions)
    assert any("filter" in s.lower() for s in result.suggestions)


# ---- Successful queries have no suggestions ----


async def test_get_traits_success_no_suggestions(mock_ctx, mock_client):
    mock_client.get_efo_traits.return_value = {
        "items": [
            {
                "efo_trait": "celiac disease",
                "uri": "http://example.com",
                "efo_id": "EFO_0001060",
            },
        ],
        "page": {
            "size": 10,
            "totalElements": 1,
            "totalPages": 1,
            "number": 0,
        },
    }

    result = await gwascatalog_get_traits(mock_ctx, efo_trait="celiac")
    assert len(result.data) == 1
    assert result.suggestions == []
    assert result.message is None
