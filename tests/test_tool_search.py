"""Keyword search over the tool catalogue, backed by SQLite FTS5.

The catalogue this exists for has ~1900 tools and serialises to 2.4 MB, which is
more than an agent can hold or choose from. Search is only useful if it *narrows*
and if it forgives the way people actually type: these tests pin AND semantics,
stemming, prefix matching, and a stable order.

Relevance ranking itself is SQLite's (bm25) and is not re-tested here; what is
tested is the behaviour this module is responsible for.
"""

import pytest

from mcp_anywhere.core.tool_search import (
    ToolEntry,
    build_match_expression,
    entries_from_rows,
    format_results,
    search_catalogue,
    tokenize,
)


def e(qualified, tool, desc="", server="srv"):
    return ToolEntry(qualified_name=qualified, server_name=server, tool_name=tool, description=desc)


CATALOGUE = [
    e("aaa1_create_issue", "create_issue", "Create a new issue in a project", "gitlab-acme"),
    e("bbb2_list_issues", "list_issues", "List issues for a project", "gitlab-acme"),
    e("ccc3_search", "search", "Search for repositories in Docker Hub", "acme-dockerhub"),
    e("ddd4_read_file", "read_file", "Read the content of any file", "files"),
    e("eee5_send_email", "send_email", "Send an email through the API", "resend"),
    e("fff6_createRepository", "createRepository",
      "Create a new repository in the given namespace", "acme-dockerhub"),
    e("ggg7_listRepositoryTags", "listRepositoryTags",
      "List paginated tags by repository", "acme-dockerhub"),
]


def names(result):
    """Tool names of a SearchResult, in the order returned."""
    return [h.tool_name for h in result.entries]


class TestTokenize:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("create issue", ["create", "issue"]),
            ("create_issue", ["create", "issue"]),
            ("  GitLab/Issues  ", ["gitlab", "issues"]),
            ("", []),
            ("   ", []),
            ("a-b.c", ["a", "b", "c"]),
        ],
    )
    def test_tokenize(self, raw, expected):
        assert tokenize(raw) == expected

    @pytest.mark.parametrize("hostile", ['"', "*", "NEAR(a b)", "a OR b", "((", "^x"])
    def test_fts_syntax_in_user_input_cannot_reach_the_query(self, hostile):
        """tokenize is the sanitiser: MATCH is a language, user input is not."""
        assert all(t.isalnum() for t in tokenize(hostile))

    def test_a_hostile_query_returns_results_or_nothing_but_never_raises(self):
        for hostile in ['"', "*", "a OR b", "NEAR(x y)", ")("]:
            search_catalogue(CATALOGUE, hostile)


class TestMatchExpression:
    def test_terms_are_anded_and_prefixed(self):
        expr = build_match_expression(["create", "issue"])
        assert "AND" in expr
        assert expr.count("*") == 2

    def test_single_term(self):
        assert build_match_expression(["docker"]) == '"docker"*'


class TestNarrowing:
    def test_every_term_must_match(self):
        """A second term narrows; an OR would hand back the catalogue."""
        assert names(search_catalogue(CATALOGUE, "create kubernetes")) == []

    def test_adding_a_term_reduces_the_result(self):
        broad = search_catalogue(CATALOGUE, "create").entries
        narrow = search_catalogue(CATALOGUE, "create repository").entries
        assert 0 < len(narrow) < len(broad)

    def test_no_match_returns_empty(self):
        assert search_catalogue(CATALOGUE, "kubernetes helm chart").entries == []


class TestStemming:
    """The gap that made hand-rolled matching untenable: plurals and inflections."""

    @pytest.mark.parametrize(
        "singular,plural",
        [("gitlab issue", "gitlab issues"), ("create issue", "creating issues"),
         ("repository", "repositories")],
    )
    def test_inflected_queries_find_the_same_tools(self, singular, plural):
        # The same tools, not necessarily in the same order: a fragment match can
        # rightly prefer the tool whose text contains the exact form typed.
        assert set(names(search_catalogue(CATALOGUE, singular))) == set(
            names(search_catalogue(CATALOGUE, plural))
        )


