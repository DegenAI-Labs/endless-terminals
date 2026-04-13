# test_final_state.py
import os
import pytest

def test_ssh_directory_exists_and_permissions():
    assert os.path.exists("/home/user/.ssh"), "The .ssh directory does not exist."
    stat = os.stat("/home/user/.ssh")
    assert stat.st_mode & 0o777 == 0o700, f"The .ssh directory has incorrect permissions: {oct(stat.st_mode & 0o777)}"

def test_private_key_exists_and_permissions():
    assert os.path.exists("/home/user/.ssh/id_rsa_exp"), "The private key file does not exist."
    stat = os.stat("/home/user/.ssh/id_rsa_exp")
    assert stat.st_mode & 0o777 == 0o600, f"The private key has incorrect permissions: {oct(stat.st_mode & 0o777)}"

def test_public_key_exists_and_permissions():
    assert os.path.exists("/home/user/.ssh/id_rsa_exp.pub"), "The public key file does not exist."
    stat = os.stat("/home/user/.ssh/id_rsa_exp.pub")
    assert stat.st_mode & 0o777 == 0o644, f"The public key has incorrect permissions: {oct(stat.st_mode & 0o777)}"

def test_public_key_format():
    public_key_path = "/home/user/.ssh/id_rsa_exp.pub"
    with open(public_key_path, 'r') as f:
        content = f.read().strip()
    assert content.startswith("ssh-rsa"), "Public key does not start with 'ssh-rsa'"
    parts = content.split()
    assert len(parts) == 3, "Public key has incorrect number of parts"

def test_remote_authorized_keys_contains_public_key():
    remote_authorized_keys_path = "/home/mluser/.ssh/authorized_keys"
    assert os.path.exists(remote_authorized_keys_path), "The remote authorized_keys file does not exist."
    with open("/home/user/.ssh/id_rsa_exp.pub", 'r') as f:
        public_key_line = f.read().strip()
    with open(remote_authorized_keys_path, 'r') as f:
        authorized_keys_content = f.read()
    assert public_key_line in authorized_keys_content, "The public key is not present in the remote authorized_keys file."