import base64
from pathlib import Path
import sys
import unittest

from cryptography.exceptions import InvalidTag

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from vault import Vault


def vault(byte):
    return Vault(base64.urlsafe_b64encode(bytes([byte]) * 32).decode())


class VaultTest(unittest.TestCase):
    def test_round_trip_and_distinct_nonces(self):
        cipher = vault(1)
        fields = {"customer": "Café", "item": "Envío"}
        first = cipher.seal(fields, "order:one")
        self.assertEqual(cipher.open(first, "order:one"), fields)
        self.assertNotEqual(first, cipher.seal(fields, "order:one"))

    def test_rejects_different_key_or_context(self):
        cipher = vault(1)
        payload = cipher.seal({"customer": "Café"}, "order:one")
        with self.assertRaises(InvalidTag):
            vault(2).open(payload, "order:one")
        with self.assertRaises(InvalidTag):
            cipher.open(payload, "order:two")

    def test_rejects_modified_ciphertext(self):
        cipher = vault(1)
        envelope = cipher.seal({"customer": "Café"}, "order:one")
        binary = bytearray(base64.urlsafe_b64decode(envelope[3:]))
        binary[-1] ^= 1
        with self.assertRaises(InvalidTag):
            cipher.open("v1." + base64.urlsafe_b64encode(binary).decode(), "order:one")
