"""Keyword search over the gateway's tool catalogue, backed by SQLite FTS5."""

import json
import sqlite3
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import NotFoundError
from fastmcp.tools.tool import ToolResult

# bm25 column weights, in table order: qualified_name is unindexed, so its weight is
# inert and only present to keep the argument list aligned with the schema. A hit in
# the tool's own name outranks the server it came from, which outranks a passing
# mention in prose.
# bm25 column weights, in table order: qualified_name is unindexed, so its weight is
# inert and only present to keep the argument list aligned with the schema. A hit in
# the tool's own name outranks the server it came from, which outranks a passing
# mention in prose.
_BM25_WEIGHTS = (0.0, 5.0, 10.0, 1.0)

# Two FTS5 indexes over the same rows, because neither tokenizer covers what people
# type on its own:
# - porter unicode61 indexes whole words and stems them, so "issues" finds
#   create_issue and "repositories" finds a repository tool. It cannot see inside a
#   word: "acme-dockerhub" is stored as the words acme and
#   dockerhub, so "hub" -- the end of a word -- matches nothing, and camelCase names
#   such as listRepositoryTags are one word, invisible to "tags".
# - trigram indexes every three-character run, so "hub" is found inside dockerhub and
#   "namespace" inside getPersonalNamespace. It does no stemming, and it cannot match
#   a term shorter than three characters.
# A term matches a tool if either index finds it.
_WORD_TOKENIZER = "porter unicode61"
_GRAM_TOKENIZER = "trigram"
_GRAM_MIN_LEN = 3

# What people type, mapped to what tool catalogues say instead. Only gaps that the
# indexes cannot close on their own belong here -- "repo" already reaches repository
# by prefix and "mail" already sits inside "email", so neither is listed. Each entry
# was checked against a real ~1900-tool catalogue: the typed word found nothing
# relevant and the catalogue word did (Twilio calls an SMS a Message; no Twilio tool
# says "sms"). Directional: an alternative is added, never substituted.
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "sms": ("message",),
    "text message": ("message",),
    "ticket": ("issue",),
    "bug": ("issue",),
    "pr": ("pull request", "merge request"),
    "mr": ("merge request", "pull request"),
    "pull request": ("merge request",),
    "merge request": ("pull request",),
    "remove": ("delete",),
    "delete": ("remove",),
    "erase": ("delete",),
    "email": ("mail",),
    "inbox": ("mail",),
    # Not "instance": on a real catalogue that meant Jira and Tempo instances, and
    # mapping to it only added noise.
    "vm": ("virtual machine",),
    "db": ("database",),
    "docs": ("documentation",),
    "todo": ("task",),
    "meeting": ("event",),
    "appointment": ("event",),
    "config": ("setting",),
    "certificate": ("ssl", "tls"),
}
_MAX_PHRASE = max(len(k.split()) for k in _SYNONYMS)


@dataclass(frozen=True)
class _Term:
    """One query term and every form that satisfies it."""

    text: str
    alternatives: tuple[str, ...]


def plan_terms(tokens: list[str]) -> list[_Term]:
    """Group query tokens into terms, merging known multi-word phrases.

    "pull request" is one term, not two ANDed words -- otherwise a GitLab tool that
    says "merge request" could never satisfy "pull", whatever its synonyms.
    """
    terms: list[_Term] = []
    i = 0
    while i < len(tokens):
        for size in range(min(_MAX_PHRASE, len(tokens) - i), 0, -1):
            text = " ".join(tokens[i : i + size])
            if size == 1 or text in _SYNONYMS:
                terms.append(_Term(text, _SYNONYMS.get(text, ())))
                i += size
                break
    return terms


def _word_expr(form: str, typed: bool) -> str:
    """Word-index expression for one form of a term.

    What the user typed is a prefix query when it is long enough to mean something as
    a prefix; a two-letter prefix such as "pr" matches project, print and prompt, so
    short input must be a whole word. Synonyms are whole words or phrases (porter
    still stems them). A phrase is never a prefix query.
    """
    if " " in form:
        return f'"{form}"'
    return f'"{form}"*' if typed and len(form) >= _GRAM_MIN_LEN else f'"{form}"'