class TestPrefixMatching:
    def test_a_partial_word_reaches_a_compound(self):
        """"docker" must reach a server called acme-dockerhub."""
        assert "createRepository" in names(search_catalogue(CATALOGUE, "docker repository"))

    def test_server_name_is_searchable(self):
        hits = search_catalogue(CATALOGUE, "dockerhub").entries
        assert {h.server_name for h in hits} == {"acme-dockerhub"}


class TestLimitsAndFilters:
    def test_limit_is_respected(self):
        assert len(search_catalogue(CATALOGUE, "create", limit=1).entries) == 1

    def test_zero_and_negative_limit_return_nothing(self):
        assert search_catalogue(CATALOGUE, "create", limit=0).entries == []
        assert search_catalogue(CATALOGUE, "create", limit=-5).entries == []

    def test_server_filter(self):
        hits = search_catalogue(CATALOGUE, "create", server="dockerhub").entries
        assert {h.server_name for h in hits} == {"acme-dockerhub"}

    def test_empty_query_browses_in_name_order(self):
        hits = search_catalogue(CATALOGUE, "", limit=3).entries
        assert [h.qualified_name for h in hits] == sorted(h.qualified_name for h in hits)

    def test_empty_catalogue_is_not_an_error(self):
        assert search_catalogue([], "anything").entries == []


class TestStability:
    def test_repeating_a_query_returns_the_same_order(self):
        a = names(search_catalogue(CATALOGUE, "create"))
        b = names(search_catalogue(list(reversed(CATALOGUE)), "create"))
        assert a == b


class TestFormatting:
    def test_summary_is_one_line_and_bounded(self):
        entry = e("x_y", "y", "A " + "very " * 200 + "long description\nwith newlines")
        s = entry.summary()
        assert "\n" not in s and len(s) < 160

    def test_summary_without_description(self):
        assert e("x_y", "y").summary() == "x_y"

    def test_no_results_message_is_actionable(self):
        out = format_results(search_catalogue(CATALOGUE, "zzz nothing"), 1866, "kubernetes")
        assert "1866" in out and "kubernetes" in out

    def test_results_list_every_hit(self):
        res = search_catalogue(CATALOGUE, "create")
        out = format_results(res, 1866, "create")
        assert all(h.qualified_name in out for h in res.entries)


class TestRowMapping:
    def test_builds_qualified_names_from_rows(self):
        rows = [
            {"server_id": "afc9d618", "server_name": "gitlab", "tool_name": "create_issue",
             "tool_description": "Create an issue"},
            {"server_id": "b6ae340b", "server_name": "mermaid", "tool_name": "render",
             "tool_description": None},
        ]
        entries = entries_from_rows(rows)
        assert entries[0].qualified_name == "afc9d618_create_issue"
        assert entries[1].description == "", "a null description must not become 'None'"


class FakeTool:
    def __init__(self, name):
        self.name = name


class TestListMode:
    """TOOL_LIST_MODE trims what is advertised; it must never trim by accident."""

    @staticmethod
    def _apply(monkeypatch, mode, search_enabled, tools):
        from mcp_anywhere.core import middleware as mw

        monkeypatch.setattr(mw.Config, "TOOL_LIST_MODE", mode)
        monkeypatch.setattr(mw.Config, "TOOL_SEARCH_ENABLED", search_enabled)
        return mw._apply_list_mode(tools)

    TOOLS = [FakeTool("search_tools"), FakeTool("aaa1_create_issue"), FakeTool("bbb2_list")]

    def test_full_mode_is_the_default_and_changes_nothing(self, monkeypatch):
        assert self._apply(monkeypatch, "full", True, self.TOOLS) == self.TOOLS

    def test_search_mode_advertises_only_meta_tools(self, monkeypatch):
        out = self._apply(monkeypatch, "search", True, self.TOOLS)
        assert [t.name for t in out] == ["search_tools"]

    def test_search_mode_is_ignored_when_search_is_disabled(self, monkeypatch):
        """Otherwise the catalogue would be hidden with nothing left to find it."""
        assert self._apply(monkeypatch, "search", False, self.TOOLS) == self.TOOLS

    def test_an_unknown_mode_is_treated_as_full(self, monkeypatch):
        assert self._apply(monkeypatch, "banana", True, self.TOOLS) == self.TOOLS


