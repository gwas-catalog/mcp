"""Exercise probes against real HTTP, including a stuck initialization handler."""

from __future__ import annotations

import asyncio
import json
import socket
import sys
from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import AsyncMock

import anyio
import httpx2
import pytest
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from gwascatalog.mcp import health, server


@asynccontextmanager
async def serve(app):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        instance = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        task = asyncio.create_task(instance.serve(sockets=[sock]))
        try:
            with anyio.fail_after(5):
                while not instance.started:
                    if task.done():
                        await task
                    await asyncio.sleep(0.01)
            yield f"http://127.0.0.1:{sock.getsockname()[1]}/gwas/mcp"
        finally:
            instance.should_exit = True
            await asyncio.wait_for(task, 5)


async def test_real_http_initialization_and_tools(monkeypatch):
    monkeypatch.setattr(
        server, "settings", replace(server.settings, streamable_http_path="/gwas/mcp")
    )
    upstream = AsyncMock()
    upstream.get_efo_traits.return_value = {"items": [], "page": None}

    def factory(*args):
        return upstream

    monkeypatch.setattr(server, "GwasCatalogClient", factory)
    listing = []
    monkeypatch.setattr(server, "record_list_request", listing.append)
    # Broken environment proxies must not affect the local health check.
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    async with serve(server.streamable_http_app()) as url:
        await asyncio.gather(health.check(url), health.check(url))
        upstream.get_efo_traits.assert_not_called()
        upstream.close.assert_not_called()
        async with (
            httpx2.AsyncClient(trust_env=False) as http,
            streamable_http_client(url, http_client=http) as streams,
            ClientSession(*streams) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            assert len(tools.tools) == 3
            assert all(tool.annotations.read_only_hint for tool in tools.tools)
            assert all(
                "gwascatalog://docs/terms-of-use" in tool.description
                for tool in tools.tools
            )
            resources = await session.list_resources()
            assert len(resources.resources) == 6
            assert any(
                resource.uri == "gwascatalog://docs/terms-of-use"
                and resource.name == "terms_of_use"
                for resource in resources.resources
            )
            result = await session.call_tool("gwascatalog_get_traits", {})
            assert not result.is_error
            assert result.structured_content["data"] == []
            assert "tools" in listing and "resources" in listing
            await session.read_resource("gwascatalog://ancestry-labels")
            index = await session.read_resource("gwascatalog://docs/index")
            assert "gwascatalog://ancestry-labels" in index.contents[0].text
            assert (
                "gwascatalog://reference/ancestry-labels" not in index.contents[0].text
            )
            terms = await session.read_resource("gwascatalog://docs/terms-of-use")
            assert (
                terms.contents[0].text == "https://www.ebi.ac.uk/about/terms-of-use/\n"
            )
        upstream.get_efo_traits.assert_awaited_once()
    upstream.close.assert_awaited_once()


@pytest.mark.parametrize("failure", ["hang", "invalid"])
async def test_probe_rejects_failed_initialization_when_listing_works(failure):
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                event = await receive()
                await send({"type": event["type"] + ".complete"})
                if event["type"] == "lifespan.shutdown":
                    return
        body = b""
        while True:
            event = await receive()
            body += event.get("body", b"")
            if not event.get("more_body"):
                break
        request = json.loads(body)
        if request["method"] == "initialize" and failure == "hang":
            while (await receive())["type"] != "http.disconnect":
                pass
            return
        response = json.dumps(
            {"jsonrpc": "2.0", "id": request["id"], "result": {"tools": []}}
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": response})

    async with serve(app) as url:
        async with httpx2.AsyncClient(trust_env=False) as http:
            response = await http.post(
                url, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            )
            assert response.json()["result"] == {"tools": []}
        with anyio.fail_after(2):
            with pytest.raises(TimeoutError if failure == "hang" else ExceptionGroup):
                await health.check(url, timeout=0.2)


async def test_probe_connection_refused():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        with anyio.fail_after(2):
            with pytest.raises((TimeoutError, ExceptionGroup)):
                await health.check(f"http://127.0.0.1:{sock.getsockname()[1]}/mcp", 0.2)


def test_probe_exit_status(monkeypatch, capsys):
    check = AsyncMock(side_effect=RuntimeError("initialization failed"))
    monkeypatch.setattr(health, "check", check)
    with pytest.raises(SystemExit, match="1"):
        health.main()
    assert "initialization failed" in capsys.readouterr().err
    check.side_effect = None
    health.main()


async def test_stdio_initialization():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "gwascatalog.mcp.server"]
    )
    with anyio.fail_after(10):
        async with stdio_client(params) as streams, ClientSession(*streams) as session:
            assert (await session.initialize()).server_info.name == "gwascatalog"
            assert len((await session.list_tools()).tools) == 3
