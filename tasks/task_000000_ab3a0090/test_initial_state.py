# test_initial_state.py
import os
import stat
import shutil
import pytest

def test_logs_directory_exists():
    path = "/home/user/logs"
    assert os.path.isdir(path), f"Directory {path} does not exist"

def test_access_log_not_present():
    path = "/home/user/logs/access.log"
    assert not os.path.exists(path), f"File {path} already exists. It should be synchronized from the remote server."

def test_analysis_directory_exists_with_permissions():
    path = "/home/user/analysis"
    assert os.path.isdir(path), f"Analysis directory {path} does not exist"
    mode = os.stat(path).st_mode
    assert (mode & 0o777) == 0o755, f"Analysis directory {path} has incorrect permissions. Expected 755, got {oct(mode & 0o777)}"

def test_report_file_not_present():
    path = "/home/user/analysis/404_ip_report.txt"
    assert not os.path.exists(path), f"Report file {path} already exists. It should be generated as part of the task."

def test_sync_check_file_not_present():
    path = "/home/user/logs/sync_verified.log"
    assert not os.path.exists(path), f"Sync check file {path} already exists. It should be created after synchronization."

def test_required_commands_installed():
    commands = ["scp", "ssh", "grep", "awk", "sort", "uniq", "head"]
    for cmd in commands:
        assert shutil.which(cmd) is not None, f"Required command '{cmd}' is not available in PATH"