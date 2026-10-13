"""Check availability and admin API authentication; run with pytest -m management."""

import pytest
from botocore.auth import S3SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

pytestmark = pytest.mark.management
INFO_PATH = "/rustfs/admin/v3/info"


def admin_get(http, settings, secret=None):
    """Send a signed GET to the native RustFS server-info endpoint.

    Use settings for the endpoint, identity, signing region, and default secret.
    S3SigV4Auth adds the signature and required payload-hash header. A secret
    override lets the negative test create a request signed with an incorrect key.
    Return the HTTP response so each test can inspect its status and body.
    """
    request = AWSRequest(method="GET", url=f"{settings.endpoint}{INFO_PATH}")
    S3SigV4Auth(
        Credentials(settings.access_key, secret or settings.secret_key), "s3", settings.region
    ).add_auth(request)
    return http.get(request.url, headers=dict(request.headers))


pytest.mark.parametrize("path", ["/health", "/health/ready"])
def test_health(settings, http, path):
    """Verify successful liveness and readiness responses from the running service.

    Purpose:
        Check the normal availability signals used by operators and startup checks.
        Liveness indicates that the process is up; readiness indicates that its
        dependencies are ready to serve requests.

    Cases and expected results:
        Send a GET to /health and, in a separate parameterized case, /health/ready.
        Each endpoint must return HTTP 200 after the service_ready fixture succeeds.
        These cases check the status code without inspecting the response body.

    Fixtures:
        settings supplies the endpoint and http supplies the shared HTTP client.
        The requests are read-only and create no resources requiring cleanup.
    """
    response = http.get(f"{settings.endpoint}{path}")
    assert response.status_code == 200, response.text


def test_admin_reports_server_and_storage(settings, http):
    """Verify authenticated visibility of healthy servers and the four-volume backend.

    Purpose:
        Check that the administrative API reports a usable storage deployment and
        that its drive counts match the supplied single-node Compose configuration.

    Steps and expected results:
        1. Sign a server-info GET with the configured administrator credentials.
        2. Expect HTTP 200 and a JSON object, accepting information directly at the
           root or inside the info envelope used by the tested RustFS image.
        3. Expect at least one server, every reported server to be online, and each
           server to report drives whose state is ok.
        4. Expect the backend to report four online disks and zero offline disks.

    Fixtures:
        settings supplies endpoint and signing credentials; http sends the request.
        This test reads server state without changing administrative configuration.
    """
    response = admin_get(http, settings)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, dict)
    # Upstream introduced an info envelope; older images return InfoMessage directly.
    info = payload.get("info", payload)
    assert isinstance(info, dict)
    assert info.get("servers"), info
    for server in info["servers"]:
        assert server.get("state") == "online", server
        assert server.get("drives"), server
        for disk in server["drives"]:
            assert disk.get("state") == "ok", disk
    assert info["backend"]["onlineDisks"] == 4
    assert info["backend"]["offlineDisks"] == 0


@pytest.mark.parametrize("authentication", ["unsigned", "wrong-secret"])
def test_admin_rejects_invalid_authentication(settings, http, authentication):
    """Verify that absent or incorrect authentication is rejected by the admin API.

    Purpose:
        Check that an unauthenticated or incorrectly signed caller cannot obtain
        the server-info response. The valid administrator setup is checked first
        by service_ready so the negative cases target a working service.

    Cases and expected results:
        unsigned: Send a GET without authentication. Expect HTTP 400 or 403 with
            InvalidRequest or AccessDenied, matching the documented image behavior.
        wrong-secret: Sign the GET with the configured access key but an incorrect
            secret. Expect HTTP 403 and SignatureDoesNotMatch.
        Neither response may contain the servers field name.

    Fixtures:
        settings supplies connection details and the legitimate identity; http
        sends the requests; authentication selects the parameterized case.
        These read-only requests create no users, policies, or storage resources.
    """
    response = (
        http.get(f"{settings.endpoint}{INFO_PATH}")
        if authentication == "unsigned"
        else admin_get(http, settings, secret="deliberately-wrong-secret")
    )
    if authentication == "unsigned":
        assert response.status_code in (400, 403), response.text
        assert "InvalidRequest" in response.text or "AccessDenied" in response.text
    else:
        assert response.status_code == 403, response.text
        assert "SignatureDoesNotMatch" in response.text
    assert "servers" not in response.text
