"""Search mode: describe_tool, call_tool, per-user filtering and the instructions.

Search mode hides the catalogue from tools/list, and an LLM client can only call what
it was listed -- so call_tool is the only door to every other tool. That makes the
catalogue call_tool trusts an authorisation boundary, and most of this file is about
keeping it one: disabled tools, inactive servers and per-user denials must all stay
shut, and a denial on one server must not leak onto a same-named tool elsewhere.
"""

import os
import tempfile

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mcp_anywhere.auth.models import User, UserToolPermission
from mcp_anywhere.base import Base
from mcp_anywhere.core import instructions as ins
from mcp_anywhere.core import tool_search as ts
from mcp_anywhere.core.tool_search import (
    META_TOOL_NAMES,
    ToolEntry,
    coerce_arguments,
    effective_list_mode,
    entries_from_rows,
    render_signature,
    resolve_callable,
)
from mcp_anywhere.database import MCPServer, MCPServerTool

# --------------------------------------------------------------------------- helpers


def entry(qualified, tool, server="srv", desc="", schema=None):
    return ToolEntry(
        qualified_name=qualified, server_name=server, tool_name=tool,
        description=desc, schema=schema,
    )


ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "labels": {"type": "array"},
        "project_id": {"type": "string"},
        "title": {"type": "string"},
        "due": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["project_id", "title"],
}


# ------------------------------------------------------------------------ signatures


class TestSignature:
    def test_required_parameters_come_first_and_optional_are_marked(self):
        sig = render_signature(ISSUE_SCHEMA)
        assert sig.startswith("(project_id: string, title: string, ")
        assert "labels?: array" in sig
        assert "due?: string" in sig, "a nullable union reads as its real type"

    def test_no_parameters(self):
        assert render_signature({"type": "object", "properties": {}}) == "()"

    def test_unknown_schema_is_marked_rather_than_guessed(self):
        assert render_signature(None) == "(…)"

    def test_long_signatures_are_bounded(self):
        schema = {"properties": {f"param_{i}": {"type": "string"} for i in range(40)}}
        assert len(render_signature(schema, width=80)) <= 80

    def test_rows_carry_a_schema_stored_as_json_text(self):
        rows = [{"server_id": "a1", "server_name": "s", "tool_name": "t",
                 "tool_description": "d", "tool_schema": '{"properties": {"x": {"type": "integer"}}}'}]
        assert entries_from_rows(rows)[0].signature() == "(x?: integer)"

    def test_a_corrupt_stored_schema_is_ignored(self):
        rows = [{"server_id": "a1", "server_name": "s", "tool_name": "t",
                 "tool_description": "d", "tool_schema": "{not json"}]
        assert entries_from_rows(rows)[0].schema is None


# ------------------------------------------------------------------ call resolution


CATALOGUE = [
    entry("afc9d618_create_issue", "create_issue", "gitlab-acme"),
    entry("b6ae340b_render", "render", "mermaid"),
]


class TestResolveCallable:
    def test_an_available_tool_resolves(self):
        assert resolve_callable("afc9d618_create_issue", CATALOGUE).server_name == "gitlab-acme"

    def test_an_unknown_name_does_not(self):
        assert resolve_callable("afc9d618_delete_everything", CATALOGUE) is None

    def test_a_bare_name_is_not_enough(self):
        """Without the prefix the target server is ambiguous; refuse rather than pick."""
        assert resolve_callable("create_issue", CATALOGUE) is None

    @pytest.mark.parametrize("meta", sorted(META_TOOL_NAMES))
    def test_meta_tools_cannot_be_called_through_call_tool(self, meta):
        catalogue = CATALOGUE + [entry(meta, meta)]
        assert resolve_callable(meta, catalogue) is None

    def test_empty_name(self):
        assert resolve_callable("", CATALOGUE) is None


