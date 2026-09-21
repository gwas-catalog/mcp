"""HTTP browser fallback tests."""

from __future__ import annotations

from gwascatalog.mcp.server import _with_browser_fallback


async def _call(app, *, method: str, accept: str) -> list[dict]:
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await app(
        {
            "type": "http",
            "method": method,
            "path": "/gwas/mcp",
            "headers": [(b"accept", accept.encode())],
        },
        receive,
        send,
    )
    return messages


async def test_browser_get_returns_html():
    async def backend(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    messages = await _call(
        _with_browser_fallback(backend, "/gwas/mcp"),
        method="GET",
        accept="text/html",
    )

    assert messages[0]["status"] == 200
    assert b"text/html; charset=utf-8" in dict(messages[0]["headers"]).values()
    assert (
        b"https://www.ebi.ac.uk/gwas/docs/programmatic-access/" in messages[1]["body"]
    )


async def test_browser_head_returns_no_body():
    async def backend(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    messages = await _call(
        _with_browser_fallback(backend, "/gwas/mcp"),
        method="HEAD",
        accept="text/html",
    )

    assert messages[0]["status"] == 200
    assert messages[1]["body"] == b""


async def test_sse_get_passes_through():
    async def backend(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 204,
                "headers": [(b"x-backend", b"1")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    messages = await _call(
        _with_browser_fallback(backend, "/gwas/mcp"),
        method="GET",
        accept="text/event-stream",
    )

    assert messages[0]["status"] == 204
    assert dict(messages[0]["headers"])[b"x-backend"] == b"1"


async def test_post_passes_through():
    async def backend(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 204,
                "headers": [(b"x-backend", b"1")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    messages = await _call(
        _with_browser_fallback(backend, "/gwas/mcp"),
        method="POST",
        accept="application/json, text/event-stream",
    )

    assert messages[0]["status"] == 204
    assert dict(messages[0]["headers"])[b"x-backend"] == b"1"
