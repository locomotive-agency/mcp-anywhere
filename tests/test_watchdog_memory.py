"""Memory-limit decisions made by the crash watchdog.

The distinction these tests exist to protect: a container that breached *its own*
cgroup limit needs more memory, while a container the kernel killed because the
*host* ran out does not -- and giving the second one a bigger limit makes the next
host-wide shortage worse. Docker's State.OOMKilled cannot tell them apart; cgroup
v2's memory.events can, because its ``oom`` counter only ever moves on the cgroup's
own limit.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from mcp_anywhere.container.manager import ContainerManager, _cgroup_int
from mcp_anywhere.core import mcp_manager as mm


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point the override file at a temp dir."""
    monkeypatch.setattr(mm.Config, "DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def server():
    s = MagicMock()
    s.id = "srv-1"
    s.name = "test-server"
    return s


def _stats(limit_ooms=0, kills=0, peak_bytes=None, limit_bytes=None):
    return {
        "limit_ooms": limit_ooms,
        "kills": kills,
        "peak_bytes": peak_bytes,
        "limit_bytes": limit_bytes,
    }


def _manager(stats, uptime=None):
    cm = MagicMock()
    cm.read_cgroup_memory.return_value = stats
    cm.container_uptime_seconds.return_value = uptime
    return cm


QUIET_PEAK = 256 * 1024 * 1024  # half of the 512m default
BUSY_PEAK = 500 * 1024 * 1024
LONG_UPTIME = mm.DEESCALATE_MIN_UPTIME_SECONDS + 1


class TestEscalation:
    def test_escalates_when_the_container_hit_its_own_limit(self, data_dir, server):
        mm.review_server_memory(server, _manager(_stats(limit_ooms=3, kills=3)))
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT

    def test_host_level_oom_does_not_escalate(self, data_dir, server):
        """The September signature: processes killed, own limit never reached."""
        mm.review_server_memory(server, _manager(_stats(limit_ooms=0, kills=5)))
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT
        assert not mm._mem_overrides_path().exists()

    def test_unreadable_cgroup_is_not_treated_as_no_oom(self, data_dir, server):
        mm.review_server_memory(server, _manager(None))
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT

    def test_escalation_is_idempotent(self, data_dir, server):
        cm = _manager(_stats(limit_ooms=1, kills=1))
        mm.review_server_memory(server, cm)
        mm.review_server_memory(server, cm)
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT

    def test_limit_event_on_an_escalated_server_does_not_raise_further(
        self, data_dir, server
    ):
        mm.set_server_memory_limit(server.id, mm.ESCALATED_MEMORY_LIMIT)
        mm.review_server_memory(server, _manager(_stats(limit_ooms=9, kills=9)))
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT


class TestDeEscalation:
    def test_de_escalates_after_a_long_quiet_run(self, data_dir, server):
        mm.set_server_memory_limit(server.id, mm.ESCALATED_MEMORY_LIMIT)
        mm.review_server_memory(
            server, _manager(_stats(peak_bytes=QUIET_PEAK), LONG_UPTIME)
        )
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT

    def test_a_high_peak_keeps_the_headroom(self, data_dir, server):
        mm.set_server_memory_limit(server.id, mm.ESCALATED_MEMORY_LIMIT)
        mm.review_server_memory(
            server, _manager(_stats(peak_bytes=BUSY_PEAK), LONG_UPTIME)
        )
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT

    def test_a_short_run_proves_nothing(self, data_dir, server):
        mm.set_server_memory_limit(server.id, mm.ESCALATED_MEMORY_LIMIT)
        mm.review_server_memory(
            server, _manager(_stats(peak_bytes=QUIET_PEAK), 3600)
        )
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT

    def test_unknown_peak_keeps_the_headroom(self, data_dir, server):
        mm.set_server_memory_limit(server.id, mm.ESCALATED_MEMORY_LIMIT)
        mm.review_server_memory(
            server, _manager(_stats(peak_bytes=None), LONG_UPTIME)
        )
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT

    def test_unknown_uptime_keeps_the_headroom(self, data_dir, server):
        mm.set_server_memory_limit(server.id, mm.ESCALATED_MEMORY_LIMIT)
        mm.review_server_memory(
            server, _manager(_stats(peak_bytes=QUIET_PEAK), None)
        )
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT

    def test_never_goes_below_the_default(self, data_dir, server):
        mm.review_server_memory(
            server, _manager(_stats(peak_bytes=1024), LONG_UPTIME)
        )
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT
        assert not mm._mem_overrides_path().exists()


class TestOverrideFile:
    def test_set_get_clear_roundtrip(self, data_dir, server):
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT
        mm.set_server_memory_limit(server.id, mm.ESCALATED_MEMORY_LIMIT)
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT
        mm.clear_server_memory_limit(server.id)
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT

    def test_clearing_one_server_leaves_the_others(self, data_dir):
        mm.set_server_memory_limit("a", mm.ESCALATED_MEMORY_LIMIT)
        mm.set_server_memory_limit("b", mm.ESCALATED_MEMORY_LIMIT)
        mm.clear_server_memory_limit("a")
        assert mm.get_server_memory_limit("a") == mm.DEFAULT_MEMORY_LIMIT
        assert mm.get_server_memory_limit("b") == mm.ESCALATED_MEMORY_LIMIT

    def test_clearing_is_a_noop_when_nothing_is_stored(self, data_dir):
        mm.clear_server_memory_limit("never-seen")  # must not raise
        assert not mm._mem_overrides_path().exists()

    @pytest.mark.parametrize("content", ["[]", '"a string"', "17", "null"])
    def test_valid_json_that_is_not_an_object_falls_back(
        self, data_dir, server, content
    ):
        """A damaged file must be no worse than a missing one, not raise."""
        mm._mem_overrides_path().write_text(content)
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT

    def test_corrupt_json_falls_back(self, data_dir, server):
        mm._mem_overrides_path().write_text("{not json")
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT

    def test_a_non_string_limit_falls_back(self, data_dir, server):
        mm._mem_overrides_path().write_text('{"srv-1": 512}')
        assert mm.get_server_memory_limit(server.id) == mm.DEFAULT_MEMORY_LIMIT

    def test_a_damaged_file_does_not_break_a_review(self, data_dir, server):
        """The regression this guards: every healthy-server review used to raise."""
        mm._mem_overrides_path().write_text("[]")
        mm.review_server_memory(server, _manager(_stats(limit_ooms=2, kills=2)))
        assert mm.get_server_memory_limit(server.id) == mm.ESCALATED_MEMORY_LIMIT


class TestLimitParsing:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("512m", 536870912),
            ("1g", 1073741824),
            ("64k", 65536),
            ("100b", 100),
            ("1024", 1024),
            ("max", None),
            ("", None),
            ("   ", None),
            ("12x", None),
            ("m", None),
        ],
    )
    def test_limit_to_bytes(self, text, expected):
        assert mm._limit_to_bytes(text) == expected