class TestCoerceArguments:
    @pytest.mark.parametrize("raw,expected", [
        (None, {}), ("", {}), ("   ", {}),
        ({"a": 1}, {"a": 1}),
        ('{"a": 1}', {"a": 1}),
    ])
    def test_accepted_shapes(self, raw, expected):
        assert coerce_arguments(raw) == expected

    @pytest.mark.parametrize("raw", ["[1, 2]", '"text"', "{broken", 42, ["a"]])
    def test_rejected_shapes(self, raw):
        with pytest.raises((ValueError, TypeError)):
            coerce_arguments(raw)


# ----------------------------------------------------------------------- list mode


class TestEffectiveListMode:
    @pytest.mark.parametrize("configured,headers,expected", [
        ("full", {}, "full"),
        ("search", {}, "search"),
        ("full", {"x-mcp-tool-list-mode": "search"}, "search"),
        ("search", {"x-mcp-tool-list-mode": "full"}, "full"),
        ("full", {"x-mcp-tool-list-mode": " SEARCH "}, "search"),
        ("full", {"x-mcp-tool-list-mode": "everything"}, "full"),
        ("banana", {}, "full"),
        ("search", None, "search"),
    ])
    def test_header_overrides_config_when_valid(self, configured, headers, expected):
        assert effective_list_mode(configured, headers) == expected


class Listed:
    def __init__(self, key, name=None):
        self.key = key
        self.name = name or key


class TestApplyListMode:
    @staticmethod
    def run(monkeypatch, *, enabled, configured, headers, tools):
        from mcp_anywhere.core import middleware as mw

        monkeypatch.setattr(mw.Config, "TOOL_SEARCH_ENABLED", enabled)
        monkeypatch.setattr(mw.Config, "TOOL_LIST_MODE", configured)
        monkeypatch.setattr(
            "fastmcp.server.dependencies.get_http_headers", lambda *a, **k: headers
        )
        return [t.key for t in mw._apply_list_mode(tools)]

    TOOLS = [Listed("search_tools"), Listed("describe_tool"), Listed("call_tool"),
             Listed("afc9d618_create_issue", "create_issue")]

    def test_one_client_can_opt_in_by_header(self, monkeypatch):
        keys = self.run(monkeypatch, enabled=True, configured="full",
                        headers={"x-mcp-tool-list-mode": "search"}, tools=self.TOOLS)
        assert keys == ["search_tools", "describe_tool", "call_tool"]

    def test_other_clients_keep_the_full_catalogue(self, monkeypatch):
        keys = self.run(monkeypatch, enabled=True, configured="full", headers={}, tools=self.TOOLS)
        assert "afc9d618_create_issue" in keys and "search_tools" in keys

    def test_full_mode_does_not_offer_call_tool_or_describe_tool(self, monkeypatch):
        """Beside the catalogue, call_tool would be a second name for every tool and
        would sidestep a client's own per-tool permission rules."""
        keys = self.run(monkeypatch, enabled=True, configured="full", headers={}, tools=self.TOOLS)
        assert "call_tool" not in keys and "describe_tool" not in keys

    def test_header_is_ignored_when_search_is_disabled(self, monkeypatch):
        keys = self.run(monkeypatch, enabled=False, configured="full",
                        headers={"x-mcp-tool-list-mode": "search"}, tools=self.TOOLS)
        assert len(keys) == 4

    def test_a_mounted_tool_whose_bare_name_is_call_tool_is_not_kept(self, monkeypatch):
        impostor = Listed("abc12345_call_tool", name="call_tool")
        keys = self.run(monkeypatch, enabled=True, configured="search", headers={},
                        tools=self.TOOLS + [impostor])
        assert "abc12345_call_tool" not in keys


# --------------------------------------------------------------------- instructions


SERVERS = [
    ("c001f7a1", "coolify-prod", 27),
    ("5b662b69", "coolify-staging", 27),
    ("afc9d618", "gitlab-acme", 21),
]


