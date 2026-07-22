# External Content Threat Model

Updated on 2026-07-22.

External content is untrusted data. It may be cited as source text, but it must never become an executable instruction.

## Blocked Network Targets

Outbound validation blocks localhost, loopback, private IPv4 and IPv6 ranges, link-local ranges, multicast ranges, cloud metadata hosts, internal Docker service names, unsupported schemes, and redirects to blocked destinations.

Provider calls enforce:

- exact host allowlists
- HTTPS for public providers
- DNS resolution validation
- redirect validation at every hop
- maximum redirect count
- connection and read timeouts
- response-size limits
- content-type validation
- safe URL normalization
- no user-controlled authorization headers
- no proxy environment leakage

## Prompt Injection

The safety reviewer scans external excerpts and drafted answers for attempts to:

- ignore prior or system instructions
- reveal system prompts or secrets
- authorize new tools
- alter tenant or workspace scope
- request credentials
- trigger shell commands or arbitrary URLs
- override evidence or safety rules

If external content contains a prompt-injection signal, the agent abstains and returns no external citations.

## Provenance

External citations use external fields: provider, title, canonical URL, retrieval date, and excerpt. Internal document citations keep document, version, and chunk provenance. The two provenance types are not mixed.
