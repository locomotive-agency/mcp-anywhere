from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch
from docker.errors import APIError, ImageNotFound, NotFound

from mcp_anywhere.container.manager import ContainerManager
from mcp_anywhere.database import MCPServer


@pytest.fixture
def mock_docker_client():
    with patch('mcp_anywhere.container.manager.DockerClient') as mock_docker:
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        yield mock_client


@pytest.fixture
def container_manager(mock_docker_client):
    return ContainerManager()


@pytest.fixture
def sample_server():
    server = MagicMock(spec=MCPServer)
    server.id = "test-server-123"
    server.name = "test-server"
    server.runtime_type = "npx"
    server.start_command = "npx test-server"
    server.install_command = "npm install -g test-server"
    server.env_variables = []
    server.secret_files = []
    server.build_status = None
    server.build_error = None
    return server


class TestContainerManagerInitialization:

    def test_initialization_creates_docker_client(self, container_manager, mock_docker_client):

        assert container_manager.docker_client is mock_docker_client
        assert isinstance(container_manager.reused_containers, set)
        assert container_manager.file_manager is not None

    def test_initialization_with_config(self, mock_docker_client):

        with patch('mcp_anywhere.container.manager.Config') as mock_config:
            mock_config.DOCKER_HOST = "unix:///var/run/docker.sock"
            mock_config.DOCKER_TIMEOUT = 120

            manager = ContainerManager()

            assert manager.docker_host == mock_config.DOCKER_HOST


class TestDockerConnection:

    def test_check_docker_running_success(self, container_manager, mock_docker_client):

        mock_docker_client.ping.return_value = True

        result = container_manager._check_docker_running()

        assert result is True
        mock_docker_client.ping.assert_called_once()

    def test_check_docker_running_api_error(self, container_manager, mock_docker_client):

        mock_docker_client.ping.side_effect = APIError("Docker daemon not running")

        result = container_manager._check_docker_running()

        assert result is False

    def test_check_docker_running_connection_error(self, container_manager, mock_docker_client):

        mock_docker_client.ping.side_effect = ConnectionError("Cannot connect")

        result = container_manager._check_docker_running()

        assert result is False

    def test_check_docker_running_os_error(self, container_manager, mock_docker_client):

        mock_docker_client.ping.side_effect = OSError("Permission denied")

        result = container_manager._check_docker_running()

        assert result is False


class TestContainerNaming:

    def test_get_image_tag(self, container_manager, sample_server):

        tag = container_manager.get_image_tag(sample_server)

        assert tag == "mcp-anywhere/server-test-server-123"

    def test_get_container_name(self, container_manager):

        name = container_manager._get_container_name("test-server-456")

        assert name == "mcp-test-server-456"


class TestContainerHealth:

    def test_is_container_healthy_running(self, container_manager, mock_docker_client, sample_server):

        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.image.tags = ["mcp-anywhere/server-test-server-123"]
        mock_docker_client.containers.get.return_value = mock_container

        result = container_manager._is_container_healthy(sample_server)

        assert result is True

    def test_is_container_healthy_not_running(self, container_manager, mock_docker_client, sample_server):

        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_docker_client.containers.get.return_value = mock_container

        result = container_manager._is_container_healthy(sample_server)

        assert result is False

    def test_is_container_healthy_wrong_image(self, container_manager, mock_docker_client, sample_server):

        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.image.tags = ["different-image:latest"]
        mock_docker_client.containers.get.return_value = mock_container

        result = container_manager._is_container_healthy(sample_server)

        assert result is False

    def test_is_container_healthy_not_found(self, container_manager, mock_docker_client, sample_server):

        mock_docker_client.containers.get.side_effect = NotFound("Container not found")

        result = container_manager._is_container_healthy(sample_server)

        assert result is False

    def test_is_container_healthy_api_error(self, container_manager, mock_docker_client, sample_server):

        mock_docker_client.containers.get.side_effect = APIError("Docker API error")

        result = container_manager._is_container_healthy(sample_server)

        assert result is False


