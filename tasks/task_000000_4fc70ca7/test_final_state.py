# test_final_state.py
import os
import re
import subprocess
import pytest

def test_remote_directory_contents():
    """Verify the remote server's directory contains the correct files with expected content."""
    remote_host = "backup-server.example.com"
    remote_dir = "/backup/restore-test"
    expected_files = {
        "file1.txt": "Sample data file 1",
        "file2.txt": "Sample data file 2",
        "backup.log": "Backup operation log"
    }

    # Check remote directory exists and contains all files
    ls_cmd = ["ssh", remote_host, f"ls -1 {remote_dir}"]
    result = subprocess.run(ls_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Failed to list remote directory: {result.stderr}"
    remote_files = result.stdout.strip().split('\n')

    for filename in expected_files:
        assert filename in remote_files, (
            f"Missing file on remote server: {remote_dir}/{filename}. "
            f"Found files: {', '.join(remote_files)}"
        )

    # Verify content of each file on the remote server
    for filename, expected_content in expected_files.items():
        cat_cmd = ["ssh", remote_host, f"cat {remote_dir}/{filename}"]
        result = subprocess.run(cat_cmd, capture_output=True, text=True)
        assert result.returncode == 0, f"Failed to read {filename} on remote: {result.stderr}"
        content = result.stdout.strip()
        assert content == expected_content, (
            f"Unexpected content in {filename} on remote server. "
            f"Expected: '{expected_content}' Got: '{content}'"
        )

def test_log_file_contents():
    """Verify the log file contains the exact required entries in the correct order."""
    log_path = "/home/user/backup_sync.log"
    assert os.path.exists(log_path), f"Log file not found: {log_path}"
    assert os.path.isfile(log_path), f"Log path is not a file: {log_path}"

    with open(log_path, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 2, (
            f"Log file must contain exactly 2 entries. "
            f"Found: {len(lines)} lines"
        )

        # Validate first log entry (rsync success)
        line1 = lines[0].strip()
        assert re.match(
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - rsync executed successfully: 3 files synced",
            line1
        ), f"Invalid first log entry: {line1}"

        # Validate second log entry (remote verification)
        line2 = lines[1].strip()
        assert re.match(
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - Remote verification: file1.txt, file2.txt, backup.log",
            line2
        ), f"Invalid second log entry: {line2}"