def _gram_forms(term: _Term) -> list[str]:
    """Substring forms of a term for the trigram index.

    Phrases are joined, so "merge request" is also found inside a camelCase
    mergeRequest.
    """
    forms = [term.text.replace(" ", "")] + [a.replace(" ", "") for a in term.alternatives]
    return [f for f in forms if len(f) >= _GRAM_MIN_LEN]


def _type_of(prop: object) -> str:
    if not isinstance(prop, dict):
        return "any"
    kind = prop.get("type")
    if isinstance(kind, list):
        return "|".join(str(k) for k in kind)
    if kind:
        return str(kind)
    for key in ("anyOf", "oneOf"):
        options = prop.get(key)
        if isinstance(options, list) and options:
            return "|".join(_type_of(o) for o in options)
    if "enum" in prop:
        return "enum"
    return "any"


def render_signature(schema: dict[str, Any] | None, width: int = 140) -> str:
    """Render a JSON schema's top-level properties as a one-line signature."""
    if not isinstance(schema, dict):
        return "(…)"
    props = schema.get("properties")
    if not isinstance(props, dict) or not props:
        return "()"
    required = set(schema.get("required") or [])
    # Required parameters first: they are the ones a caller cannot leave out.
    names = sorted(props, key=lambda n: (n not in required, list(props).index(n)))
    parts = [
        f"{n}{'' if n in required else '?'}: {_type_of(props[n]).replace('null', '').strip('|') or 'null'}"
        for n in names
    ]
    text = "(" + ", ".join(parts) + ")"
    if len(text) > width:
        text = text[: width - 2].rstrip(", ") + "…)"
    return text


@dataclass(frozen=True)
class SearchResult:
    """What a search found, and how much of it the caller is being shown.

    total_matches is reported separately because the caller cannot infer it: a page
    of 20 looks identical whether 20 tools matched or 535 did, and the agent needs
    that difference to decide between narrowing the query and asking for more.
    """

    entries: list["ToolEntry"]
    total_matches: int


@dataclass(frozen=True)
class ToolEntry:
    """One callable tool, as the gateway exposes it."""

    qualified_name: str
    server_name: str
    tool_name: str
    description: str = ""
    schema: dict[str, Any] | None = field(default=None, compare=False)

    def signature(self, width: int = 140) -> str:
        """Top-level parameters as "(name: type, optional?: type)".

        Enough to call most tools without a second round trip; describe_tool has the
        full schema for the ones whose parameters are nested.
        """
        return render_signature(self.schema, width)

    def summary(self, width: int = 110) -> str:
        """A single line: the callable name and the first sentence of its purpose."""
        first = " ".join((self.description or "").split())
        if len(first) > width:
            first = first[: width - 1].rstrip() + "\u2026"
        return f"{self.qualified_name} \u2014 {first}" if first else self.qualified_name


def tokenize(query: str) -> list[str]:
    """Split a query into lowercase terms, dropping everything that is not alphanumeric.

    This is also the sanitiser: an FTS5 MATCH expression is a small language, and
    quotes, asterisks or NEAR in user input would otherwise be read as syntax.
    """
    cleaned = "".join(ch if ch.isalnum() else " " for ch in query.lower())
    return [t for t in cleaned.split() if t]


def build_match_expression(tokens: list[str]) -> str:
    """Turn query terms into a whole-word FTS5 expression, each term a prefix query.

    Terms are ANDed so that adding a word narrows: on a catalogue of this size almost
    everything matches "list" or "get", and an OR would return the catalogue back.
    """
    return " AND ".join(f'"{token}"*' for token in tokens)