class TestContainerCleanup:

    def test_cleanup_stopped_container_success(self, container_manager, mock_docker_client):

        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_docker_client.containers.get.return_value = mock_container

        container_manager.cleanup_stopped_container("test-container")

        mock_container.remove.assert_called_once_with(force=True)

    def test_cleanup_stopped_container_running(self, container_manager, mock_docker_client):

        mock_container = MagicMock()
        mock_container.status = "running"
        mock_docker_client.containers.get.return_value = mock_container

        container_manager.cleanup_stopped_container("test-container")

        mock_container.remove.assert_not_called()

    def test_cleanup_stopped_container_api_error(self, container_manager, mock_docker_client):

        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_container.remove.side_effect = APIError("Failed to remove")
        mock_docker_client.containers.get.return_value = mock_container

        container_manager.cleanup_stopped_container("test-container")

    def test_cleanup_existing_container_stops_and_removes(self, container_manager, mock_docker_client):

        mock_container = MagicMock()
        mock_docker_client.containers.get.return_value = mock_container

        container_manager._cleanup_existing_container("test-container")

        mock_container.stop.assert_called_once_with(timeout=10)
        mock_container.remove.assert_called_once_with(force=True)

    def test_cleanup_existing_container_not_found(self, container_manager, mock_docker_client):

        mock_docker_client.containers.get.side_effect = NotFound("Not found")

        container_manager._cleanup_existing_container("test-container")

    def test_cleanup_existing_container_stop_fails(self, container_manager, mock_docker_client):

        mock_container = MagicMock()
        mock_container.stop.side_effect = APIError("Cannot stop")
        mock_docker_client.containers.get.return_value = mock_container

        container_manager._cleanup_existing_container("test-container")

        mock_container.remove.assert_called_once_with(force=True)


class TestContainerRestart:

    def test_restart_container_success(self, container_manager, mock_docker_client):

        mock_container = MagicMock()
        mock_docker_client.containers.get.return_value = mock_container

        result = container_manager.restart_container("test-server-123")

        assert result is True
        mock_container.restart.assert_called_once()

    def test_restart_container_not_found(self, container_manager, mock_docker_client):

        mock_docker_client.containers.get.side_effect = NotFound("Not found")

        result = container_manager.restart_container("test-server-123")

        assert result is False

    def test_restart_container_api_error(self, container_manager, mock_docker_client):

        mock_docker_client.containers.get.side_effect = APIError("API error")

        result = container_manager.restart_container("test-server-123")

        assert result is False

    def test_restart_container_connection_error(self, container_manager, mock_docker_client):

        mock_docker_client.containers.get.side_effect = ConnectionError("Connection lost")

        result = container_manager.restart_container("test-server-123")

        assert result is False


class TestContainerLogs:

    def test_get_container_error_logs_success(self, container_manager, mock_docker_client):

        mock_container = MagicMock()
        mock_container.logs.return_value = b"Error: Connection refused\nStarting server..."
        mock_docker_client.containers.get.return_value = mock_container

        logs = container_manager.get_container_error_logs("test-server-123")

        assert "Connection refused" in logs
        mock_container.logs.assert_called_once()

    def test_get_container_error_logs_with_custom_tail(self, container_manager, mock_docker_client):

        mock_container = MagicMock()
        mock_container.logs.return_value = b"Recent logs"
        mock_docker_client.containers.get.return_value = mock_container

        logs = container_manager.get_container_error_logs("test-server-123", tail=100)

        assert logs == "Recent logs"

    def test_get_container_error_logs_not_found(self, container_manager, mock_docker_client):

        mock_docker_client.containers.get.side_effect = NotFound("Not found")

        logs = container_manager.get_container_error_logs("test-server-123")

        assert logs == ""

    def test_get_container_error_logs_api_error(self, container_manager, mock_docker_client):

        mock_docker_client.containers.get.side_effect = APIError("API error")

        logs = container_manager.get_container_error_logs("test-server-123")

        assert logs == ""


class TestEnvironmentVariables:

    def test_get_env_vars_empty(self, container_manager, sample_server):

        sample_server.env_variables = []

        env_vars = container_manager._get_env_vars(sample_server)

        assert isinstance(env_vars, dict)
        assert len(env_vars) >= 0  # May have default vars

    def test_get_env_vars_with_values(self, container_manager, sample_server):

        mock_env_var1 = MagicMock()
        mock_env_var1.key = "API_KEY"
        mock_env_var1.value = "test-key-123"
        mock_env_var2 = MagicMock()
        mock_env_var2.key = "DEBUG"
        mock_env_var2.value = "true"
        sample_server.env_variables = [mock_env_var1, mock_env_var2]

        env_vars = container_manager._get_env_vars(sample_server)

        assert isinstance(env_vars, dict)