class TestTotalsAndTruncation:
    """The agent cannot tell a complete page from a truncated one without being told."""

    def test_a_truncated_page_says_how_many_matched(self):
        res = search_catalogue(CATALOGUE, "issue", limit=1)
        out = format_results(res, 1867, "issue")
        assert res.total_matches > len(res.entries)
        assert f"of {res.total_matches}" in out
        assert "limit" in out

    def test_a_complete_page_does_not_claim_truncation(self):
        res = search_catalogue(CATALOGUE, "docker tag", limit=20)
        out = format_results(res, 1867, "docker tag")
        assert "Showing" not in out

    def test_total_counts_matches_not_the_catalogue(self):
        res = search_catalogue(CATALOGUE, "issue", limit=1)
        assert 1 < res.total_matches < len(CATALOGUE) + 1


THREE_JIRAS = [
    e("25d54006_jira_delete_issue", "jira_delete_issue", "Delete an existing Jira issue.", "team-c-atlassian"),
    e("34c0dd21_jira_delete_issue", "jira_delete_issue", "Delete an existing Jira issue.", "team-a-jira"),
    e("a3d611f9_jira_delete_issue", "jira_delete_issue", "Delete an existing Jira issue.", "team-b-jira"),
    e("afc9d618_create_issue", "create_issue", "Create an issue", "gitlab-acme"),
]


class TestInstanceGrouping:
    def test_identical_tools_on_several_servers_collapse(self):
        out = format_results(search_catalogue(THREE_JIRAS, "issue", limit=20), 1867, "issue")
        assert out.count("Delete an existing Jira issue.") == 1, "description printed once"
        for entry in THREE_JIRAS[:3]:
            assert entry.qualified_name in out, "every instance stays callable"

    def test_same_name_different_purpose_is_not_collapsed(self):
        """Two servers may both expose "search" and mean different things."""
        pair = [
            e("a_search", "search", "Search Docker Hub repositories", "dockerhub"),
            e("b_search", "search", "Search the Cloudflare documentation", "cloudflare"),
        ]
        out = format_results(search_catalogue(pair, "search", limit=20), 1867, "search")
        assert "on 2 servers" not in out

    def test_limit_counts_distinct_tools_not_instances(self):
        res = search_catalogue(THREE_JIRAS, "issue", limit=2)
        distinct = {en.tool_name for en in res.entries}
        assert len(distinct) == 2, "two tools asked for, two tools returned"
        assert len(res.entries) > 2, "instances of a grouped tool come along with it"


class TestFriendlyServerName:
    def test_the_server_name_is_shown_next_to_the_callable_name(self):
        """afc9d618 says nothing; gitlab-acme says which estate it is."""
        out = format_results(search_catalogue(CATALOGUE, "create issue"), 1867, "create issue")
        assert "gitlab-acme" in out
        assert "aaa1_create_issue" in out


FRAGMENTS = [
    e("ff181935_getPersonalNamespace", "getPersonalNamespace", "Get the personal namespace name",
      "acme-dockerhub"),
    e("ff181935_listRepositoryTags", "listRepositoryTags", "List paginated tags by repository",
      "acme-dockerhub"),
    e("gh000001_search_code", "search_code", "Search code across repositories", "github"),
    e("cf000001_staging_deploy", "staging_deploy", "Deploy the current build", "cloudflare"),
    e("ai000001_ai_chat", "ai_chat", "Talk to a model", "openai"),
]


class TestFragmentsInsideWords:
    """Whole-word indexing cannot see inside "dockerhub" or a camelCase name."""

    def test_a_compound_written_as_two_words_is_found(self):
        """The query that failed live: "hub" is the end of "dockerhub", not a word."""
        found = names(search_catalogue(FRAGMENTS, "docker hub namespace"))
        assert found == ["getPersonalNamespace"]

    def test_a_word_inside_a_camelcase_name_is_found(self):
        assert "listRepositoryTags" in names(search_catalogue(FRAGMENTS, "repository tags"))

    def test_the_other_query_terms_still_narrow(self):
        """"hub" alone also sits inside "github"; "docker" keeps that out."""
        found = names(search_catalogue(FRAGMENTS, "docker hub"))
        assert "search_code" not in found and found

    def test_a_whole_word_match_outranks_a_fragment(self):
        """"tag" is a word in listRepositoryTags and only a fragment of "staging"."""
        found = names(search_catalogue(FRAGMENTS, "tag"))
        assert found.index("listRepositoryTags") < found.index("staging_deploy")

    def test_terms_too_short_for_trigrams_still_match_as_words(self):
        assert names(search_catalogue(FRAGMENTS, "ai")) == ["ai_chat"]

    def test_the_total_counts_fragment_matches_too(self):
        res = search_catalogue(FRAGMENTS, "hub", limit=1)
        assert res.total_matches == 3, "dockerhub twice, github once"


