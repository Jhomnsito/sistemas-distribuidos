import sys
import unittest
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from tls_verify import validate_local_certificate


class LocalCertificateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def certificate(self, *, extra_host=False, expired=False, ca=False, wrong_signer=False):
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        now = datetime.now(timezone.utc)
        sans = [x509.DNSName("localhost"), x509.IPAddress(ip_address("127.0.0.1"))]
        if extra_host:
            sans.append(x509.DNSName("example.com"))
        builder = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                   .public_key(self.key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(days=2))
                   .not_valid_after(now + timedelta(days=-1 if expired else 1))
                   .add_extension(x509.SubjectAlternativeName(sans), critical=False)
                   .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True))
        signer = rsa.generate_private_key(public_exponent=65537, key_size=2048) if wrong_signer else self.key
        return builder.sign(signer, hashes.SHA256()).public_bytes(serialization.Encoding.PEM)

    def test_accepts_loopback_certificate(self):
        validate_local_certificate(self.certificate())

    def test_rejects_other_hosts(self):
        with self.assertRaises(ValueError):
            validate_local_certificate(self.certificate(extra_host=True))

    def test_rejects_expired_certificate(self):
        with self.assertRaises(ValueError):
            validate_local_certificate(self.certificate(expired=True))

    def test_rejects_ca_certificate(self):
        with self.assertRaises(ValueError):
            validate_local_certificate(self.certificate(ca=True))

    def test_rejects_wrong_signature(self):
        with self.assertRaises(InvalidSignature):
            validate_local_certificate(self.certificate(wrong_signer=True))


if __name__ == "__main__":
    unittest.main()
