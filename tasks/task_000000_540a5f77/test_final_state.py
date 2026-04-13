# test_final_state.py
import pytest
from pathlib import Path

def test_backup_sql_exists():
    backup_path = Path("/home/user/_sim_remote/backup.sql")
    assert backup_path.exists(), f"Missing required backup file: {backup_path}"
    assert backup_path.is_file(), f"{backup_path} is not a regular file"

def test_backup_sql_size():
    backup_path = Path("/home/user/_sim_remote/backup.sql")
    assert backup_path.stat().st_size == 1354, (
        f"backup.sql has incorrect size {backup_path.stat().st_size} bytes "
        f"(expected 1354 bytes)"
    )

def test_backup_sql_content():
    expected_content = """-- SQLite schema dump
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE "sensor_data" ("timestamp" TEXT, "temperature" REAL, "humidity" REAL);
INSERT INTO "sensor_data" VALUES('2023-10-15 08:00:00',23.4,45.6);
INSERT INTO "sensor_data" VALUES('2023-10-15 08:15:00',24.1,46.3);
INSERT INTO "sensor_data" VALUES('2023-10-15 08:30:00',22.8,44.9);
COMMIT;
"""
    backup_path = Path("/home/user/_sim_remote/backup.sql")
    actual_content = backup_path.read_text()
    assert actual_content == expected_content, (
        f"backup.sql content does not match expected schema and data.\n"
        f"Found: {repr(actual_content)}\n"
        f"Expected: {repr(expected_content)}"
    )

def test_transfer_complete_file():
    transfer_path = Path("/home/user/_sim_remote/transfer_complete.txt")
    assert transfer_path.exists(), f"Missing transfer_complete.txt marker file"
    expected_text = "Database transfer completed at 2023-10-15T10:00:00Z"
    actual_text = transfer_path.read_text()
    assert actual_text == expected_text, (
        f"transfer_complete.txt has incorrect content.\n"
        f"Found: {actual_text}\n"
        f"Expected: {expected_text}"
    )