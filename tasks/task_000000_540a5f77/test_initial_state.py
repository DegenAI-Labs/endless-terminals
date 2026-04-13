# test_initial_state.py
import pytest
from pathlib import Path

def test_local_database_exists():
    db_path = Path("/home/user/iotsensors.db")
    assert db_path.exists(), f"Local SQLite database file {db_path} is missing"
    assert db_path.is_file(), f"{db_path} is not a regular file"

def test_simulated_remote_directory_exists():
    remote_dir = Path("/home/user/_sim_remote")
    assert remote_dir.exists(), f"Simulated remote directory {remote_dir} does not exist"
    assert remote_dir.is_dir(), f"{remote_dir} is not a directory"

def test_backup_sql_not_present():
    backup_path = Path("/home/user/_sim_remote/backup.sql")
    assert not backup_path.exists(), f"backup.sql already exists in remote directory before task execution"

def test_transfer_complete_not_present():
    transfer_path = Path("/home/user/_sim_remote/transfer_complete.txt")
    assert not transfer_path.exists(), f"transfer_complete.txt already exists in remote directory before task execution"