class TestCgroupIntHelper:
    @pytest.mark.parametrize(
        "text,expected",
        [("76054528\n", 76054528), ("max\n", None), ("", None), (None, None)],
    )
    def test_cgroup_int(self, text, expected):
        assert _cgroup_int(text) == expected


EVENTS_CLEAN = b"low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n"
EVENTS_OWN_LIMIT = b"low 0\nhigh 4\nmax 7\noom 3\noom_kill 3\noom_group_kill 0\n"
EVENTS_GLOBAL_ONLY = b"low 0\nhigh 0\nmax 0\noom 0\noom_kill 5\noom_group_kill 0\n"


@pytest.fixture
def mock_docker_client():
    with patch("mcp_anywhere.container.manager.DockerClient") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client
        yield client


@pytest.fixture
def container_manager(mock_docker_client):
    return ContainerManager()


def _wire_container(client, files):
    """Make exec_run answer per cgroup path; a missing key exits non-zero."""
    container = MagicMock()

    def exec_run(cmd, **kwargs):
        path = cmd[-1]
        if path in files:
            return (0, files[path])
        return (1, b"cat: no such file")

    container.exec_run.side_effect = exec_run
    client.containers.get.return_value = container
    return container


class TestReadCgroupMemory:
    def test_reads_events_peak_and_limit(self, container_manager, mock_docker_client):
        _wire_container(
            mock_docker_client,
            {
                ContainerManager._CGROUP_EVENTS: EVENTS_OWN_LIMIT,
                ContainerManager._CGROUP_PEAK: b"76054528\n",
                ContainerManager._CGROUP_MAX: b"536870912\n",
            },
        )
        stats = container_manager.read_cgroup_memory("srv-1")
        assert stats == {
            "limit_ooms": 3,
            "kills": 3,
            "peak_bytes": 76054528,
            "limit_bytes": 536870912,
        }

    def test_separates_a_global_oom_from_a_limit_breach(
        self, container_manager, mock_docker_client
    ):
        _wire_container(
            mock_docker_client,
            {
                ContainerManager._CGROUP_EVENTS: EVENTS_GLOBAL_ONLY,
                ContainerManager._CGROUP_PEAK: b"220232000\n",
                ContainerManager._CGROUP_MAX: b"536870912\n",
            },
        )
        stats = container_manager.read_cgroup_memory("srv-1")
        assert stats["limit_ooms"] == 0
        assert stats["kills"] == 5

    def test_a_missing_peak_file_does_not_lose_the_events(
        self, container_manager, mock_docker_client
    ):
        _wire_container(
            mock_docker_client,
            {ContainerManager._CGROUP_EVENTS: EVENTS_CLEAN},
        )
        stats = container_manager.read_cgroup_memory("srv-1")
        assert stats["limit_ooms"] == 0
        assert stats["peak_bytes"] is None
        assert stats["limit_bytes"] is None

    def test_unlimited_container_reports_no_limit(
        self, container_manager, mock_docker_client
    ):
        _wire_container(
            mock_docker_client,
            {
                ContainerManager._CGROUP_EVENTS: EVENTS_CLEAN,
                ContainerManager._CGROUP_MAX: b"max\n",
            },
        )
        assert container_manager.read_cgroup_memory("srv-1")["limit_bytes"] is None

    def test_unreadable_events_returns_none(
        self, container_manager, mock_docker_client
    ):
        _wire_container(mock_docker_client, {})
        assert container_manager.read_cgroup_memory("srv-1") is None

    def test_garbage_events_returns_none(self, container_manager, mock_docker_client):
        _wire_container(
            mock_docker_client,
            {ContainerManager._CGROUP_EVENTS: b"not a cgroup file\n"},
        )
        assert container_manager.read_cgroup_memory("srv-1") is None

    def test_missing_container_returns_none(
        self, container_manager, mock_docker_client
    ):
        from docker.errors import NotFound

        mock_docker_client.containers.get.side_effect = NotFound("gone")
        assert container_manager.read_cgroup_memory("srv-1") is None


class TestContainerUptime:
    def test_parses_rfc3339_with_nanoseconds(
        self, container_manager, mock_docker_client
    ):
        started = datetime.now(UTC) - timedelta(days=3)
        stamp = started.strftime("%Y-%m-%dT%H:%M:%S.%f") + "123456789Z"
        container = MagicMock()
        container.attrs = {"State": {"StartedAt": stamp}}
        mock_docker_client.containers.get.return_value = container

        uptime = container_manager.container_uptime_seconds("srv-1")
        assert uptime is not None
        assert abs(uptime - 3 * 86400) < 120

    def test_missing_timestamp_returns_none(
        self, container_manager, mock_docker_client
    ):
        container = MagicMock()
        container.attrs = {"State": {}}
        mock_docker_client.containers.get.return_value = container
        assert container_manager.container_uptime_seconds("srv-1") is None

    def test_unparseable_timestamp_returns_none(
        self, container_manager, mock_docker_client
    ):
        container = MagicMock()
        container.attrs = {"State": {"StartedAt": "not-a-date"}}
        mock_docker_client.containers.get.return_value = container
        assert container_manager.container_uptime_seconds("srv-1") is None
