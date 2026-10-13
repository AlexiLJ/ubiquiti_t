import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.gui


@pytest.mark.smoke
def test_console_smoke(page, settings, bucket):
    """Verify that a user can log in and see an API-created bucket in the console.

        Purpose:
            Exercise one essential browser journey: open the login page, authenticate,
            and view stored resources. Using a bucket created through S3 also checks
            that the console displays resources from the same storage service.

        Preconditions:
            RustFS and its English-language console must be running. The session-level
            service_ready fixture checks liveness and authenticated S3 access. The
            bucket fixture creates a unique, unversioned bucket before this test runs.

        Steps and expected results:
            1. Open settings.console, which defaults to the RustFS console login URL.
            2. Fill the access key and password from settings, then submit the form.
            3. Verify that the Buckets heading becomes visible after login.
            4. Verify that the exact name of the fixture-created bucket is visible.
            Each visibility assertion waits up to 15 seconds for its expected element.
            Missing elements or failed browser actions cause the test to fail.

        Fixtures:
            page: Playwright page in an isolated browser context for this test.
            settings: Configured console URL, access key, and secret key.
            bucket: Name of the unique bucket created through the S3 API.

        Cleanup:
            The bucket fixture deletes its objects and bucket, including after an
            assertion failure. pytest-playwright closes the page and browser context.

        Execution:
            Marked as both gui and smoke; --gui enables the optional console test.
            Run headless with installed Chrome using:
            uv run pytest -m smoke --gui --browser chromium --browser-channel chrome
            Add --headed --slowmo 500 to watch the browser perform its actions.
        """
    page.goto(settings.console)
    page.get_by_role("textbox").first.fill(settings.access_key)
    page.locator('input[type="password"]').fill(settings.secret_key)
    page.get_by_role("button", name=re.compile(r"sign in|log in|login", re.IGNORECASE)).click()
    expect(page.get_by_role("heading", name="Buckets", exact=True)).to_be_visible(timeout=15_000)
    expect(page.get_by_text(bucket, exact=True)).to_be_visible(timeout=15_000)
