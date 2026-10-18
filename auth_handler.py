"""Optional authentication stage for the website explorer.

AUTH_MODE:
    skip    - do not authenticate
    manual  - user logs in or registers manually in the browser
    login   - fill recognized login fields using environment variables
    signup  - fill recognized registration fields using environment variables

Credentials come from environment variables and are never printed.

Every return value is a dict with `attempted`, `authenticated` (True/False,
never None) and `mode`; `page` is included when a browser page is involved.
"""
import os
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _normalize(url):
    parsed = urlparse(url)
    return parsed._replace(fragment="", path=parsed.path.rstrip("/") or "/").geturl()


def _first_visible(page, selectors):
    """Return the first visible, enabled element matching known selectors."""
    for selector in selectors:
        try:
            elements = page.locator(selector)
            for index in range(min(elements.count(), 10)):
                element = elements.nth(index)
                if element.is_visible() and element.is_enabled():
                    return element
        except Exception:
            continue
    return None


def _open_auth_page(page, mode):
    """Open a recognizable login or registration page if available."""
    keywords = (
        ("login", "log in", "sign in")
        if mode == "login"
        else ("sign up", "signup", "register", "create account")
    )
    try:
        for element in page.locator("a, button").all()[:200]:
            try:
                text = (element.inner_text() or "").strip().lower()
                aria = (element.get_attribute("aria-label") or "").strip().lower()
                if any(word in f"{text} {aria}" for word in keywords):
                    if element.is_visible() and element.is_enabled():
                        print(f"[Auth] Opening {mode} page: {text or aria}")
                        element.click()
                        page.wait_for_load_state("domcontentloaded", timeout=10_000)
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _fill_first(page, selectors, value, field_name):
    """Fill a recognized visible field without guessing arbitrary fields."""
    if not value:
        return False
    element = _first_visible(page, selectors)
    if element is None:
        print(f"[Auth] Could not identify the {field_name} field.")
        return False
    try:
        element.fill(value)
        return True
    except Exception as error:
        print(f"[Auth] Could not fill {field_name}: {error}")
        return False


def _submit_auth_form(page):
    """Submit a recognizable form; do not click unrelated page buttons."""
    try:
        forms = page.locator("form")
        for index in range(min(forms.count(), 20)):
            form = forms.nth(index)
            try:
                if not form.is_visible():
                    continue
                submit = form.locator("button[type='submit'], input[type='submit']")
                if submit.count() and submit.first.is_visible():
                    submit.first.click()
                    return True
                buttons = form.locator("button")
                if buttons.count() and buttons.first.is_visible():
                    buttons.first.click()
                    return True
            except Exception:
                continue
    except Exception:
        pass
    print("[Auth] No recognizable form submit button was found.")
    return False


def _wait_for_login_result(page, login_url, timeout_ms=10_000):
    """
    Decide whether login worked, waiting on a condition instead of guessing.

    Success = the password field is gone AND (the URL changed OR no visible
    error message). Returns True/False, never None.
    """
    password = page.locator("input[type='password']:visible")
    try:
        password.first.wait_for(state="hidden", timeout=timeout_ms)
    except Exception:
        pass  # still visible (or page navigated); checked below

    try:
        if password.count() > 0:
            return False
        url_changed = _normalize(page.url) != _normalize(login_url)
        error_visible = page.locator(
            "[role='alert']:visible, .error:visible, "
            ".alert-danger:visible, .invalid-feedback:visible"
        ).count() > 0
        return url_changed or not error_visible
    except Exception:
        return False


def _result(mode, page=None, attempted=True, authenticated=False):
    result = {"attempted": attempted, "authenticated": authenticated, "mode": mode}
    if page is not None:
        result["page"] = page
    return result


