# test_initial_state.py
import os
from pathlib import Path
import pytest

def test_initial_state():
    """Verify the initial filesystem state before student interaction."""
    base_dir = Path("/home/user/backup-test")

    # Verify base directory exists
    assert base_dir.exists(), f"Missing source directory: {base_dir}"
    assert base_dir.is_dir(), f"Path is not a directory: {base_dir}"

    # Verify all required files exist with correct content
    required_files = {
        "file1.txt": "Sample data file 1",
        "file2.txt": "Sample data file 2",
        "backup.log": "Backup operation log"
    }

    for filename, expected_content in required_files.items():
        file_path = base_dir / filename
        assert file_path.exists(), f"Missing source file: {file_path}"
        assert file_path.is_file(), f"Path is not a file: {file_path}"

        with open(file_path, 'r') as f:
            content = f.read().strip()
            assert content == expected_content, (
                f"Unexpected content in {file_path}. "
                f"Expected: '{expected_content}' Got: '{content}'"
            )