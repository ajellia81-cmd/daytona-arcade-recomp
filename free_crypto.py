"""Authenticated envelopes for public CI inputs and outputs; never print keys."""
from pathlib import Path
import base64
import io
import os
import sys
import zipfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIX = b'DAYTONA-AESGCM-1\n'

def key():
    value = base64.b64decode(os.environ['DAYTONA_BUILD_KEY'], validate=True)
    assert len(value) == 32
    return value

def encrypt(data, purpose):
    nonce = os.urandom(12)
    return PREFIX + nonce + AESGCM(key()).encrypt(nonce, data, purpose)

def decrypt(data, purpose):
    assert data.startswith(PREFIX), 'Wrong envelope format'
    at = len(PREFIX)
    return AESGCM(key()).decrypt(data[at:at+12], data[at+12:], purpose)

if __name__ == '__main__':
    if sys.argv[1] == 'input':
        data = decrypt(Path('private-input.enc').read_bytes(), b'daytona-private-input-v1')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert set(archive.namelist()) == {'daytona.zip', 'daytona-official-art-icon-white-1024.png'}
            archive.extractall('private-input')
        print('Authenticated private input decrypted in ephemeral runner storage')
    elif sys.argv[1] == 'output':
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for folder in ('private-package',):
                for path in Path(folder).rglob('*'):
                    if path.is_file(): archive.write(path, path.relative_to(folder))
        Path(sys.argv[2]).write_bytes(encrypt(stream.getvalue(), b'daytona-private-output-v1'))
        print('Build outputs/logs authenticated and encrypted; no plaintext artifacts uploaded')