def authenticate_if_configured(page, start_url, context=None):
    mode = os.getenv("AUTH_MODE", "skip").strip().lower()

    if mode not in {"skip", "manual", "login", "signup"}:
        print(f"[Auth] Unknown AUTH_MODE={mode!r}; skipping authentication.")
        return _result(mode, page, attempted=False)

    if mode == "skip":
        print("[Auth] Authentication skipped (AUTH_MODE=skip).")
        return _result(mode, page, attempted=False)

    print(f"\n[Auth] Authentication mode: {mode}")
    print(f"[Auth] Website: {start_url}")

    # ---------------------------------------------------------------- manual
    if mode == "manual":
        print(
            "\n[Auth] Browser open rakhein aur manually login karein."
            "\n[Auth] Dashboard/internal page khulne ke baad Enter dabayein."
        )
        input("[Auth] Press Enter after login...")

        # Login may have opened a new tab or popup.
        if context is not None:
            try:
                open_pages = [p for p in context.pages if not p.is_closed()]
                if open_pages:
                    page = open_pages[-1]
            except Exception:
                pass

        try:
            password_visible = (
                page.locator("input[type='password']:visible").count() > 0
            )
            print(f"[Auth] Current page after login: {page.url}")
            if password_visible:
                print("[Auth] Password field is still visible. Login may not have completed.")
                return _result(mode, page, authenticated=False)
            print("[Auth] Password field is not visible. Continuing.")
            return _result(mode, page, authenticated=True)
        except Exception as error:
            print(f"[Auth] Could not inspect the login page: {error}")
            return _result(mode, page, authenticated=False)

    # ----------------------------------------------------------- login/signup
    username = os.getenv("TEST_USERNAME", "").strip()
    email = os.getenv("TEST_EMAIL", "").strip()
    password = os.getenv("TEST_PASSWORD", "")
    full_name = os.getenv("TEST_FULL_NAME", "").strip()
    identifier = username or email

    if not password:
        print("[Auth] TEST_PASSWORD is missing; authentication skipped.")
        return _result(mode, page, attempted=False)
    if mode == "login" and not identifier:
        print("[Auth] Set TEST_USERNAME or TEST_EMAIL for login.")
        return _result(mode, page, attempted=False)
    if mode == "signup" and not email:
        print("[Auth] Set TEST_EMAIL for account registration.")
        return _result(mode, page, attempted=False)

    # The explorer already opened the site; follow a login/register link if any.
    _open_auth_page(page, mode)

    try:
        if page.locator("input[type='password']").count() == 0:
            print("[Auth] No password field found on the current page.")
            print("[Auth] Use AUTH_MODE=manual if the login flow needs extra steps.")
            return _result(mode, page, attempted=False)
    except Exception:
        return _result(mode, page, attempted=False)

    password_selectors = [
        "input[type='password']",
        "input[autocomplete='current-password']"
        if mode == "login"
        else "input[autocomplete='new-password']",
    ]
    identifier_selectors = [
        "input[type='email']",
        "input[autocomplete='username']",
        "input[name*='email' i]",
        "input[id*='email' i]",
        "input[name*='username' i]",
        "input[id*='username' i]",
        "input[name*='user' i]",
        "input[id*='user' i]",
        "input[type='text']",
    ]
    if mode == "signup":
        identifier_selectors = [
            "input[type='email']",
            "input[autocomplete='email']",
            "input[name*='email' i]",
            "input[id*='email' i]",
        ]

    if mode == "signup" and full_name:
        _fill_first(
            page,
            [
                "input[autocomplete='name']",
                "input[name='name' i]",
                "input[id='name' i]",
                "input[name*='full_name' i]",
                "input[id*='full_name' i]",
            ],
            full_name,
            "full name",
        )

    identifier_filled = _fill_first(
        page,
        identifier_selectors,
        email if mode == "signup" else identifier,
        "email/username",
    )
    password_filled = _fill_first(page, password_selectors, password, "password")

    if not identifier_filled or not password_filled:
        print("[Auth] Required fields were not filled; stopping this attempt.")
        return _result(mode, page, authenticated=False)

    # Registration pages can require extra fields. Never guess their values.
    if mode == "signup":
        try:
            required_empty = page.locator(
                "input[required], select[required], textarea[required]"
            ).evaluate_all(
                """elements => elements.filter(el =>
                    !el.disabled && el.type !== 'hidden' &&
                    !String(el.value || '').trim()
                ).map(el => el.name || el.type || el.tagName)"""
            )
            if required_empty:
                print("[Auth] Other required fields remain empty. "
                      "Use manual mode for this registration form.")
                return _result(mode, page, authenticated=False)
        except Exception:
            pass

    login_url = page.url
    if not _submit_auth_form(page):
        return _result(mode, page, authenticated=False)

    authenticated = _wait_for_login_result(page, login_url)
    if authenticated:
        print("[Auth] Login looks successful (password form gone, no error shown).")
    else:
        print("[Auth] The password field is still visible or an error is shown. "
              "Login/registration may have failed or need more steps.")
    return _result(mode, page, authenticated=authenticated)
