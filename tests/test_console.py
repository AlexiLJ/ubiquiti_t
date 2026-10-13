import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.gui


@pytest.mark.smoke
def test_console_smoke(page, settings, bucket):
    pass
