# test_initial_state.py
import os
import pytest

def test_ssh_directory_does_not_exist():
    assert not os.path.exists("/home/user/.ssh"), "The .ssh directory already exists. It should be created by the task."

def test_private_key_does_not_exist():
    assert not os.path.exists("/home/user/.ssh/id_rsa_exp"), "The private key file already exists."

def test_public_key_does_not_exist():
    assert not os.path.exists("/home/user/.ssh/id_rsa_exp.pub"), "The public key file already exists."