def _index(entries: list[ToolEntry]) -> sqlite3.Connection:
    """Build the word and trigram FTS5 indexes over the given tools, in memory.

    Row i of both tables is entries[i]. Rebuilt per search rather than kept in sync:
    it costs tens of milliseconds for ~1900 tools, far inside the latency this has to
    meet, and it buys exactness -- no index to drift from the catalogue, no
    migration, and no triggers to keep correct when a server is mounted or removed.
    """
    db = sqlite3.connect(":memory:")
    rows = [
        (i, e.qualified_name, e.server_name, e.tool_name, e.description or "")
        for i, e in enumerate(entries)
    ]
    for table, tokenizer in (("words", _WORD_TOKENIZER), ("grams", _GRAM_TOKENIZER)):
        db.execute(
            f"CREATE VIRTUAL TABLE {table} USING fts5("
            "qualified_name UNINDEXED, server_name, tool_name, description, "
            f"tokenize='{tokenizer}')"
        )
        db.executemany(
            f"INSERT INTO {table}(rowid, qualified_name, server_name, tool_name, "  # noqa: S608
            "description) VALUES (?,?,?,?,?)",
            rows,
        )
    return db


def _rowids(db: sqlite3.Connection, table: str, expression: str) -> set[int]:
    return {r[0] for r in db.execute(
        f"SELECT rowid FROM {table} WHERE {table} MATCH ?", (expression,)  # noqa: S608
    )}


def _ranks(db: sqlite3.Connection, table: str, expression: str) -> dict[int, float]:
    weights = ",".join(str(w) for w in _BM25_WEIGHTS)
    return dict(db.execute(
        f"SELECT rowid, bm25({table},{weights}) FROM {table} "  # noqa: S608
        f"WHERE {table} MATCH ?",
        (expression,),
    ))


def search_catalogue(
    entries: list[ToolEntry],
    query: str,
    limit: int = 20,
    server: str | None = None,
) -> SearchResult:
    """Rank tools against a query, best first.

    Every query term must match (AND). A term matches a tool if it is a word, or the
    start of a word, in the word index -- or, for terms of three characters or more,
    anywhere inside a word in the trigram index -- or if one of its synonyms does.
    Terms shorter than three characters must match a whole word.

    Ordering puts precision first: a tool named exactly as typed, then tools where
    more terms matched as words before tools that matched only as fragments -- so
    "tag" ranks listRepositoryTags above a tool that merely contains "stage". Within
    that, relevance is the sum of bm25 from both indexes, then the name.

    An empty query is a browse request rather than a match-everything request, so it
    returns the start of the catalogue in name order.
    """
    pool = entries
    if server:
        needle = server.lower()
        pool = [e for e in pool if needle in e.server_name.lower()]

    limit = max(limit, 0)
    tokens = tokenize(query)
    if not tokens:
        ordered = sorted(pool, key=lambda e: e.qualified_name)
        return SearchResult(entries=ordered[:limit], total_matches=len(ordered))
    if not limit or not pool:
        return SearchResult(entries=[], total_matches=0)

    try:
        db = _index(pool)
    except sqlite3.OperationalError:
        # SQLite built without FTS5 (or trigram): search is unavailable, not broken.
        return SearchResult(entries=[], total_matches=0)
    try:
        word_hits: dict[int, int] = {}
        candidates: set[int] | None = None
        word_exprs: list[str] = []
        gram_exprs: list[str] = []
        for term in plan_terms(tokens):
            term_word = [_word_expr(term.text, typed=True)] + [
                _word_expr(a, typed=False) for a in term.alternatives
            ]
            term_gram = [f'"{f}"' for f in _gram_forms(term)]
            word_exprs += term_word
            gram_exprs += term_gram
            by_word = _rowids(db, "words", " OR ".join(term_word))
            for rowid in by_word:
                word_hits[rowid] = word_hits.get(rowid, 0) + 1
            matched = set(by_word)
            if term_gram:
                matched |= _rowids(db, "grams", " OR ".join(term_gram))
            candidates = matched if candidates is None else candidates & matched
            if not candidates:
                return SearchResult(entries=[], total_matches=0)

        word_rank = _ranks(db, "words", " OR ".join(word_exprs))
        gram_rank = _ranks(db, "grams", " OR ".join(gram_exprs)) if gram_exprs else {}
    except sqlite3.OperationalError:
        # A malformed expression must return nothing, never raise at the caller.
        return SearchResult(entries=[], total_matches=0)
    finally:
        db.close()

    # A tool whose whole name is exactly what was typed ("send email" -> send-email)
    # comes first; bm25 alone would rank a longer name that repeats the words, such as
    # send-batch-emails, above it.
    typed = "".join(tokens)

    def exact_name(r: int) -> bool:
        return "".join(tokenize(pool[r].tool_name)) == typed

    # bm25 is negative in SQLite (lower is better), so a missing index scores 0.
    ordered = sorted(
        candidates,
        key=lambda r: (
            not exact_name(r),
            -word_hits.get(r, 0),
            word_rank.get(r, 0.0) + gram_rank.get(r, 0.0),
            pool[r].qualified_name,
        ),
    )
    hits = [pool[r] for r in ordered]
    # Trim by *tool*, not by instance: limit=20 should mean twenty distinct tools to
    # choose from, not twenty rows that might be the same tool on twenty servers.
    kept = [e for group in group_instances(hits)[:limit] for e in group]
    return SearchResult(entries=kept, total_matches=len(candidates))


