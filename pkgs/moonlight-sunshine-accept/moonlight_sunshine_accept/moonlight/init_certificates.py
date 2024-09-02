import argparse
import datetime
from datetime import timedelta
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
            x509.NameAttribute(NameOID.COMMON_NAME, "NVIDIA GameStream Client"),
        ]
    )
    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(tz=datetime.UTC))
        .not_valid_after(
            datetime.datetime.now(tz=datetime.UTC) + timedelta(days=365 * 20)
        )
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
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        # format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem_private_key


def init_credentials() -> tuple[bytes, bytes]:
    private_key = generate_private_key()
    certificate = generate_certificate(private_key)
    private_key_pem = private_key_to_pem(private_key)
    return certificate, private_key_pem


def write_credentials(_args: argparse.Namespace) -> None:
    pem_certificate, pem_private_key = init_credentials()
    credentials_path = Path.cwd() / "credentials"
    Path(credentials_path).mkdir(parents=True, exist_ok=True)

    (credentials_path / "cacert.pem").write_bytes(pem_certificate)
    (credentials_path / "cakey.pem").write_bytes(pem_private_key)
    print("Finished writing moonlight credentials")


def register_initialization_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=write_credentials)
