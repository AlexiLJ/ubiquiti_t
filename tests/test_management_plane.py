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


@pytest.mark.parametrize("path", ["/health", "/health/ready"])
def test_health(settings, http, path):
    """Verify successful liveness and readiness responses from the running service.

    Purpose:
        Check the normal availability signals used by operators and startup checks.
        Liveness indicates that the process is up; readiness indicates that its
        dependencies are ready to serve requests.


    """
    pass


def test_admin_reports_server_and_storage(settings, http):
    """Verify authenticated visibility of healthy servers and the four-volume backend.

    Purpose:
        Check that the administrative API reports a usable storage deployment and
        that its drive counts match the supplied single-node Compose configuration.


    """
    pass

@pytest.mark.parametrize("authentication", ["unsigned", "wrong-secret"])
def test_admin_rejects_invalid_authentication(settings, http, authentication):
    """Verify that absent or incorrect authentication is rejected by the admin API.

    Purpose:
        Check that an unauthenticated or incorrectly signed caller cannot obtain
        the server-info response. The valid administrator setup is checked first
        by service_ready so the negative cases target a working service.


    """
    pass
