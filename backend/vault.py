import base64
import binascii
import hmac
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class Vault:
    def __init__(self, encoded_key):
        try:
            key = base64.b64decode(encoded_key, altchars=b"-_", validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("DATA_KEY debe codificar 32 bytes en Base64 URL-safe") from error
        if len(key) != 32:
            raise ValueError("DATA_KEY debe codificar 32 bytes en Base64 URL-safe")
        self.cipher = AESGCM(key)
        self.digest_key = hmac.digest(key, b'vayxer/request-fingerprint/v1', 'sha256')

    def fingerprint(self, digest):
        return 'v1.' + hmac.digest(self.digest_key, digest.encode(), 'sha256').hex()

    def seal(self, value, context):
        nonce = os.urandom(12)
        data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
        sealed = self.cipher.encrypt(nonce, data, context.encode())
        return "v1." + base64.urlsafe_b64encode(nonce + sealed).decode()

    def open(self, envelope, context):
        if not envelope.startswith("v1."):
            raise ValueError("Versión de cifrado desconocida")
        data = base64.b64decode(envelope[3:], altchars=b"-_", validate=True)
        return json.loads(self.cipher.decrypt(data[:12], data[12:], context.encode()))
