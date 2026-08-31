---
name: audit-curl-request
description: "Audit a curl command or config file before execution for HTTP method and body semantics, implicit default config, local-file references, and credential-bearing options. Use when asked to review, explain, or safety-check a curl request without sending it. Do not use to execute or replay a request, test a live endpoint, handle real credentials, bypass TLS, diagnose browser CORS, or modify server configuration."
---

# Audit a curl request

Perform a local pre-execution audit. Never run curl, contact the URL, read an `@file` payload, load an unrequested default config, or retain credential values.

## Normalize the input

Identify the shell that produced the command when quoting affects argument boundaries. Convert only the arguments after the `curl` executable into a JSON string array. Preserve option names and ordering, but replace passwords, bearer tokens, cookies, and authorization values with `<redacted>` while keeping the credential-bearing option or header name visible.

Add an optional intent object when the expected HTTP method is known:

```json
{
  "arguments": ["--disable", "--request", "POST", "--data-urlencode", "name=value", "https://api.example.invalid/items"],
  "intent": {"method": "POST"}
}
```

Do not translate an ambiguous command by guessing its shell rules. Ask for the shell or an exact argument vector when the distinction changes a value or file boundary.

## Run the bounded inspector

From an isolated temporary directory, run:

`python scripts/inspect_curl_request.py --input REQUEST.json`

When the command intentionally uses one curl config, pass the exact reviewed file separately:

`python scripts/inspect_curl_request.py --input REQUEST.json --config CURL_CONFIG`

The inspector bounds both inputs, parses only the supplied config, redacts all option values from its report, and never executes curl or reads body file references. It checks method selection, HEAD-mode misuse, declared intent, URL count, implicit default-config ambiguity, credential-bearing options, and `@file` forms. Use [the audit contract](references/audit-contract.md) to interpret limitations.

## Decide and report

Lead with `reviewable`, `unverified`, or `blocked`:

- `reviewable` means the normalized local evidence has no known gate failure; it is not authorization to send the request and does not prove server behavior.
- `unverified` means missing or implicit inputs prevent a complete review.
- `blocked` means the request crosses the Skill boundary or contains a deterministic semantic conflict.

List finding codes, the inferred method, URL count and schemes, body option names, redacted credential or file-reference option names, and every skipped gate. Never echo URLs containing user info, header values, body values, local filenames, or secrets. A user must separately approve any live request.
