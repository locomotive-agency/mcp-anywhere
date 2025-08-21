"""Secure file manager for handling secret files."""

import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from cryptography.fernet import Fernet

from mcp_anywhere.config import Config
from mcp_anywhere.logging_config import get_logger

logger = get_logger(__name__)


class SecureFileManager:
    """Manages secure storage and retrieval of secret files."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize the secure file manager."""
        self.storage_path = storage_path or Path("/app/secrets")
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
        # Allowed file extensions for security
        self.allowed_extensions = {
            '.json', '.pem', '.p12', '.pfx', '.key', '.crt', '.cert', 
            '.txt', '.yaml', '.yml', '.xml', '.jks', '.keystore'
        }
        
        # Maximum file size (10MB)
        self.max_file_size = 10 * 1024 * 1024

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for file encryption."""
        key_file = self.storage_path / ".encryption_key"
        
        # Create secrets directory if it doesn't exist
        key_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            logger.info("Generated new encryption key for secret files")
            return key

    def _get_server_secrets_dir(self, server_id: str) -> Path:
        """Get the secrets directory for a specific server."""
        server_dir = self.storage_path / server_id
        server_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        return server_dir

    def validate_file(self, filename: str, file_size: int) -> tuple[bool, str]:
        """Validate uploaded file."""
        # Check file size
        if file_size > self.max_file_size:
            return False, f"File size ({file_size} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)"
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            allowed = ', '.join(sorted(self.allowed_extensions))
            return False, f"File extension '{file_ext}' not allowed. Allowed extensions: {allowed}"
        
        # Check filename for security
        if '..' in filename or '/' in filename or '\\' in filename:
            return False, "Invalid filename: path traversal characters not allowed"
        
        return True, ""

    def store_file(self, server_id: str, original_filename: str, file_content: bytes) -> str:
        """Store a secret file securely."""
        # Generate unique filename
        file_ext = Path(original_filename).suffix.lower()
        stored_filename = f"{uuid.uuid4().hex}{file_ext}"
        
        # Get server directory
        server_dir = self._get_server_secrets_dir(server_id)
        file_path = server_dir / stored_filename
        
        # Encrypt and store file
        encrypted_content = self.cipher.encrypt(file_content)
        
        with open(file_path, 'wb') as f:
            f.write(encrypted_content)
        
        # Set restrictive permissions
        os.chmod(file_path, 0o600)
        
        logger.info(f"Stored secret file for server {server_id}: {original_filename} -> {stored_filename}")
        return stored_filename

    def retrieve_file(self, server_id: str, stored_filename: str) -> bytes:
        """Retrieve and decrypt a secret file."""
        server_dir = self._get_server_secrets_dir(server_id)
        file_path = server_dir / stored_filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Secret file not found: {stored_filename}")
        
        with open(file_path, 'rb') as f:
            encrypted_content = f.read()
        
        # Decrypt content
        decrypted_content = self.cipher.decrypt(encrypted_content)
        return decrypted_content

    def delete_file(self, server_id: str, stored_filename: str) -> bool:
        """Delete a secret file."""
        server_dir = self._get_server_secrets_dir(server_id)
        file_path = server_dir / stored_filename
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted secret file for server {server_id}: {stored_filename}")
            return True
        return False

    def cleanup_server_files(self, server_id: str) -> None:
        """Clean up all secret files for a server."""
        server_dir = self._get_server_secrets_dir(server_id)
        
        if server_dir.exists():
            shutil.rmtree(server_dir)
            logger.info(f"Cleaned up all secret files for server {server_id}")

    def get_container_file_path(self, original_filename: str) -> str:
        """Get the path where the file will be accessible in the container."""
        return f"/secrets/{original_filename}"

    def prepare_container_files(self, server_id: str, secret_files: list) -> dict[str, str]:
        """Prepare secret files for container mounting."""
        server_dir = self._get_server_secrets_dir(server_id)
        container_files = {}
        
        for secret_file in secret_files:
            if not secret_file.is_active:
                continue
                
            stored_path = server_dir / secret_file.stored_filename
            if stored_path.exists():
                # Decrypt file to a temporary location for container mounting
                decrypted_content = self.retrieve_file(server_id, secret_file.stored_filename)
                
                # Create a temporary unencrypted file for container mounting
                temp_filename = f"temp_{secret_file.stored_filename}"
                temp_path = server_dir / temp_filename
                
                with open(temp_path, 'wb') as f:
                    f.write(decrypted_content)
                
                os.chmod(temp_path, 0o600)
                
                # Map to container path
                container_path = self.get_container_file_path(secret_file.original_filename)
                container_files[str(temp_path)] = container_path
        
        return container_files