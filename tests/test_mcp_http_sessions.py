"""The MCP HTTP endpoint must not keep per-client sessions in memory.

Clients rarely send DELETE to end a session, and the session manager has no
idle timeout, so every stateful session lived until the process died.
"""

import json
from contextlib import asynccontextmanager

import httpx
import pytest
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request

from mcp_anywhere.web.mcp_mount import create_mcp_http_app

HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
}
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


def result_of(response: httpx.Response) -> dict:
    data = next(
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith("data: ")
    )
    return json.loads(data)["result"]


@pytest.fixture
def router() -> FastMCP:
    router = FastMCP("test-router")

    @router.tool
    def whoami() -> str:
        return get_http_request().headers["x-client"]

    return router


@asynccontextmanager
async def serve(router: FastMCP):
    app = create_mcp_http_app(router)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def test_clients_that_never_end_their_session_are_not_tracked(router):
    async with serve(router) as client:
        responses = [
            await client.post("/", json=INITIALIZE, headers={**HEADERS, "x-client": f"client-{i}"})
            for i in range(20)
        ]

    for response in responses:
        assert response.status_code == 200
        assert "mcp-session-id" not in response.headers


async def test_tools_are_listed_without_a_session(router):
    async with serve(router) as client:
        response = await client.post(
            "/",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers={**HEADERS, "x-client": "lister"},
        )

    assert response.status_code == 200
    assert [tool["name"] for tool in result_of(response)["tools"]] == ["whoami"]


async def test_each_tool_call_sees_its_own_http_request(router):
    async with serve(router) as client:
        responses = {
            name: await client.post(
                "/",
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "whoami", "arguments": {}},
                },
                headers={**HEADERS, "x-client": name},
            )
            for name in ("alice", "bob")
        }

    for name, response in responses.items():
        assert response.status_code == 200
        assert result_of(response)["content"][0]["text"] == name
