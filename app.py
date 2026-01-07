from __future__ import annotations

from flask import Flask, jsonify, make_response, request
from urllib.parse import urlsplit, urlunsplit
import ipaddress

app = Flask(__name__)

PLACEHOLDER_CHALLENGE = "placeholder-token"


def json_result(status: str, *, data: dict | None = None, reason: str | None = None):
    payload: dict[str, object] = {"status": status}
    if data is not None:
        payload["data"] = data
    if reason is not None:
        payload["reason"] = reason
    return payload


def is_private_or_local_host(hostname: str) -> bool:
    if hostname == "localhost" or hostname.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def normalize_url(raw_url: str) -> tuple[str | None, str | None, str | None]:
    if not isinstance(raw_url, str) or not raw_url:
        return None, "failure", "Input 'url' must be a non-empty string."

    try:
        parts = urlsplit(raw_url)
    except ValueError:
        return None, "failure", "Input 'url' is not a valid URL."

    if parts.scheme not in {"http", "https"}:
        return None, "failure", "Only http and https URLs are supported."

    if not parts.hostname:
        return None, "failure", "URL must include a hostname."

    if parts.username or parts.password:
        return None, "failure", "User info is not supported in URLs."

    hostname = parts.hostname.lower()

    if is_private_or_local_host(hostname):
        return None, "blocked", "Private or local addresses are not allowed."

    port = parts.port
    if port is not None:
        if port < 1 or port > 65535:
            return None, "failure", "Port must be between 1 and 65535."
        if (parts.scheme == "http" and port == 80) or (
            parts.scheme == "https" and port == 443
        ):
            port = None

    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    netloc = hostname
    if port is not None:
        netloc = f"{hostname}:{port}"

    path = parts.path if parts.path else "/"
    normalized = urlunsplit(
        (parts.scheme, netloc, path, parts.query, "")
    )

    return normalized, "success", None


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/mcp", methods=["GET"])
def mcp_hint():
    return make_response("POST JSON-RPC 2.0 requests to this endpoint.", 200)


@app.route("/mcp", methods=["OPTIONS"])
def mcp_options():
    return make_response("", 204)


@app.route("/mcp", methods=["POST"])
def mcp_post():
    try:
        payload = request.get_json(force=True)
    except Exception:
        response = json_result("failure", reason="Request body must be valid JSON.")
        return jsonify({"jsonrpc": "2.0", "id": None, "result": response})

    if not isinstance(payload, dict):
        response = json_result("failure", reason="Request body must be a JSON object.")
        return jsonify({"jsonrpc": "2.0", "id": None, "result": response})

    method = payload.get("method")
    request_id = payload.get("id")

    if method == "initialize":
        result = json_result(
            "success",
            data={
                "name": "url-validator",
                "version": "1.0.0",
            },
        )
        return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})

    if method == "tools/list":
        result = json_result(
            "success",
            data={
                "tools": [
                    {
                        "name": "validate_normalize_url",
                        "description": "Validate and normalize a public http(s) URL string.",
                        "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
                        "annotations": {
                            "readOnlyHint": True,
                            "openWorldHint": True,
                            "destructiveHint": False,
                        },
                    }
                ]
            },
        )
        return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})

    if method == "tools/call":
        params = payload.get("params")
        if not isinstance(params, dict):
            result = json_result("failure", reason="'params' must be an object.")
            return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})

        name = params.get("name")
        arguments = params.get("arguments")
        if name != "validate_normalize_url":
            result = json_result("failure", reason="Unknown tool name.")
            return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})

        if not isinstance(arguments, dict):
            result = json_result("failure", reason="'arguments' must be an object.")
            return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})

        normalized, status, reason = normalize_url(arguments.get("url"))
        if status == "success":
            result = json_result("success", data={"normalized_url": normalized})
        else:
            result = json_result(status, reason=reason)

        return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})

    result = json_result("failure", reason="Unsupported method.")
    return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


@app.route("/privacy", methods=["GET"])
def privacy():
    return make_response("This app stores no user data.", 200)


@app.route("/terms", methods=["GET"])
def terms():
    return make_response("Use at your own risk. No warranties.", 200)


@app.route("/.well-known/openai-apps-challenge", methods=["GET"])
def openai_apps_challenge():
    return make_response(PLACEHOLDER_CHALLENGE, 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
