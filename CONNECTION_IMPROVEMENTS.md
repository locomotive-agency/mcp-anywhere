# Connection Stability Improvements

This document describes the improvements made to resolve MCP error -32000 "Connection closed" issues.

## Problem Description

Users were experiencing "MCP error -32000: Connection closed" with approximately 90% failure rate when calling tools through Claude web interface. The error appeared immediately when tools were invoked, while MCP Inspector worked fine.

## Root Causes Identified

1. **Silent Error Suppression**: Connection errors were being silently suppressed, making debugging impossible
2. **Container Health Check Failures**: Intermittent Docker API issues causing premature connection failures
3. **FastMCP Lifespan Management**: Inadequate timeout handling and error recovery in HTTP transport mode
4. **Missing Connection Timeouts**: No explicit timeouts on Docker operations leading to hanging connections

## Implemented Solutions

### 1. Enhanced Error Logging (`stdio_gateway.py`)

**Before:**
```python
except (RuntimeError, ValueError, OSError, ConnectionError):
    # Silent exit on any error to keep stdio clean
    sys.exit(1)
```

**After:**
```python
except (RuntimeError, ValueError, OSError, ConnectionError) as e:
    # Log error to help with debugging, but still exit cleanly
    try:
        with open(f"{tempfile.gettempdir()}/mcp_anywhere_error.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - STDIO Gateway Error: {type(e).__name__}: {e}\n")
    except Exception:
        pass
    sys.exit(1)
```

**Benefits:**
- Errors are now captured to `/tmp/mcp_anywhere_error.log` for debugging
- STDIO protocol remains clean (no stderr contamination)
- Administrators can diagnose connection issues

### 2. Resilient Container Health Checks (`container/manager.py`)

**Before:**
```python
def _is_container_healthy(self, server: MCPServer) -> bool:
    try:
        container = self.docker_client.containers.get(container_name)
        # Single attempt, immediate failure
```

**After:**
```python
def _is_container_healthy(self, server: MCPServer, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            container = self.docker_client.containers.get(container_name)
            container.reload()  # Get fresh status
            # ... retry logic with delays
```

**Benefits:**
- Handles transient Docker API errors with 3 retry attempts
- Refreshes container status for accurate health checks
- Includes backoff delays (0.5s, 1s) between retries
- More reliable container reuse decisions

### 3. Graceful Fallback for Unhealthy Containers (`stdio_gateway.py`)

**Before:**
```python
if container_manager._is_container_healthy(server):
    server_config_dict = config_options["existing"]
else:
    raise RuntimeError(f"Container {server.name} is not healthy")
```

**After:**
```python
if container_manager._is_container_healthy(server):
    server_config_dict = config_options["existing"]
else:
    # Try to use the new configuration instead of failing immediately
    server_config_dict = config_options["new"]
    if not server_config_dict:
        # Log and skip this server instead of crashing
        continue
```

**Benefits:**
- Automatic fallback to new container creation when existing containers fail
- Individual server failures don't crash the entire gateway
- Improved resilience in multi-server configurations

### 4. Robust FastMCP Lifespan Management (`web/mcp_mount.py`)

**Enhanced Startup:**
```python
async def _ensure_lifespan_started(self) -> None:
    startup_completed = asyncio.Event()
    startup_error = None
    
    # Wait for startup to complete or fail (with timeout)
    await asyncio.wait_for(startup_completed.wait(), timeout=30.0)
```

**Enhanced Shutdown:**
```python
async def shutdown(self) -> None:
    try:
        # Increased timeout from 5s to 10s
        await asyncio.wait_for(self.lifespan_task, timeout=10.0)
    except TimeoutError:
        # Proper cancellation handling
        self.lifespan_task.cancel()
```

**Enhanced Error Handling:**
```python
async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
    try:
        await self._ensure_lifespan_started()
    except Exception as e:
        # Send proper HTTP error responses instead of crashing
        if scope["type"] == "http":
            await send({"type": "http.response.start", "status": 500, ...})
```

**Benefits:**
- 30-second startup timeout prevents hanging initialization
- 10-second shutdown timeout (increased from 5s) for graceful cleanup
- HTTP error responses (500) instead of connection drops
- Proper error propagation and logging

### 5. Connection Timeout Configuration (`core/mcp_manager.py`)

**Added to both configurations:**
```python
existing_config = {
    "command": "docker",
    "args": [...],
    "transport": "stdio",
    "timeout": 300,  # 5 minute timeout for tool calls
}

new_config = {
    "command": "docker", 
    "args": [...],
    "transport": "stdio",
    "timeout": 300,  # 5 minute timeout for tool calls
}
```

**Benefits:**
- Prevents hanging Docker operations that cause "Connection closed" errors
- 5-minute timeout allows for long-running tool operations
- Consistent timeout behavior across container configurations

## Testing

### Unit Tests
- `test_connection_stability.py`: Validates error handling and lifespan management
- All existing transport tests continue to pass

### Integration Testing
- Manual verification shows improved error logging
- Container health checks now retry successfully
- STDIO gateway runs continuously without premature exits

## Expected Impact

These improvements should significantly reduce the "Connection closed" error rate by:

1. **Making connections more resilient** to transient Docker issues
2. **Providing better error visibility** for remaining issues  
3. **Preventing hanging operations** through explicit timeouts
4. **Enabling graceful degradation** when individual components fail

The combination of these changes addresses all identified root causes while maintaining backward compatibility and clean protocol handling.