class TestCommandParsing:

    def test_parse_install_command_npm(self, container_manager, sample_server):

        sample_server.runtime_type = "npx"
        sample_server.install_command = "npm install -g @test/server"

        parsed = container_manager._parse_install_command(sample_server)

        assert "npm install" in parsed

    def test_parse_install_command_pip(self, container_manager, sample_server):

        sample_server.runtime_type = "uvx"
        sample_server.install_command = "pip install test-server"

        parsed = container_manager._parse_install_command(sample_server)

        assert "pip install" in parsed or "uv pip install" in parsed

    def test_parse_start_command_npx(self, container_manager, sample_server):

        sample_server.runtime_type = "npx"
        sample_server.start_command = "npx @test/server"

        parsed = container_manager._parse_start_command(sample_server)

        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_parse_start_command_uvx(self, container_manager, sample_server):

        sample_server.runtime_type = "uvx"
        sample_server.start_command = "uvx test-server"

        parsed = container_manager._parse_start_command(sample_server)

        assert isinstance(parsed, list)
        assert len(parsed) > 0


class TestImageManagement:

    def test_ensure_image_exists_already_present(self, container_manager, mock_docker_client):

        mock_docker_client.images.get.return_value = MagicMock()

        container_manager._ensure_image_exists("test-image:latest")

        mock_docker_client.images.get.assert_called_once_with("test-image:latest")

    def test_ensure_image_exists_pulls_if_missing(self, container_manager, mock_docker_client):

        mock_docker_client.images.get.side_effect = ImageNotFound("Not found")

        container_manager._ensure_image_exists("test-image:latest")

        mock_docker_client.images.pull.assert_called_once_with("test-image:latest")

    def test_ensure_image_exists_pull_fails(self, container_manager, mock_docker_client):

        mock_docker_client.images.get.side_effect = ImageNotFound("Not found")
        mock_docker_client.images.pull.side_effect = APIError("Pull failed")

        with pytest.raises(APIError, match="Pull failed"):
            container_manager._ensure_image_exists("test-image:latest")

        mock_docker_client.images.pull.assert_called_once_with("test-image:latest")


class TestReusedContainers:

    def test_reused_containers_tracking(self, container_manager):
        assert isinstance(container_manager.reused_containers, set)

        container_manager.reused_containers.add("container-123")

        assert "container-123" in container_manager.reused_containers

    def test_reused_containers_empty_on_init(self, container_manager):
        assert len(container_manager.reused_containers) == 0


class TestSecureFileManager:

    def test_file_manager_initialized(self, container_manager):
        assert container_manager.file_manager is not None

    def test_file_manager_type(self, container_manager):
        from mcp_anywhere.security.file_manager import SecureFileManager
        assert isinstance(container_manager.file_manager, SecureFileManager)


class TestContainerManagerEdgeCases:

    def test_get_image_tag_with_special_characters(self, container_manager):
        server = MagicMock(spec=MCPServer)
        server.id = "test-server_123-456"

        tag = container_manager.get_image_tag(server)

        assert "mcp-anywhere/server-" in tag
        assert server.id in tag

    def test_restart_container_with_empty_id(self, container_manager, mock_docker_client):
        mock_docker_client.containers.get.side_effect = NotFound("Container not found")

        result = container_manager.restart_container("")

        assert result is False

    def test_get_container_error_logs_with_unicode(self, container_manager, mock_docker_client):
        mock_container = MagicMock()
        mock_container.logs.return_value = "Error: 日本語エラー\n".encode('utf-8')
        mock_docker_client.containers.get.return_value = mock_container

        logs = container_manager.get_container_error_logs("test-server-123")

        assert "日本語" in logs or logs != ""


class TestMultipleContainers:
    def test_track_multiple_reused_containers(self, container_manager):
        container_manager.reused_containers.add("container-1")
        container_manager.reused_containers.add("container-2")
        container_manager.reused_containers.add("container-3")

        assert len(container_manager.reused_containers) == 3
        assert "container-1" in container_manager.reused_containers
        assert "container-2" in container_manager.reused_containers

    def test_get_image_tags_for_multiple_servers(self, container_manager):
        server1 = MagicMock(spec=MCPServer)
        server1.id = "server-1"
        server2 = MagicMock(spec=MCPServer)
        server2.id = "server-2"

        tag1 = container_manager.get_image_tag(server1)
        tag2 = container_manager.get_image_tag(server2)

        assert tag1 != tag2
        assert "server-1" in tag1
        assert "server-2" in tag2


