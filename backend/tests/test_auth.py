"""Offline regressions for SAML metadata transport certificate validation."""

import ssl
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from onelogin.saml2 import idp_metadata_parser

from app import auth


METADATA = b"""<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="https://idp.example.invalid/">
  <IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        Location="https://idp.example.invalid/sso"/>
  </IDPSSODescriptor>
</EntityDescriptor>"""


class MetadataTransportTests(unittest.TestCase):
    def setUp(self):
        auth.reset_settings_cache()
        self.addCleanup(auth.reset_settings_cache)

    def _check_metadata_transport(self, url):
        response = Mock()
        response.read.return_value = METADATA
        with (
            patch.object(auth, "IDP_METADATA_URL", url),
            patch.object(idp_metadata_parser.urllib2, "urlopen", return_value=response) as open_url,
            patch.object(
                auth.OneLogin_Saml2_IdPMetadataParser,
                "parse_remote",
                wraps=auth.OneLogin_Saml2_IdPMetadataParser.parse_remote,
            ) as parse_remote,
        ):
            settings = auth.get_saml_settings()
            self.assertEqual(settings["idp"]["entityId"], "https://idp.example.invalid/")
            self.assertIs(auth.get_saml_settings(), settings)
            parse_remote.assert_called_once_with(url, validate_cert=True)
            open_url.assert_called_once()
            self.assertEqual(open_url.call_args.args[0].full_url, url)
            # urllib's secure default context is used; no CERT_NONE override.
            self.assertNotIn("context", open_url.call_args.kwargs)

    def test_https_metadata_uses_certificate_validation(self):
        self._check_metadata_transport("https://idp.example.invalid/metadata")

    def test_internal_http_development_metadata_still_parses(self):
        self._check_metadata_transport(
            "http://keycloak:8080/kc/realms/open-genai/protocol/saml/descriptor"
        )

    def test_invalid_certificate_propagates_without_fallback_or_cache(self):
        certificate_error = ssl.SSLCertVerificationError("untrusted test certificate")
        url = "https://idp.example.invalid/metadata"
        for error in (certificate_error, URLError(certificate_error)):
            with (
                self.subTest(error=type(error).__name__),
                patch.object(auth, "IDP_METADATA_URL", url),
                patch.object(idp_metadata_parser.urllib2, "urlopen", side_effect=error) as open_url,
                patch.object(
                    auth.OneLogin_Saml2_IdPMetadataParser,
                    "parse_remote",
                    wraps=auth.OneLogin_Saml2_IdPMetadataParser.parse_remote,
                ) as parse_remote,
            ):
                with self.assertRaises(type(error)) as caught:
                    auth.get_saml_settings()
                self.assertIs(caught.exception, error)
                self.assertIsNone(auth._settings_cache)
                parse_remote.assert_called_once_with(url, validate_cert=True)
                open_url.assert_called_once()
                self.assertNotIn("context", open_url.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
