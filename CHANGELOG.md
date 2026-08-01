# Changelog

## v0.3.0-enterprise-rc1 (proposed, untagged)

- Added a deterministic 100-document, entirely synthetic enterprise corpus manifest.
- Added a 118-case release acceptance contract spanning ingestion, Search, Agent,
  Evaluation, Research, security, resilience, and operations.
- Added isolated enterprise API/browser, bounded load, and soak tooling.
- Hardened release, security, backup/restore, monitoring, and incident documentation.

Baseline and rollback point: `736a402`. No cloud deployment is claimed.

Release status: **PARTIAL PASS**. Closure reruns passed Search, browser, Ollama,
resilience, security, regression, Docker, and migration profiles, but the provisioned-model
semantic and reranker acceptance gate failed. No commit or tag was created.
