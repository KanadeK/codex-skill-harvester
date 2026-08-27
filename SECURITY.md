# Security Policy

## Supported versions

Security fixes are made on the latest published `0.1.x` release and `main`. Older commits and forks are not separately supported.

## Reporting a vulnerability

Use GitHub's private **Report a vulnerability** form for this repository. Do not open a public issue for token exposure, path traversal, unsafe handling of fetched content, workflow-permission escalation, or another exploitable condition.

Include the affected version, a minimal reproduction using non-sensitive data, impact, and any suggested mitigation. Do not include real credentials or private source material. We aim to acknowledge a complete report within seven days and will coordinate disclosure after a fix is available.

The harvester treats public internet content as untrusted data. A report showing that fetched instructions or third-party scripts can be executed is in scope. Reports that only request publication of a low-quality or duplicate Skill are product-quality issues, not security vulnerabilities.