def group_instances(entries: list[ToolEntry]) -> list[list[ToolEntry]]:
    """Collapse the same tool offered by several server instances into one group.

    Grouping is on the name *and* the description together: two servers can legitimately
    both expose a "search" that does entirely different things, and merging those would
    be a lie. An identical description is strong evidence of the same underlying server
    software run twice -- three Jira instances, say -- which is the case worth collapsing,
    because the description is the bulk of what a listing costs.
    """
    groups: dict[tuple[str, str], list[ToolEntry]] = {}
    order: list[tuple[str, str]] = []
    for entry in entries:
        key = (entry.tool_name, " ".join((entry.description or "").split()))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(entry)
    return [groups[k] for k in order]


def format_results(result: SearchResult, total_catalogue: int, query: str) -> str:
    """Render results compactly enough to be worth sending instead of the catalogue."""
    if not result.entries:
        return (
            f"No tool matches {query!r} among {total_catalogue} tools. "
            "Try fewer or broader terms."
        )

    groups = group_instances(result.entries)
    shown = len(result.entries)
    if shown < result.total_matches:
        header = (
            f"Showing {shown} of {result.total_matches} tools matching {query!r} "
            f"({total_catalogue} in the catalogue). "
            "Narrow the query or raise `limit` to see more."
        )
    else:
        header = f"{result.total_matches} of {total_catalogue} tools match {query!r}:"

    lines = [header, ""]
    for group in groups:
        first = group[0]
        if len(group) == 1:
            lines.append(
                f"  {first.qualified_name}{first.signature()}  [{first.server_name}]"
            )
        else:
            # The description is printed once for the group; the instances differ only
            # in which server they came from, and that is the part worth choosing between.
            lines.append(
                f"  {first.tool_name}{first.signature()}  — on {len(group)} servers:"
            )
            for member in group:
                lines.append(f"      {member.qualified_name}  [{member.server_name}]")
        summary = " ".join((first.description or "").split())
        if summary:
            if len(summary) > 110:
                summary = summary[:109].rstrip() + "\u2026"
            lines.append(f"      {summary}")
    lines += [
        "",
        "Call a tool by its prefixed name (through call_tool if it is not in your tool list); the value in brackets is the server it acts on.",
    ]
    return "\n".join(lines)


def entries_from_rows(rows: list[Any]) -> list[ToolEntry]:
    """Build entries from database rows of (server_id, server_name, name, description).

    tool_schema is optional in the row and may arrive as JSON text, which is what a
    raw query against SQLite's JSON column returns.
    """
    out = []
    for r in rows:
        schema = r.get("tool_schema") if hasattr(r, "get") else None
        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
            except ValueError:
                schema = None
        out.append(
            ToolEntry(
                qualified_name=f"{r['server_id']}_{r['tool_name']}",
                server_name=r["server_name"],
                tool_name=r["tool_name"],
                description=r["tool_description"] or "",
                schema=schema if isinstance(schema, dict) else None,
            )
        )
    return out