class TestInstructions:
    def test_without_search_the_upstream_text_is_unchanged(self):
        assert ins.build_instructions(SERVERS, search_enabled=False) == ins.BASE_INSTRUCTIONS

    def test_every_server_id_is_mapped_to_its_name(self):
        text = ins.build_instructions(SERVERS, search_enabled=True)
        for sid, name, count in SERVERS:
            assert f"{sid} {name} ({count})" in text

    def test_totals_and_meta_tools_are_explained(self):
        text = ins.build_instructions(SERVERS, search_enabled=True)
        assert "3 servers, 75 tools" in text
        for meta in META_TOOL_NAMES:
            assert meta in text

    def test_guidance_then_addendum_then_table(self):
        """Claude Code truncates at 2048 chars; the table is the part to lose."""
        text = ins.build_instructions(SERVERS, True, extra="ADDENDUM-LINE")
        assert text.index("call_tool(") < text.index("ADDENDUM-LINE") < text.index("Server ids:")

    def test_guidance_and_addendum_survive_claude_codes_limit_at_this_size(self):
        servers = [(f"{i:08x}", f"some-fairly-long-server-name-{i}", 40) for i in range(37)]
        text = ins.build_instructions(servers, True, extra="Z" * 600)
        assert len(text) > 2048, "the scenario only matters when the text is too long"
        head = text[:2048]
        assert "call_tool(" in head and "Z" * 600 in head

    def test_base_text_is_byte_identical_to_upstream(self):
        upstream = (
            "This router provides access to multiple MCP servers.\n"
            "        \n"
            "All tools from mounted servers are available directly with prefixed names.\n"
            "You can use tools/list to see all available tools from all mounted servers.\n"
        )
        assert ins.BASE_INSTRUCTIONS == upstream

    def test_the_addendum_applies_without_search_too(self):
        text = ins.build_instructions([], False, extra="Policy line.")
        assert text.startswith(ins.BASE_INSTRUCTIONS.rstrip()) and "Policy line." in text

    def test_blank_addendum_adds_nothing(self):
        assert ins.build_instructions([], False, extra="  \n ") == ins.BASE_INSTRUCTIONS

    def test_unreadable_or_unset_addendum_is_empty(self, tmp_path):
        assert ins.read_extra_instructions("") == ""
        assert ins.read_extra_instructions(str(tmp_path / "missing.md")) == ""

    def test_addendum_is_capped(self, tmp_path):
        f = tmp_path / "extra.md"
        f.write_text("x" * (ins._EXTRA_MAX_CHARS + 500))
        assert len(ins.read_extra_instructions(str(f))) == ins._EXTRA_MAX_CHARS

    def test_setting_instructions_reaches_the_router(self):
        from fastmcp import FastMCP

        router = FastMCP(name="t", instructions="old")
        ins.set_router_instructions(router, "new")
        assert router.instructions == "new"


# ------------------------------------------------------------- the database boundary


