"""Valida el certificado público local antes de autorizar su confianza en Windows."""
import sys
from datetime import datetime, timezone
from ipaddress import ip_address

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID


def validate_local_certificate(pem: bytes) -> None:
    cert = x509.load_pem_x509_certificate(pem)
    now = datetime.now(timezone.utc)
    if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
        raise ValueError("El certificado local no está vigente.")
    if cert.issuer != cert.subject:
        raise ValueError("Se esperaba un certificado local autofirmado.")
    key = cert.public_key()
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048:
        raise ValueError("La clave pública local no cumple el tamaño esperado.")
    key.verify(cert.signature, cert.tbs_certificate_bytes, padding.PKCS1v15(), cert.signature_hash_algorithm)
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if set(san) != {x509.DNSName("localhost"), x509.IPAddress(ip_address("127.0.0.1"))}:
        raise ValueError("El certificado debe limitarse a localhost y 127.0.0.1.")
    # Las instalaciones anteriores omiten estas extensiones; si existen, se restringen.
    try:
        if cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError("No se admite un certificado de autoridad certificadora.")
    except x509.ExtensionNotFound:
        pass
    try:
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if set(eku) != {ExtendedKeyUsageOID.SERVER_AUTH}:
            raise ValueError("El certificado debe ser de servidor HTTPS.")
    except x509.ExtensionNotFound:
        pass


if __name__ == "__main__":
    validate_local_certificate(sys.stdin.buffer.read())
    print("Certificado local válido: firma, vigencia, SAN y clave pública.")