SEARCH_TOOL_NAME = "search_tools"
DESCRIBE_TOOL_NAME = "describe_tool"
CALL_TOOL_NAME = "call_tool"
# Names the gateway serves itself rather than proxying. TOOL_LIST_MODE="search"
# advertises exactly these; everything else is reached through call_tool.
META_TOOL_NAMES = frozenset({SEARCH_TOOL_NAME, DESCRIBE_TOOL_NAME, CALL_TOOL_NAME})

LIST_MODE_HEADER = "x-mcp-tool-list-mode"
LIST_MODES = frozenset({"full", "search"})


def current_user_id() -> int | None:
    """Id of the authenticated caller, or None outside an authenticated HTTP request."""
    try:
        from fastmcp.server.dependencies import get_http_request

        user = getattr(get_http_request().state, "user", None)
    except Exception:  # no HTTP request in scope: stdio transport, tests
        return None
    if isinstance(user, dict) and user.get("id") is not None:
        try:
            return int(user["id"])
        except (TypeError, ValueError):
            return None
    return None


def effective_list_mode(configured: str, headers: dict[str, str] | None) -> str:
    """The list mode for this request: the client's header if valid, else config.

    Letting one client opt in by header means search mode can be tried with a single
    agent while every other client keeps the full catalogue.
    """
    requested = ((headers or {}).get(LIST_MODE_HEADER) or "").strip().lower()
    if requested in LIST_MODES:
        return requested
    return configured if configured in LIST_MODES else "full"


