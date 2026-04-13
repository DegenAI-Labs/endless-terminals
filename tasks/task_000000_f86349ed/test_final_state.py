# test_final_state.py
import os
import socket
import urllib.request
import pytest

def test_nginx_config_log_format():
    config_path = "/home/user/services/nginx.conf"
    expected_log_format = "log_format combined '$remote_addr - $remote_user [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"';"

    with open(config_path, 'r') as f:
        config_lines = f.readlines()

    log_format_found = any(expected_log_format in line for line in config_lines)
    assert log_format_found, (
        f"Missing correct `log_format` directive in {config_path}. "
        f"Expected: {expected_log_format}"
    )

def test_nginx_config_access_log():
    config_path = "/home/user/services/nginx.conf"
    expected_access_log = "/home/user/logs/nginx-access.log combined;"

    with open(config_path, 'r') as f:
        config_lines = f.readlines()

    access_log_found = any(expected_access_log in line for line in config_lines)
    assert access_log_found, (
        f"Missing correct `access_log` directive in {config_path}. "
        f"Expected path: {expected_access_log}"
    )

def test_log_file_content():
    log_path = "/home/user/logs/nginx-access.log"
    expected_line = '192.0.2.1 - - [10/Oct/2023:13:55:36 +0000] "GET /health HTTP/1.1" 200 612 "-" "curl/7.81.0"'

    assert os.path.exists(log_path), f"Log file {log_path} does not exist."
    with open(log_path, 'r') as f:
        lines = f.readlines()

    assert len(lines) == 1, f"Log file {log_path} contains {len(lines)} lines. Expected exactly one line."
    assert lines[0].strip() == expected_line, (
        f"Log file content mismatch. Expected: {expected_line}, Got: {lines[0].strip()}"
    )

def test_nginx_listening_on_port_8080():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8080))
    assert result == 0, "Nginx is not listening on port 8080. Ensure the service is running and configured correctly."
    sock.close()

def test_health_check_returns_200():
    url = "http://localhost:8080/health"
    try:
        with urllib.request.urlopen(url) as response:
            status_line = response.status_line if hasattr(response, 'status_line') else f"HTTP/1.1 {response.status} {response.reason}"
            assert status_line == "HTTP/1.1 200 OK", (
                f"Health check failed. Expected 'HTTP/1.1 200 OK', got '{status_line}'"
            )
    except Exception as e:
        pytest.fail(f"Health check request failed: {e}")

def test_logs_directory_writable():
    logs_dir = "/home/user/logs"
    assert os.path.isdir(logs_dir), f"Logs directory {logs_dir} does not exist."
    assert os.access(logs_dir, os.W_OK), (
        f"Logs directory {logs_dir} is not writable. Required for log file updates."
    )