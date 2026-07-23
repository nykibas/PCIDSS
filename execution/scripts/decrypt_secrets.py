import os
import sys
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def get_cipher():
    vault_pass_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.vault_pass')
    with open(vault_pass_path, 'rb') as f:
        password = f.read().strip()
    salt = b"solidaire_salt_12345"
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return Fernet(key)

if __name__ == '__main__':
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.secrets.env.enc')
    if os.path.exists(secrets_path):
        f = get_cipher()
        with open(secrets_path, 'rb') as file:
            encrypted = file.read()
        print(f.decrypt(encrypted).decode('utf-8'))