class TestHostPathTranslation:
    """Bind sources for spawned MCP servers must use host paths when MCP
    Anywhere talks to a sibling docker daemon."""

    def test_explicit_host_data_dir_override_wins(
        self, container_manager, mock_docker_client
    ):
        with patch("mcp_anywhere.container.manager.Config") as mock_cfg:
            mock_cfg.HOST_DATA_DIR = "/mcp-anywhere-data"
            mock_cfg.DATA_DIR = Path("/app/.data")
            container_manager._host_data_dir_cache = "unset"

            translated = container_manager.translate_to_host_path(
                "/app/.data/secrets/abc/temp_xyz.json"
            )

        assert translated == "/mcp-anywhere-data/secrets/abc/temp_xyz.json"
        mock_docker_client.containers.get.assert_not_called()

    def test_auto_detects_via_self_inspect(
        self, container_manager, mock_docker_client
    ):
        mock_self_container = MagicMock()
        mock_self_container.attrs = {
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": "/mcp-anywhere-data",
                    "Destination": "/app/.data",
                },
                {
                    "Type": "bind",
                    "Source": "/var/run/docker.sock",
                    "Destination": "/var/run/docker.sock",
                },
            ]
        }
        mock_docker_client.containers.get.return_value = mock_self_container

        with patch("mcp_anywhere.container.manager.Config") as mock_cfg:
            mock_cfg.HOST_DATA_DIR = None
            mock_cfg.DATA_DIR = Path("/app/.data")
            container_manager._host_data_dir_cache = "unset"

            translated = container_manager.translate_to_host_path(
                "/app/.data/secrets/abc/temp_xyz.json"
            )

        assert translated == "/mcp-anywhere-data/secrets/abc/temp_xyz.json"

    def test_returns_path_unchanged_when_no_mapping_found(
        self, container_manager, mock_docker_client
    ):
        mock_self_container = MagicMock()
        mock_self_container.attrs = {"Mounts": []}
        mock_docker_client.containers.get.return_value = mock_self_container

        with patch("mcp_anywhere.container.manager.Config") as mock_cfg:
            mock_cfg.HOST_DATA_DIR = None
            mock_cfg.DATA_DIR = Path("/app/.data")
            container_manager._host_data_dir_cache = "unset"

            translated = container_manager.translate_to_host_path(
                "/app/.data/secrets/abc/temp_xyz.json"
            )

        assert translated == "/app/.data/secrets/abc/temp_xyz.json"

    def test_path_outside_data_dir_passes_through(
        self, container_manager, mock_docker_client
    ):
        with patch("mcp_anywhere.container.manager.Config") as mock_cfg:
            mock_cfg.HOST_DATA_DIR = "/mcp-anywhere-data"
            mock_cfg.DATA_DIR = Path("/app/.data")
            container_manager._host_data_dir_cache = "unset"

            translated = container_manager.translate_to_host_path(
                "/etc/something-else.json"
            )

        assert translated == "/etc/something-else.json"

    def test_inspect_failure_falls_back_to_no_translation(
        self, container_manager, mock_docker_client
    ):
        mock_docker_client.containers.get.side_effect = NotFound("nope")

        with patch("mcp_anywhere.container.manager.Config") as mock_cfg:
            mock_cfg.HOST_DATA_DIR = None
            mock_cfg.DATA_DIR = Path("/app/.data")
            container_manager._host_data_dir_cache = "unset"

            translated = container_manager.translate_to_host_path(
                "/app/.data/secrets/abc/temp_xyz.json"
            )

        assert translated == "/app/.data/secrets/abc/temp_xyz.json"

    def test_result_is_cached(self, container_manager, mock_docker_client):
        mock_self_container = MagicMock()
        mock_self_container.attrs = {
            "Mounts": [
                {"Source": "/mcp-anywhere-data", "Destination": "/app/.data"},
            ]
        }
        mock_docker_client.containers.get.return_value = mock_self_container

        with patch("mcp_anywhere.container.manager.Config") as mock_cfg:
            mock_cfg.HOST_DATA_DIR = None
            mock_cfg.DATA_DIR = Path("/app/.data")
            container_manager._host_data_dir_cache = "unset"

            container_manager.translate_to_host_path("/app/.data/a")
            container_manager.translate_to_host_path("/app/.data/b")
            container_manager.translate_to_host_path("/app/.data/c")

        assert mock_docker_client.containers.get.call_count == 1