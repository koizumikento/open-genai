"""Check a built Python image's interpreter and independent CA stores, offline."""

import hashlib
import importlib.metadata
import importlib.util
import ssl
import sys
from pathlib import Path

from pip._vendor import certifi as pip_certifi
from pip._vendor.packaging.version import Version

# Exact affected roots, not all certificates with "emSign" in their names.
# https://emudhra.we-have-a-problem.com/roots.json
COMPROMISED_ROOTS = {
    "7dd78d5f4f13459a83dff9abbba62edbaf6f2d102bf257fd712f4d9f2746ed8d",
    "f2edaaff3d9b701fb4d14c9f285f8c0bad90fc3bcc1fa07d47f4718edaba34a5",
    "d7a7a0fb5d7e2731d771e9484ebcdef71d5f0c3e0a2948782bc83ee0ea699ef4",
    "86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b",
}


def check_store(name: str, cafile: str | None = None) -> None:
    certificates = ssl.create_default_context(cafile=cafile).get_ca_certs(binary_form=True)
    assert certificates, f"{name}: empty CA store"
    compromised = [
        hashlib.sha256(certificate).hexdigest()
        for certificate in certificates
        if hashlib.sha256(certificate).hexdigest() in COMPROMISED_ROOTS
    ]
    assert not compromised, f"{name}: affected roots remain: {compromised}"
    print(f"{name}: {len(certificates)} trusted CAs; no affected root fingerprints")


assert sys.version_info >= (3, 12, 15), sys.version
print(f"Python: {sys.version.split()[0]}")
pip_version = importlib.metadata.version("pip")
assert Version(pip_version) >= Version("26.2.2"), pip_version
assert Version(pip_certifi.__version__) >= Version("2026.10.19")
print(f"pip: {pip_version}; vendored certifi: {pip_certifi.__version__}")
check_store("OS/OpenSSL")
check_store("pip certifi", pip_certifi.where())

requirements = Path("/app/requirements.txt").read_text()
if any(line.startswith(("httpx==", "requests==")) for line in requirements.splitlines()):
    import certifi

    assert Version(certifi.__version__) >= Version("2026.10.19")
    print(f"Application certifi: {certifi.__version__}")
    check_store("application certifi", certifi.where())

# Verify botocore selects the updated certifi, rather than its bundled fallback.
if importlib.util.find_spec("botocore") is not None:
    from botocore.httpsession import get_cert_path

    assert Path(get_cert_path(True)).resolve() == Path(certifi.where()).resolve()
    check_store("botocore effective bundle", get_cert_path(True))
