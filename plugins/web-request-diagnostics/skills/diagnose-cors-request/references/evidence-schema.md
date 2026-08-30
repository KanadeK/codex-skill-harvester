# CORS evidence schema

Provide a UTF-8 JSON object no larger than 1 MB:

```json
{
  "page_origin": "https://app.example",
  "request": {
    "url": "https://api.example/items",
    "method": "POST",
    "mode": "cors",
    "credentials": "include",
    "headers": {"content-type": "application/json", "x-request-id": "redacted"}
  },
  "preflight": {
    "status": 204,
    "headers": {
      "access-control-allow-origin": "https://app.example",
      "access-control-allow-credentials": "true",
      "access-control-allow-methods": "POST",
      "access-control-allow-headers": "content-type, x-request-id"
    }
  },
  "response": {
    "status": 200,
    "headers": {
      "access-control-allow-origin": "https://app.example",
      "access-control-allow-credentials": "true"
    }
  }
}
```

Header names are case-insensitive. Redact values for cookies, authorization, API keys, and private query strings; the classifier needs only header names for request classification.

An `OPTIONS` success alone is insufficient: the actual response also needs a valid `Access-Control-Allow-Origin`, and credentialed requests require an explicit origin plus `Access-Control-Allow-Credentials: true`. Wildcard origin cannot authorize credentialed response access. `mode: no-cors` yields an opaque response and is not a CORS permission fix.
