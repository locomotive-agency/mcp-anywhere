"""The "docker" runtime: a server that ships as a published image.

The runtime was offered by the add/edit forms and documented on the model, but the
builder raised ValueError for it, so choosing it could only ever fail. These tests
pin the behaviour that makes it real: nothing is built, the named image is pulled,
and that reference becomes the image the server runs from.
"""

from unittest.mock import MagicMock, patch

import pytest
from docker.errors import APIError, ImageNotFound

from mcp_anywhere.container.manager import ContainerManager, split_image_ref
from mcp_anywhere.database import MCPServer


@pytest.fixture
def mock_docker_client():
    with patch("mcp_anywhere.container.manager.DockerClient") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client
        yield client


@pytest.fixture
def container_manager(mock_docker_client):
    return ContainerManager()


def make_server(runtime_type="docker", install_command="mcp/dockerhub"):
    server = MagicMock(spec=MCPServer)
    server.id = "abc123"
    server.name = "dockerhub"
    server.runtime_type = runtime_type
    server.install_command = install_command
    server.start_command = "--transport=stdio --username=example"
    return server


class TestSplitImageRef:
    @pytest.mark.parametrize(
        "image,expected",
        [
            ("mcp/dockerhub", ("mcp/dockerhub", "latest")),
            ("mcp/dockerhub:1.2.3", ("mcp/dockerhub", "1.2.3")),
            ("nginx", ("nginx", "latest")),
            ("nginx:alpine", ("nginx", "alpine")),
            ("ghcr.io/owner/img:v2", ("ghcr.io/owner/img", "v2")),
            # a registry port is not a tag
            ("localhost:5000/img", ("localhost:5000/img", "latest")),
            ("localhost:5000/img:dev", ("localhost:5000/img", "dev")),
            # a digest pins exact bytes and is passed through as the tag
            (
                "mcp/dockerhub@sha256:" + "a" * 64,
                ("mcp/dockerhub", "sha256:" + "a" * 64),
            ),
        ],
    )
    def test_split(self, image, expected):
        assert split_image_ref(image) == expected


class TestImageTag:
    def test_docker_runtime_uses_its_published_image(self, container_manager):
        server = make_server(install_command="mcp/dockerhub:1.0")
        assert container_manager.get_image_tag(server) == "mcp/dockerhub:1.0"

    def test_npx_still_gets_a_built_tag(self, container_manager):
        server = make_server(runtime_type="npx", install_command="npm install -g x")
        assert container_manager.get_image_tag(server) == "mcp-anywhere/server-abc123"

    def test_uvx_still_gets_a_built_tag(self, container_manager):
        server = make_server(runtime_type="uvx", install_command="uvx x")
        assert container_manager.get_image_tag(server) == "mcp-anywhere/server-abc123"

    def test_docker_runtime_without_an_image_falls_back(self, container_manager):
        """A blank install_command must not produce the tag "" for a live container."""
        server = make_server(install_command="")
        assert container_manager.get_image_tag(server) == "mcp-anywhere/server-abc123"


class TestBuildPullsInsteadOfBuilding:
    def test_pulls_the_named_image(self, container_manager, mock_docker_client):
        server = make_server(install_command="mcp/dockerhub")
        result = container_manager.build_server_image(server)

        assert result == "mcp/dockerhub"
        mock_docker_client.images.pull.assert_called_once_with(
            "mcp/dockerhub", tag="latest"
        )

    def test_respects_an_explicit_tag(self, container_manager, mock_docker_client):
        server = make_server(install_command="mcp/dockerhub:2.1")
        assert container_manager.build_server_image(server) == "mcp/dockerhub:2.1"
        mock_docker_client.images.pull.assert_called_once_with(
            "mcp/dockerhub", tag="2.1"
        )

    def test_never_opens_a_sandbox_session(self, container_manager):
        """The whole point: no build, so no SandboxSession and no Dockerfile."""
        with patch("mcp_anywhere.container.manager.SandboxSession") as sandbox:
            container_manager.build_server_image(make_server())
        sandbox.assert_not_called()

    def test_missing_image_reference_is_rejected(self, container_manager):
        server = make_server(install_command="   ")
        with pytest.raises(ValueError, match="must name its published image"):
            container_manager.build_server_image(server)

    def test_unknown_image_surfaces_as_runtime_error(
        self, container_manager, mock_docker_client
    ):
        mock_docker_client.images.pull.side_effect = ImageNotFound("nope")
        with pytest.raises(RuntimeError, match="Failed to pull image"):
            container_manager.build_server_image(make_server())

    def test_registry_error_surfaces_as_runtime_error(
        self, container_manager, mock_docker_client
    ):
        mock_docker_client.images.pull.side_effect = APIError("registry down")
        with pytest.raises(RuntimeError, match="Failed to pull image"):
            container_manager.build_server_image(make_server())

    def test_an_unknown_runtime_is_still_rejected(self, container_manager):
        server = make_server(runtime_type="wasm")
        with pytest.raises(ValueError, match="Unsupported runtime type"):
            container_manager.build_server_image(server)
