import argparse
import datetime
import uuid
from pathlib import Path

from cryptography import hazmat, x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate_private_key() -> rsa.RSAPrivateKey:
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=hazmat.backends.default_backend()
    )
    return private_key


def generate_certificate(private_key: rsa.RSAPrivateKey) -> bytes:
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Sunshine Gamestream Host"),
        ]
    )
    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(61093384576940497812448570031200738505731293357)
        .not_valid_before(datetime.datetime(2024, 2, 27, tzinfo=datetime.UTC))
        .not_valid_after(datetime.datetime(2044, 2, 22, tzinfo=datetime.UTC))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    pem_certificate = cert_builder.public_bytes(serialization.Encoding.PEM)
    return pem_certificate


def private_key_to_pem(private_key: rsa.RSAPrivateKey) -> bytes:
    pem_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem_private_key


def init_credentials() -> tuple[bytes, bytes]:
    private_key = generate_private_key()
    certificate = generate_certificate(private_key)
    private_key_pem = private_key_to_pem(private_key)
    return certificate, private_key_pem


def uniqueid() -> str:
    return str(uuid.uuid4()).upper()


def write_credentials(_args: argparse.Namespace) -> None:
    print("Writing sunshine credentials")
    pem_certificate, pem_private_key = init_credentials()
    credentials_dir = Path("credentials")
    credentials_dir.mkdir(parents=True, exist_ok=True)
    (credentials_dir / "cacert.pem").write_bytes(pem_certificate)
    (credentials_dir / "cakey.pem").write_bytes(pem_private_key)
    print("Generating sunshine UUID")
    Path("uuid").write_text(uniqueid())


def register_initialization_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=write_credentials)
