# URL Validator App

## What this app does
This app validates and normalizes a public http(s) URL string.

## When to use it
Use it when you need a deterministic, rule-based check that a URL is public and well-formed.

## Input
A JSON-RPC request to `POST /mcp` calling the `validate_normalize_url` tool with:

```
{ "url": "string" }
```

## Output
Either a `normalized_url` on success, or a `failure`/`blocked` reason on error.

## What this app does NOT do
- It does not fetch URLs.
- It does not analyze or summarize content.
- It does not allow private or local addresses.
