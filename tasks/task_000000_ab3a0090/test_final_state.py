# test_final_state.py
import os
import stat
import pytest

def test_local_access_log_exists_and_permissions():
    path = "/home/user/logs/access.log"
    assert os.path.exists(path), f"Local access log file {path} does not exist."
    mode = os.stat(path).st_mode
    expected_perms = 0o644
    actual_perms = mode & 0o777
    assert actual_perms == expected_perms, (
        f"Permissions for {path} are incorrect. Expected {oct(expected_perms)}, got {oct(actual_perms)}"
    )

def test_sync_verification_file_content():
    path = "/home/user/logs/sync_verified.log"
    assert os.path.exists(path), f"Sync verification file {path} does not exist."
    with open(path, 'r') as f:
        lines = [line.strip() for line in f.readlines()]
    expected = [
        "Remote file timestamp: 2023-10-01 12:35:20",
        "Local file timestamp: 2023-10-01 12:35:20",
        "Synchronization status: SUCCESS"
    ]
    assert lines == expected, (
        f"Sync verification content is incorrect. Expected {expected}, got {lines}"
    )

def test_404_ip_report_exists_and_permissions():
    path = "/home/user/analysis/404_ip_report.txt"
    assert os.path.exists(path), f"404 IP report file {path} does not exist."
    mode = os.stat(path).st_mode
    expected_perms = 0o644
    actual_perms = mode & 0o777
    assert actual_perms == expected_perms, (
        f"Permissions for {path} are incorrect. Expected {oct(expected_perms)}, got {oct(actual_perms)}"
    )

def test_404_ip_report_content():
    path = "/home/user/analysis/404_ip_report.txt"
    with open(path, 'r') as f:
        lines = [line.strip() for line in f.readlines()]
    expected = [
        "123.45.67.89: 2",
        "98.76.54.32: 2",
        "111.222.333.444: 1"
    ]
    assert lines == expected, (
        f"404 IP report content is incorrect. Expected {expected}, got {lines}"
    )