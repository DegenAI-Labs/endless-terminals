# test_initial_state.py
import os
import pytest

def test_nginx_config_file_exists():
    config_path = "/home/user/services/nginx.conf"
    assert os.path.exists(config_path), (
        f"Missing Nginx configuration file at {config_path}. "
        "Ensure the configuration file exists before proceeding."
    )

def test_logs_directory_exists_and_writable():
    logs_dir = "/home/user/logs"
    assert os.path.isdir(logs_dir), (
        f"Logs directory {logs_dir} does not exist. "
        "Create the directory before proceeding."
    )
    assert os.access(logs_dir, os.W_OK), (
        f"Logs directory {logs_dir} is not writable by the user. "
        "Adjust permissions to allow write access."
    )