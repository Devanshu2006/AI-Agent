"""Shared fixtures for generated Playwright tests."""

from pathlib import Path

import pytest

AUTH_STATE = Path(__file__).resolve().parent / "auth_state.json"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "bug: regression test for a bug found during exploration",
    )
    config.addinivalue_line(
        "markers",
        "authenticated: test requires an authenticated browser session",
    )


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Reuse the session saved by the website explorer when available."""
    args = dict(browser_context_args)
    args.setdefault("viewport", {"width": 1440, "height": 900})  # same size the explorer used

    if AUTH_STATE.exists():
        args["storage_state"] = str(AUTH_STATE)

    return args


@pytest.fixture
def auth_page(browser):
    """Explicitly create a page using the saved authenticated session."""
    if not AUTH_STATE.exists():
        pytest.skip(
            "No saved login session. Configure authentication and explore again."
        )

    context = browser.new_context(
        storage_state=str(AUTH_STATE),
        viewport={"width": 1440, "height": 900},
    )
    page = context.new_page()

    try:
        yield page
    finally:
        context.close()