@pytest_asyncio.fixture
async def catalogue_db(monkeypatch):
    """A real SQLite database behind load_catalogue, so the SQL itself is tested."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("mcp_anywhere.database.get_async_session", lambda: maker())

    async with maker() as s:
        gitlab = MCPServer(id="afc9d618", name="gitlab-acme", github_url="x",
                           runtime_type="npx", start_command="x", is_active=True)
        mermaid = MCPServer(id="b6ae340b", name="mermaid-mcp", github_url="x",
                            runtime_type="npx", start_command="x", is_active=True)
        retired = MCPServer(id="dead0000", name="retired", github_url="x",
                            runtime_type="npx", start_command="x", is_active=False)
        s.add_all([gitlab, mermaid, retired])
        s.add_all([
            MCPServerTool(id="t0000001", server_id="afc9d618", tool_name="create_issue",
                          tool_description="Create an issue", tool_schema=ISSUE_SCHEMA),
            MCPServerTool(id="t0000002", server_id="b6ae340b", tool_name="create_issue",
                          tool_description="Mermaid's own create_issue"),
            MCPServerTool(id="t0000003", server_id="b6ae340b", tool_name="render",
                          tool_description="Render", is_enabled=False),
            MCPServerTool(id="t0000004", server_id="dead0000", tool_name="anything",
                          tool_description="On an inactive server"),
        ])
        s.add(User(id=7, username="alice", password_hash="x"))
        await s.flush()
        # alice may not use mermaid's create_issue -- and only that one
        s.add(UserToolPermission(user_id=7, tool_id="t0000002", permission="deny"))
        await s.commit()
    try:
        yield
    finally:
        await engine.dispose()
        os.unlink(path)


def names(catalogue):
    return sorted(e.qualified_name for e in catalogue)


class TestCatalogueBoundary:
    async def test_disabled_tools_and_inactive_servers_are_excluded(self, catalogue_db):
        got = names(await ts.load_catalogue())
        assert "b6ae340b_render" not in got, "disabled"
        assert "dead0000_anything" not in got, "server inactive"

    async def test_a_denial_is_scoped_to_one_server(self, catalogue_db):
        """The list filter matches bare names and hides both; this path must not."""
        got = names(await ts.load_catalogue(user_id=7))
        assert "b6ae340b_create_issue" not in got, "the denied instance is gone"
        assert "afc9d618_create_issue" in got, "the same-named tool elsewhere is not"

    async def test_without_a_user_no_denials_apply(self, catalogue_db):
        got = names(await ts.load_catalogue(user_id=None))
        assert "b6ae340b_create_issue" in got

    async def test_the_stored_schema_reaches_the_entry(self, catalogue_db):
        cat = {e.qualified_name: e for e in await ts.load_catalogue()}
        assert cat["afc9d618_create_issue"].signature().startswith("(project_id: string")

    async def test_call_tool_cannot_reach_a_denied_or_disabled_tool(self, catalogue_db):
        cat = await ts.load_catalogue(user_id=7)
        assert resolve_callable("b6ae340b_create_issue", cat) is None
        assert resolve_callable("b6ae340b_render", cat) is None
        assert resolve_callable("afc9d618_create_issue", cat) is not None


class TestServerSummary:
    async def test_counts_enabled_tools_of_active_servers(self, catalogue_db):
        summary = {name: count for _, name, count in await ins.load_server_summary()}
        assert summary == {"gitlab-acme": 1, "mermaid-mcp": 1}, (
            "render is disabled and 'retired' is inactive"
        )


class TestSchemaRefreshOnDiscovery:
    """Rows used to be only added or removed, so old rows never gained a schema."""

    async def test_existing_rows_gain_schema_and_keep_their_enabled_flag(self, catalogue_db):
        from mcp_anywhere import database as db
        from mcp_anywhere.database_utils import store_server_tools

        new_schema = {"properties": {"code": {"type": "string"}}, "required": ["code"]}
        async with db.get_async_session() as s:
            server = await s.get(MCPServer, "b6ae340b")
            await store_server_tools(s, server, [
                {"name": "render", "description": "Render (v2)", "schema": new_schema},
                {"name": "create_issue", "description": "Mermaid's own create_issue"},
            ])
        async with db.get_async_session() as s:
            render = await s.get(MCPServerTool, "t0000003")
            assert render.tool_description == "Render (v2)"
            assert render.tool_schema == new_schema
            assert render.is_enabled is False, "the operator's choice survives discovery"

    async def test_a_new_tool_is_stored_with_its_schema(self, catalogue_db):
        from sqlalchemy import select

        from mcp_anywhere import database as db
        from mcp_anywhere.database_utils import store_server_tools

        async with db.get_async_session() as s:
            server = await s.get(MCPServer, "afc9d618")
            await store_server_tools(s, server, [
                {"name": "create_issue", "description": "Create an issue", "schema": ISSUE_SCHEMA},
                {"name": "get_issue", "description": "Get one", "schema": {"properties": {}}},
            ])
        async with db.get_async_session() as s:
            row = (await s.execute(select(MCPServerTool).where(
                MCPServerTool.server_id == "afc9d618", MCPServerTool.tool_name == "get_issue"
            ))).scalar_one()
            assert row.tool_schema == {"properties": {}}
