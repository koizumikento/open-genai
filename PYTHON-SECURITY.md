# Python / CA baseline (2026-10-24)

The ten Python services use Python 3.12.15 on Debian trixie. This keeps the
existing Python minor version and makes the patch/distribution baseline explicit.
The image tag can still be rebuilt by its publisher; rebuild with `--pull
--no-cache` to obtain current Debian packages. Previously built images and
existing virtual environments are not updated by this source change.

Three independent trust inputs need attention:

- The six services using httpx or requests require `certifi>=2026.10.19`.
- All ten images bootstrap pip 26.2.2 from the hash-verified wheel linked by
  Python's release announcement, before installing application requirements.
  Updating application certifi alone does not replace pip's vendored bundle.
- All ten images refresh Debian's `ca-certificates` package separately. The
  inspected trixie package, `20250419+deb13u1`, is listed as patched in the
  incident's distribution guidance. The offline check also verifies the actual
  trust-store contents, rather than relying only on package version labels.

Do not disable TLS verification. The affected Mozilla-store roots are
`emSign ECC Root CA - G3` and `AAA Certificate Services`; other emSign/Comodo
roots must not be removed just because of their names. The offline check uses
the four exact SHA-256 root fingerprints in the incident's `roots.json`, also
covering two affected roots normally absent from Mozilla-based stores.
Updated trust stores may reject services still chaining to the affected roots;
their operators need to replace those chains. Custom CA files, mounted stores,
proxy-provided roots, host installers and external model/runtime containers need separate
review. Backend botocore ships a fallback CA bundle but normally selects certifi
when installed; the offline check verifies this effective bundle as well.

## Local verification

Build only the Python images (no application startup or production deployment).
At the audited commit the Compose files have an existing `depends_on` YAML
error, so use the Dockerfiles directly:

```sh
for service in backend rag-app whisper-app sd-app dify-app audit-app \
  usermgmt-app modelpolicy-app ngword-app prompt-app; do
  context="$service"
  case "$service" in backend|rag-app) context=. ;; esac
  docker build --pull --no-cache -t "open-genai-security-$service" \
    -f "$service/Dockerfile" "$context" || exit 1
done
```

Run the offline CA check against each resulting image, for example:

```sh
docker run --rm --network none \
  -v "$PWD/scripts/check-python-ca.py:/check-python-ca.py:ro" \
  --entrypoint python open-genai-security-backend /check-python-ca.py
docker run --rm --network none --entrypoint python open-genai-security-backend -m pip check
docker run --rm --network none --entrypoint python open-genai-security-backend \
  -m compileall -q app shared
```

Check all ten images; only backend and rag-app include `shared/`. The CA check
makes no network requests. No Python test/lint/type configuration existed at the
audited commit; image builds, dependency consistency, byte-compilation and
isolated application import/health checks are the applicable Python checks.

### Validation recorded for this change

On Linux/amd64, all ten Dockerfiles built with `--pull --no-cache`. All ten
images passed `pip check`, Python byte-compilation, the offline CA check, and
application import/OpenAPI plus mocked health checks (without startup lifespans).
Whisper's faster-whisper/ctranslate2/PyAV native imports passed without loading
or downloading a model. The new CA checker also correctly rejected the original
base image's pip CA bundle by the affected G3/AAA fingerprints.

Observed versions were Python 3.12.15, pip 26.2.2 (vendored certifi 2026.10.19),
application certifi 2026.10.23 in the six HTTP-client images, and Debian
ca-certificates 20250419+deb13u1. These checks do not assert that all CVEs are fixed.

Unchanged baseline issues were kept separate:

- Development, production and HTTP-verification Compose configurations fail
  parsing because `depends_on` mixes list and mapping forms. The development
  failure was reproduced in a clean worktree at the audited commit.
- `npm ci` fails on the existing lockfile's missing/inconsistent `@emnapi`
  entries, with both the image's npm 10 and a temporary npm 11 tool.
- In a disposable copy of the unchanged frontend/CDK source, npm 11 could install
  after repairing only that copy's lockfile. Web lint passed with one warning;
  CDK tests passed (582/582), and web/CDK TypeScript builds passed. Web tests
  failed (4 failures, 585 passes, in TeamAppCreateForm/TeamAppEditForm); CDK lint
  reported three existing errors. These are fallback-install results, not a
  successful frozen-lockfile check. No frontend or Compose files were changed.

No active root GitHub Actions workflows or repository webhooks existed during
publication review; nested `genai-web/.github/*.yaml.example` files are samples.
The draft PR therefore has no automatic CI configured. Full production-stack
startup, real API calls, non-amd64 builds and deployment were not run.

## Scope and remaining risks

This addresses the emSign CA incident, not every Python or dependency advisory.
The CPython `tar_filter` CVE-2026-114583 patch landed on October 22, after the
October 21 releases. No stable fixed release was established in this review,
and no direct tar extraction call was found in this repository. Python 3.12.15
must not be described as fixing that issue. Reassess when an official fixed
release/image is available; no speculative tar workaround is included here.

Other application dependency pins are unchanged. Transitive dependencies remain
unlocked; the new certifi minimum prevents older bundles from being selected.
Existing HTTP endpoints and application TLS-verification policies are unchanged.
Non-Python images (Node, nginx,
Keycloak, Qdrant, SeaweedFS, Ollama) and existing deployed artifacts are outside
this change. No production environment or real application API is contacted.

References:

- [certifi emSign advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2)
- [Python October 21 release and hash-verified pip bootstrap](https://blog.python.org/2026/10/python-3151-3149-31317/)
- [Incident scope, affected roots and distribution updates](https://emudhra.we-have-a-problem.com/)
- [Affected root certificate fingerprints](https://emudhra.we-have-a-problem.com/roots.json)