async def load_catalogue(user_id: int | None = None) -> list[ToolEntry]:
    """Read the tools this caller may use: active servers, enabled tools, not denied.

    Deliberately not a fan-out to the mounted servers: that is what makes a listing
    slow, and the point of search is to answer without paying it.

    Denials are matched by tool id, i.e. per server. The list filter matches them by
    bare tool name, which also hides a same-named tool on every other server; this
    path must not repeat that, because call_tool trusts it as the authorisation check.
    """
    from sqlalchemy import text

    from mcp_anywhere.database import get_async_session

    async with get_async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT t.server_id AS server_id, s.name AS server_name,
                       t.tool_name AS tool_name, t.tool_description AS tool_description,
                       t.tool_schema AS tool_schema
                FROM mcp_server_tools t
                JOIN mcp_servers s ON s.id = t.server_id
                WHERE s.is_active = 1 AND t.is_enabled = 1
                  AND (:uid IS NULL OR t.id NOT IN (
                        SELECT p.tool_id FROM user_tool_permissions p
                        WHERE p.user_id = :uid AND p.permission = 'deny'))
                """
            ),
            {"uid": user_id},
        )
        rows = [dict(row._mapping) for row in result]
    return entries_from_rows(rows)


def resolve_callable(name: str, catalogue: list[ToolEntry]) -> ToolEntry | None:
    """The catalogue entry call_tool may dispatch to, or None.

    A meta tool is never callable through call_tool: that would only let a caller nest
    the proxy inside itself.
    """
    if not name or name in META_TOOL_NAMES:
        return None
    for entry in catalogue:
        if entry.qualified_name == name:
            return entry
    return None


def coerce_arguments(arguments: object) -> dict[str, Any]:
    """Accept arguments as an object or as JSON text; some clients send the latter."""
    if arguments is None:
        return {}
    if isinstance(arguments, str):
        stripped = arguments.strip()
        if not stripped:
            return {}
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError("arguments must be a JSON object")
        return parsed
    if isinstance(arguments, dict):
        return arguments
    raise TypeError("arguments must be an object")


def register_search_tool(
    router: FastMCP, mounted_ids: Callable[[], Iterable[str]] | None = None
) -> None:
    """Register search_tools, describe_tool and call_tool on the gateway's own router.

    Args:
        router: The gateway's router.
        mounted_ids: Ids of the servers mounted right now. The database says which
            servers are *meant* to run; a server whose mount failed is still active
            there, and without this its tools would be offered and then fail with a
            confusing "not found" when called.
    """

    async def available() -> list[ToolEntry]:
        catalogue = await load_catalogue(current_user_id())
        if mounted_ids is None:
            return catalogue
        live = set(mounted_ids())
        return [e for e in catalogue if e.qualified_name.split("_", 1)[0] in live]

    from fastmcp.exceptions import ToolError
    from fastmcp.tools import Tool

    async def search_tools(
        query: str = "", limit: int = 10, server: str | None = None
    ) -> str:
        """Find tools by keyword across every server behind this gateway.

        Args:
            query: Words to look for in tool names, server names and descriptions.
                Every word must match, so adding a word narrows the result. Plurals and
                word endings are handled. Leave empty to browse.
            limit: Maximum number of distinct tools to return.
            server: Only return tools from servers whose name contains this text.

        Returns:
            Matching tools with their callable name, parameters and the server each
            one acts on, plus how many matched in total.
        """
        catalogue = await available()
        result = search_catalogue(catalogue, query, limit=limit, server=server)
        return format_results(result, len(catalogue), query)

    async def describe_tool(name: str) -> str:
        """Show the full description and input schema of one tool.

        Args:
            name: The tool's full prefixed name, as search_tools returns it.

        Returns:
            JSON with the tool's name, server, description and input_schema.
        """
        entry = resolve_callable(name, await available())
        if entry is None:
            raise ToolError(
                f"No available tool named {name!r}. Use search_tools to find the name."
            )
        schema = entry.schema
        if schema is None:
            # Rows created before schemas were stored get one on the next remount;
            # until then ask the mounted server directly for this one tool.
            try:
                schema = (await router.get_tool(name)).parameters
            except Exception:
                schema = None
        return json.dumps(
            {
                "name": entry.qualified_name,
                "server": entry.server_name,
                "description": entry.description,
                "input_schema": schema,
            },
            indent=2,
        )

    async def call_tool(
        name: str, arguments: dict[str, Any] | str | None = None
    ) -> ToolResult:
        """Run any tool behind this gateway by its full name.

        Use this for tools that are not in your own tool list; this gateway may list
        only its search tools and leave the rest to be found with search_tools.

        Args:
            name: The tool's full prefixed name, as search_tools returns it.
            arguments: The tool's arguments as an object (see describe_tool).

        Returns:
            Exactly what the tool itself returns.
        """
        entry = resolve_callable(name, await available())
        if entry is None:
            raise ToolError(
                f"No available tool named {name!r}: it does not exist, is disabled, or "
                "is not permitted for you. Use search_tools to find the name."
            )
        try:
            args = coerce_arguments(arguments)
        except (ValueError, TypeError) as e:
            raise ToolError(f"Invalid arguments for {name!r}: {e}") from e
        # Through the router, not the tool manager: the call then runs the same
        # middleware chain as a direct call, so auditing and filtering see the real
        # tool rather than call_tool.
        try:
            return await router._call_tool(entry.qualified_name, args)
        except NotFoundError as e:
            raise ToolError(
                f"{name!r} is known but its server ({entry.server_name}) is not "
                "reachable right now."
            ) from e

    # output_schema=None on all three. FastMCP otherwise derives one from the return
    # annotation: for the two text tools it wraps the result as {"result": text},
    # which Claude Code hands the model as escaped JSON; for call_tool, any object
    # schema would make the SDK reject every inner tool that returns text only.
    for fn, tool_name in (
        (search_tools, SEARCH_TOOL_NAME),
        (describe_tool, DESCRIBE_TOOL_NAME),
        (call_tool, CALL_TOOL_NAME),
    ):
        router.add_tool(Tool.from_function(fn, name=tool_name, output_schema=None))