class TestExactNameFirst:
    def test_the_tool_named_exactly_as_typed_comes_first(self):
        cat = [
            e("a_send-batch-emails", "send-batch-emails", "Send a batch of emails; send email to many", "resend"),
            e("b_send-email", "send-email", "Send a single email", "resend"),
        ]
        assert names(search_catalogue(cat, "send email"))[0] == "send-email"

    def test_separators_and_case_do_not_matter(self):
        cat = [e("x_listTags", "listTags", "List tags; list all tags", "s"),
               e("y_list_tags_everywhere", "list_tags_everywhere", "list tags list tags", "s")]
        assert names(search_catalogue(cat, "List-Tags"))[0] == "listTags"


VOCAB = [
    e("tw_CreateMessage", "TwilioApiV2010_CreateMessage", "Send a message", "twilio-main"),
    e("gl_create_merge_request", "create_merge_request", "Open a new merge request", "gitlab"),
    e("gl_mergeRequestNotes", "mergeRequestNotes", "Notes on a change", "gitlab"),
    e("gl_create_project", "create_project", "Create a project", "gitlab"),
    e("gl_print_report", "print_report", "Print a report", "gitlab"),
    e("tr_create_issue", "create_issue", "Create an issue", "tracker"),
    e("dh_delete_repo", "deleteRepository", "Delete a repository", "dockerhub"),
    e("cf_remove_record", "remove_record", "Remove a DNS record", "cloudflare"),
]


class TestSynonyms:
    """Close vocabulary gaps no index can: the word typed is not in the catalogue."""

    def test_sms_finds_twilios_message_tools(self):
        """No Twilio tool says "sms" -- it calls them Messages."""
        assert names(search_catalogue(VOCAB, "twilio sms")) == ["TwilioApiV2010_CreateMessage"]

    def test_a_github_word_reaches_gitlabs_word(self):
        assert "create_merge_request" in names(search_catalogue(VOCAB, "pull request"))

    def test_a_phrase_synonym_reaches_a_camelcase_name(self):
        assert "mergeRequestNotes" in names(search_catalogue(VOCAB, "pull request"))

    def test_an_abbreviation_expands(self):
        assert "create_merge_request" in names(search_catalogue(VOCAB, "pr"))

    def test_a_short_term_is_a_whole_word_not_a_prefix(self):
        """"pr" used to match project and print as a prefix: 707 hits live."""
        found = names(search_catalogue(VOCAB, "pr"))
        assert "create_project" not in found and "print_report" not in found

    def test_ticket_finds_issue_tools(self):
        assert names(search_catalogue(VOCAB, "ticket")) == ["create_issue"]

    def test_synonyms_add_rather_than_replace(self):
        found = names(search_catalogue(VOCAB, "delete"))
        assert "deleteRepository" in found, "the typed word still matches"
        assert "remove_record" in found, "and so does its synonym"

    def test_phrases_are_planned_as_one_term(self):
        from mcp_anywhere.core.tool_search import plan_terms

        terms = plan_terms(tokenize("open pull request"))
        assert [t.text for t in terms] == ["open", "pull request"]
        assert terms[1].alternatives == ("merge request",)

    def test_every_synonym_entry_is_already_normalised(self):
        """Keys and values must survive tokenize() unchanged or they never match."""
        from mcp_anywhere.core.tool_search import _SYNONYMS

        for key, alts in _SYNONYMS.items():
            for form in (key, *alts):
                assert " ".join(tokenize(form)) == form, form
