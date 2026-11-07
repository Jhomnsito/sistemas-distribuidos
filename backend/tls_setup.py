"""Creates a loopback-only certificate for the Windows first-run guide."""
import os
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from ipaddress import ip_address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

root = Path("/tls")
key_file, cert_file = root / "key.pem", root / "cert.pem"
if key_file.exists() or cert_file.exists():
    raise SystemExit("Los archivos HTTPS existentes se conservan.")
key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Vayxer local")])
now = datetime.now(timezone.utc)
cert = (
    x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now - timedelta(minutes=2)).not_valid_after(now + timedelta(days=30))
    .add_extension(x509.SubjectAlternativeName(
        [x509.DNSName("localhost"), x509.IPAddress(ip_address("127.0.0.1"))]), critical=False)
    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
    .sign(key, hashes.SHA256())
)
private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
with os.fdopen(os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
    output.write(private)
public = cert.public_bytes(serialization.Encoding.PEM)
with cert_file.open("xb") as output:
    output.write(public)
(root / "vayxer-local.sha256").write_text(sha256(public).hexdigest(), encoding="ascii")
