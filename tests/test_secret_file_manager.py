"""Tests for SecureFileManager secret-file mounting behaviour."""

import shutil
from types import SimpleNamespace

import pytest

from mcp_anywhere.security.file_manager import SecureFileManager


def _make_secret(stored_filename: str, original_filename: str = "creds.json"):
    return SimpleNamespace(
        is_active=True,
        stored_filename=stored_filename,
        original_filename=original_filename,
        env_var_name="GOOGLE_CREDENTIALS_PATH",
    )


def test_prepare_container_files_raises_when_stored_file_missing(tmp_path):
    """If the DB row is active but the encrypted file is gone, fail loudly."""
    fm = SecureFileManager(storage_path=tmp_path)
    server_id = "abc12345"

    # Force-create the server dir without writing any encrypted file.
    fm._get_server_secrets_dir(server_id)
    secret = _make_secret(stored_filename="missing.json")

    with pytest.raises(FileNotFoundError):
        fm.prepare_container_files(server_id, [secret])


def test_prepare_container_files_writes_regular_file(tmp_path):
    fm = SecureFileManager(storage_path=tmp_path)
    server_id = "abc12345"
    stored = fm.store_file(server_id, "creds.json", b'{"hello": "world"}')

    secret = _make_secret(stored_filename=stored)
    mounts = fm.prepare_container_files(server_id, [secret])

    assert len(mounts) == 1
    [host_path] = mounts.keys()
    assert mounts[host_path] == "/secrets/creds.json"

    from pathlib import Path
    assert Path(host_path).is_file()


def test_prepare_container_files_replaces_stale_dir_at_temp_path(tmp_path):
    """If a directory was left behind at temp_path, replace it with the file."""
    fm = SecureFileManager(storage_path=tmp_path)
    server_id = "abc12345"
    stored = fm.store_file(server_id, "creds.json", b'{"hello": "world"}')

    server_dir = fm._get_server_secrets_dir(server_id)
    stale_dir = server_dir / f"temp_{stored}"
    stale_dir.mkdir()
    assert stale_dir.is_dir()

    secret = _make_secret(stored_filename=stored)
    mounts = fm.prepare_container_files(server_id, [secret])

    [host_path] = mounts.keys()
    from pathlib import Path
    assert Path(host_path).is_file()

    shutil.rmtree(server_dir)


def test_prepare_container_files_skips_inactive(tmp_path):
    fm = SecureFileManager(storage_path=tmp_path)
    server_id = "abc12345"
    stored = fm.store_file(server_id, "creds.json", b'{"hello": "world"}')

    secret = _make_secret(stored_filename=stored)
    secret.is_active = False

    mounts = fm.prepare_container_files(server_id, [secret])
    assert mounts == {}
