"""Routes for handling secret file uploads and management."""

import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from mcp_anywhere.database import MCPServer, MCPServerSecretFile, get_async_session
from mcp_anywhere.logging_config import get_logger
from mcp_anywhere.security.file_manager import SecureFileManager

logger = get_logger(__name__)
templates = Jinja2Templates(directory="src/mcp_anywhere/web/templates")


class SecretFileUploadData(BaseModel):
    """Form data for secret file uploads."""
    
    env_var_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    
    @field_validator("env_var_name")
    @classmethod
    def validate_env_var_name(cls, v):
        """Validate environment variable name format."""
        if not re.match(r'^[A-Z][A-Z0-9_]*$', v):
            raise ValueError("Environment variable name must start with a letter and contain only uppercase letters, numbers, and underscores")
        return v


async def upload_secret_file(request: Request) -> Response:
    """Handle secret file upload for a server."""
    server_id = request.path_params["server_id"]
    
    try:
        # Get server
        async with get_async_session() as db_session:
            stmt = select(MCPServer).where(MCPServer.id == server_id)
            result = await db_session.execute(stmt)
            server = result.scalar_one_or_none()
            
            if not server:
                return JSONResponse(
                    {"error": f"Server '{server_id}' not found"}, 
                    status_code=404
                )
        
        # Parse form data
        form_data = await request.form()
        
        # Get uploaded file
        uploaded_file: UploadFile = form_data.get("secret_file")
        if not uploaded_file or not uploaded_file.filename:
            return JSONResponse(
                {"error": "No file uploaded"}, 
                status_code=400
            )
        
        # Read file content
        file_content = await uploaded_file.read()
        file_size = len(file_content)
        
        # Initialize file manager and validate file
        file_manager = SecureFileManager()
        is_valid, error_msg = file_manager.validate_file(uploaded_file.filename, file_size)
        
        if not is_valid:
            return JSONResponse(
                {"error": error_msg}, 
                status_code=400
            )
        
        # Validate form data
        try:
            upload_data = SecretFileUploadData(
                env_var_name=form_data.get("env_var_name", ""),
                description=form_data.get("description", "")
            )
        except ValidationError as e:
            return JSONResponse(
                {"error": f"Validation error: {e.errors()[0]['msg']}"}, 
                status_code=400
            )
        
        # Check for duplicate environment variable names
        async with get_async_session() as db_session:
            stmt = select(MCPServerSecretFile).where(
                MCPServerSecretFile.server_id == server_id,
                MCPServerSecretFile.env_var_name == upload_data.env_var_name,
                MCPServerSecretFile.is_active == True
            )
            result = await db_session.execute(stmt)
            existing_file = result.scalar_one_or_none()
            
            if existing_file:
                return JSONResponse(
                    {"error": f"Environment variable '{upload_data.env_var_name}' already exists for this server"}, 
                    status_code=400
                )
        
        # Store file securely
        stored_filename = file_manager.store_file(
            server_id, 
            uploaded_file.filename, 
            file_content
        )
        
        # Save to database
        async with get_async_session() as db_session:
            secret_file = MCPServerSecretFile(
                server_id=server_id,
                original_filename=uploaded_file.filename,
                stored_filename=stored_filename,
                file_type=uploaded_file.content_type or "application/octet-stream",
                file_size=file_size,
                env_var_name=upload_data.env_var_name,
                description=upload_data.description
            )
            
            db_session.add(secret_file)
            await db_session.commit()
        
        logger.info(f"Uploaded secret file for server {server_id}: {uploaded_file.filename}")
        
        # Return success response
        if request.headers.get("HX-Request"):
            # HTMX request - return partial HTML
            return RedirectResponse(
                url=f"/servers/{server_id}",
                status_code=303
            )
        else:
            # Regular request - return JSON
            return JSONResponse({
                "success": True,
                "message": f"Secret file '{uploaded_file.filename}' uploaded successfully",
                "file_id": secret_file.id
            })
    
    except Exception as e:
        logger.exception(f"Error uploading secret file for server {server_id}")
        return JSONResponse(
            {"error": f"Failed to upload file: {str(e)}"}, 
            status_code=500
        )


async def list_secret_files(request: Request) -> JSONResponse:
    """List secret files for a server."""
    server_id = request.path_params["server_id"]
    
    try:
        async with get_async_session() as db_session:
            # Get server with secret files
            stmt = (
                select(MCPServer)
                .options(selectinload(MCPServer.secret_files))
                .where(MCPServer.id == server_id)
            )
            result = await db_session.execute(stmt)
            server = result.scalar_one_or_none()
            
            if not server:
                return JSONResponse(
                    {"error": f"Server '{server_id}' not found"}, 
                    status_code=404
                )
            
            # Convert to dict
            secret_files = [
                secret_file.to_dict() 
                for secret_file in server.secret_files 
                if secret_file.is_active
            ]
            
            return JSONResponse({
                "server_id": server_id,
                "secret_files": secret_files
            })
    
    except Exception as e:
        logger.exception(f"Error listing secret files for server {server_id}")
        return JSONResponse(
            {"error": f"Failed to list files: {str(e)}"}, 
            status_code=500
        )


async def delete_secret_file(request: Request) -> Response:
    """Delete a secret file."""
    server_id = request.path_params["server_id"]
    file_id = request.path_params["file_id"]
    
    try:
        async with get_async_session() as db_session:
            # Get secret file
            stmt = select(MCPServerSecretFile).where(
                MCPServerSecretFile.id == file_id,
                MCPServerSecretFile.server_id == server_id
            )
            result = await db_session.execute(stmt)
            secret_file = result.scalar_one_or_none()
            
            if not secret_file:
                return JSONResponse(
                    {"error": f"Secret file '{file_id}' not found"}, 
                    status_code=404
                )
            
            # Delete file from storage
            file_manager = SecureFileManager()
            file_manager.delete_file(server_id, secret_file.stored_filename)
            
            # Mark as inactive in database
            secret_file.is_active = False
            await db_session.commit()
        
        logger.info(f"Deleted secret file {file_id} for server {server_id}")
        
        # Return success response
        if request.headers.get("HX-Request"):
            # HTMX request - return partial HTML
            return RedirectResponse(
                url=f"/servers/{server_id}",
                status_code=303
            )
        else:
            # Regular request - return JSON
            return JSONResponse({
                "success": True,
                "message": "Secret file deleted successfully"
            })
    
    except Exception as e:
        logger.exception(f"Error deleting secret file {file_id} for server {server_id}")
        return JSONResponse(
            {"error": f"Failed to delete file: {str(e)}"}, 
            status_code=500
        )


# Define routes for secret file management
secret_file_routes = [
    Route("/servers/{server_id}/secrets", upload_secret_file, methods=["POST"]),
    Route("/servers/{server_id}/secrets", list_secret_files, methods=["GET"]),
    Route("/servers/{server_id}/secrets/{file_id}", delete_secret_file, methods=["DELETE"]),
]