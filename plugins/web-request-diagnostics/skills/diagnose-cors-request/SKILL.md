---
name: diagnose-cors-request
description: "Diagnose browser Fetch and CORS request failures from captured request, response, and preflight evidence. Use when a browser reports a CORS block, an OPTIONS preflight fails, or Fetch returns an opaque or inaccessible response. Do not use to disable browser security, proxy around policy, change production headers without approval, debug unrelated backend failures, or make live requests automatically."
---

# Diagnose Cors Request

Diagnose from captured evidence first. Do not launch a browser, replay a credentialed request, weaken server policy, recommend `mode: no-cors` as a fix, or edit client/server code without approval.

## Gather one failing exchange

Collect page origin; request URL, method, mode, credentials mode, and request headers; actual response status and CORS headers; and OPTIONS preflight status and headers when present. Redact cookies, authorization values, tokens, and private query parameters.

Encode only those facts in a local JSON file using [the evidence schema](references/evidence-schema.md). Run:

`python scripts/classify_cors.py --input PATH/evidence.json`

The classifier performs no network requests. It determines whether the request is cross-origin and simple or preflighted, then checks origin, credential, method, and header gates. A blocked or incomplete exchange exits nonzero and names the failing phase.

## Interpret before remediation

Distinguish browser policy from server application errors, redirects, DNS/TLS failures, and absent evidence. Assign each finding to the client request, preflight response, actual response, or server CORS policy. Read the remediation notes in the evidence schema; propose the narrowest allowed origin, method, and header set.

## Report

Lead with `allowed`, `blocked`, `same-origin`, `opaque`, or `unverified`. Cite the captured field behind each finding, name the responsible phase, and provide a minimal validation replay for the user to approve. Never recommend wildcard origins with credentialed requests or claim that `no-cors` grants response access.
