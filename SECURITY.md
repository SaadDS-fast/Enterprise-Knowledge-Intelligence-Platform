# Security policy

Report suspected vulnerabilities privately to the repository maintainers. Do not open a
public issue containing credentials, private documents, exploit payloads, or tenant data.

The supported release candidate is the proposed `v0.3.0-enterprise-rc1`; it is not tagged
until release acceptance completes. Security boundaries include JWT authentication,
workspace-scoped authorization, server-owned citations and response state, strict upload
validation, outbound URL policy, model/host allowlists, and fail-closed generation.

See [the threat model](docs/security/threat-model.md),
[security controls](security/SECURITY.md), and
[incident response](docs/operations/incident-response.md).
