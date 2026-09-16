# Changelog

## 1.0.8 - 2026-09-16

- Use Helm 3.16.2 in CI deployments and remove production deployment jobs from
  main-branch pipelines.

## 1.0.7 - 2026-09-16

- Keep Helm chart metadata in sync with the released MCP application version.

## 1.0.6 - 2026-09-16

- Fix the ancestry-label resource URI in the MCP resource index and expose the
  Terms of Use resource URI in every tool description.

## 1.0.5 - 2026-09-16

- Add a Terms of Use MCP resource linking to the current EMBL-EBI terms for
  GWAS Catalog and data usage.
- Restore each study's summary-statistics location and dataset-specific licence
  terms that were missing from MCP results despite being supplied by the GWAS
  Catalog REST API.

## 1.0.4 - 2026-09-14

- Advertise the canonical `https://www.ebi.ac.uk/gwas/mcp` endpoint so MCP
  clients do not encounter a cross-origin redirect during initialisation.

## 1.0.3 - 2026-09-08

- Fix release image digest parsing with Buildx descriptor output.

## 1.0.2 - 2026-09-07

- Add GitLab CI checks and AMD64 image publishing for stable release tags,
  with `latest` tracking the highest published stable version.
- Upgrade the MCP Python SDK to 2.1.1 while preserving stateless HTTP, existing
  tools and resources, stdio support and telemetry.
- Add Kubernetes probes that check fresh MCP initialisation, remove unready
  containers from traffic and restart after three consecutive liveness failures.
- Allow approximately 60 seconds for startup, with compatibility for older
  Kubernetes clusters.
- Document the development endpoint as `https://wwwdev.ebi.ac.uk/gwas/mcp`.

## 1.0.1 - 2026-07-03

- Fix broken REST API V2 queries (camel case and broken sort)

## 1.0.0 - 2026-07-01

- Initial release of the GWAS Catalog MCP server.
- Adds tools for querying studies, traits and associations.
- Adds MCP resources for API docs, schemas, indexes and cohort guidance.
- Includes telemetry, HTTP deployment support and Helm configuration.
