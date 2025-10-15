"""Test container reuse on application restart."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_anywhere.container.manager import ContainerManager
from mcp_anywhere.database import MCPServer


class TestContainerReuse:
    """Test container reuse functionality on restart."""

    @pytest.mark.asyncio
    async def test_reused_containers_not_cleaned_up(self):
        """Test that reused containers are not cleaned up during mount_built_servers."""
        from mcp_anywhere.core.mcp_manager import MCPManager
        from fastmcp import FastMCP
        
        # Create mock router
        mock_router = MagicMock(spec=FastMCP)
        
        # Create mock servers
        server1 = MagicMock(spec=MCPServer)
        server1.id = "server1"
        server1.name = "test-server-1"
        server1.runtime_type = "uvx"
        server1.start_command = "uvx test-server-1"
        server1.build_status = "built"
        server1.build_error = None
        server1.env_variables = []
        server1.secret_files = []
        
        server2 = MagicMock(spec=MCPServer)
        server2.id = "server2"
        server2.name = "test-server-2"
        server2.runtime_type = "uvx"
        server2.start_command = "uvx test-server-2"
        server2.build_status = "built"
        server2.build_error = None
        server2.env_variables = []
        server2.secret_files = []
        
        # Create container manager
        container_manager = ContainerManager()
        
        # Mark server1 as reused (healthy container from previous run)
        container_manager.reused_containers.add("mcp-server1")
        
        # Create MCP manager
        mcp_manager = MCPManager(router=mock_router)
        
        # Mock database functions
        with patch('mcp_anywhere.container.manager.get_built_servers') as mock_get_built:
            mock_get_built.return_value = [server1, server2]
            
            with patch('mcp_anywhere.container.manager.get_async_session'):
                # Track cleanup calls
                cleanup_calls = []
                
                with patch.object(container_manager, '_cleanup_existing_container') as mock_cleanup:
                    def track_cleanup(container_name):
                        cleanup_calls.append(container_name)
                    
                    mock_cleanup.side_effect = track_cleanup
                    
                    # Mock add_server to avoid actual connection attempts
                    with patch.object(mcp_manager, 'add_server') as mock_add_server:
                        mock_add_server.return_value = []
                        
                        # Mock database session
                        with patch('mcp_anywhere.container.manager.store_server_tools'):
                            await container_manager.mount_built_servers(mcp_manager)
                        
                        # Verify cleanup behavior:
                        # - mcp-server1 (reused) should NOT be cleaned up
                        # - mcp-server2 (not reused) SHOULD be cleaned up
                        assert "mcp-server1" not in cleanup_calls, \
                            "Reused container should not be cleaned up"
                        assert "mcp-server2" in cleanup_calls, \
                            "Non-reused container should be cleaned up"

    @pytest.mark.asyncio
    async def test_healthy_container_selection(self):
        """Test that healthy containers are used instead of creating new ones."""
        from mcp_anywhere.core.mcp_manager import create_mcp_config
        
        # Create a mock server
        server = MagicMock(spec=MCPServer)
        server.id = "test123"
        server.name = "test-server"
        server.runtime_type = "uvx"
        server.start_command = "uvx test-server"
        server.install_command = ""
        server.env_variables = []
        server.secret_files = []
        
        # Mock container manager
        with patch('mcp_anywhere.core.mcp_manager.ContainerManager') as MockContainerManager:
            mock_manager = MagicMock()
            MockContainerManager.return_value = mock_manager
            
            # Simulate healthy container
            mock_manager._is_container_healthy.return_value = True
            mock_manager._parse_start_command.return_value = ["uvx", "test-server"]
            mock_manager._get_container_name.return_value = "mcp-test123"
            mock_manager.get_image_tag.return_value = "mcp-anywhere/server-test123"
            mock_manager._get_env_vars.return_value = {}
            
            # Get configuration
            config = create_mcp_config(server)
            
            # When container is healthy, should use "existing" config with docker exec
            assert "existing" in config
            assert config["existing"]["command"] == "docker"
            assert "exec" in config["existing"]["args"]
            assert "mcp-test123" in config["existing"]["args"]

    @pytest.mark.asyncio
    async def test_unhealthy_container_selection(self):
        """Test that unhealthy containers trigger new container creation."""
        from mcp_anywhere.core.mcp_manager import create_mcp_config
        
        # Create a mock server
        server = MagicMock(spec=MCPServer)
        server.id = "test123"
        server.name = "test-server"
        server.runtime_type = "uvx"
        server.start_command = "uvx test-server"
        server.install_command = ""
        server.env_variables = []
        server.secret_files = []
        
        # Mock container manager
        with patch('mcp_anywhere.core.mcp_manager.ContainerManager') as MockContainerManager:
            mock_manager = MagicMock()
            MockContainerManager.return_value = mock_manager
            
            # Simulate unhealthy container (not running or wrong image)
            mock_manager._is_container_healthy.return_value = False
            mock_manager._parse_start_command.return_value = ["uvx", "test-server"]
            mock_manager._get_container_name.return_value = "mcp-test123"
            mock_manager.get_image_tag.return_value = "mcp-anywhere/server-test123"
            mock_manager._get_env_vars.return_value = {}
            
            # Mock SecureFileManager
            with patch('mcp_anywhere.core.mcp_manager.SecureFileManager'):
                # Get configuration
                config = create_mcp_config(server)
                
                # When container is unhealthy, should use "new" config with docker run
                assert "new" in config
                assert config["new"]["command"] == "docker"
                assert "run" in config["new"]["args"]
                assert "mcp-test123" in config["new"]["args"]
