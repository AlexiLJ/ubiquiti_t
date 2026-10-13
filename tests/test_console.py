import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.gui


@pytest.mark.smoke
def test_console_smoke(page, settings, bucket):
    pass
    page.goto(settings.console)
    page.get_by_role("textbox").first.fill(settings.access_key)
    page.locator('input[type="password"]').fill(settings.secret_key)
    page.get_by_role("button", name=re.compile(r"sign in|log in|login", re.IGNORECASE)).click()
    expect(page.get_by_role("heading", name="Buckets", exact=True)).to_be_visible(timeout=15_000)
    expect(page.get_by_text(bucket, exact=True)).to_be_visible(timeout=15_000)
