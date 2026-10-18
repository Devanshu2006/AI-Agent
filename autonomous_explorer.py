"""Autonomous website explorer.

Crawls the public site, optionally logs in and crawls the authenticated part,
and records for every page:
  * its structure (headings, links, buttons, inputs with labels, forms)
  * runtime diagnostics (HTTP status, console/JS errors, failed requests)

The diagnostics are what bug_detector.py uses to find real bugs.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from auth_handler import authenticate_if_configured

MAX_PAGES = 25
MAX_DEPTH = 3
MAX_QUERY_VARIANTS_PER_PATH = 3  # stops /items?page=1..9999 style crawl traps
NAVIGATION_TIMEOUT_MS = 60_000
APPLICATION_READY_TIMEOUT_MS = 45_000
HEADLESS = os.getenv("HEADLESS", "0") == "1"

GENERATED_ROOT = Path("generated_tests")
AUTH_STATE_PATH = GENERATED_ROOT / "auth_state.json"
SCREENSHOT_DIR = Path("artifacts") / "screenshots"

# Link TEXT that we never follow.
DANGEROUS_KEYWORDS = (
    "delete", "remove permanently", "destroy", "purchase", "buy now",
    "pay now", "payment", "checkout", "transfer", "withdraw",
    "cancel subscription", "place order", "submit payment", "logout",
)

# Link URL paths that we never follow. Icon-only links have no text, so the
# text filter alone would happily GET /logout and kill the session.
DANGEROUS_URL_RE = re.compile(
    r"(^|[/_\-.])(logout|log-out|signout|sign-out|delete|destroy|remove|"
    r"unsubscribe|cancel)([/_\-.]|$)",
    re.IGNORECASE,
)

IGNORED_EXTENSIONS = (
    ".pdf", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".mp4", ".mp3", ".csv", ".xlsx", ".docx",
)


# ============================================================
# URL / TEXT HELPERS
# ============================================================

def normalize_url(url):
    """Remove fragments and trailing slashes while preserving query strings."""
    url, _ = urldefrag(url.strip())
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return parsed._replace(path=path, fragment="").geturl()


def is_same_domain(base_url, target_url):
    """Only explore HTTP(S) pages on the starting hostname."""
    base = urlparse(base_url)
    target = urlparse(target_url)
    return (
        target.scheme in ("http", "https")
        and (target.hostname or "").lower() == (base.hostname or "").lower()
    )


def is_dangerous_text(text):
    text = (text or "").strip().lower()
    return any(keyword in text for keyword in DANGEROUS_KEYWORDS)


def is_dangerous_link(text, href):
    if is_dangerous_text(text):
        return True
    return bool(DANGEROUS_URL_RE.search(urlparse(href or "").path))


def safe_text(value):
    return "" if value is None else str(value).strip()


# ============================================================
# RUNTIME DIAGNOSTICS
# ============================================================

class PageMonitor:
    """Collects runtime problems for the page currently being visited."""

    def __init__(self, page, base_url):
        self.base_host = (urlparse(base_url).hostname or "").lower()
        self.reset()
        page.on("console", self._on_console)
        page.on("pageerror", self._on_page_error)
        page.on("response", self._on_response)
        page.on("requestfailed", self._on_request_failed)

    def reset(self):
        self.console_errors = []
        self.page_errors = []
        self.bad_responses = []
        self.failed_requests = []

    def _same_host(self, url):
        return (urlparse(url).hostname or "").lower() == self.base_host

    def _on_console(self, message):
        # "Failed to load resource" is already captured via the response event.
        if message.type == "error" and not message.text.startswith(
            "Failed to load resource"
        ):
            self.console_errors.append(message.text[:300])

    def _on_page_error(self, error):
        self.page_errors.append(str(error)[:300])

    def _on_response(self, response):
        if (
            response.status >= 400
            and self._same_host(response.url)
            and not response.url.endswith("favicon.ico")
        ):
            self.bad_responses.append({
                "url": response.url,
                "status": response.status,
                "type": response.request.resource_type,
            })

    def _on_request_failed(self, request):
        failure = str(request.failure or "")
        # ERR_ABORTED is normal when navigation cancels in-flight requests.
        if self._same_host(request.url) and "ERR_ABORTED" not in failure:
            self.failed_requests.append(
                {"url": request.url, "failure": failure[:200]}
            )

    def snapshot(self):
        return {
            "console_errors": list(dict.fromkeys(self.console_errors))[:10],
            "page_errors": list(dict.fromkeys(self.page_errors))[:10],
            "bad_responses": self.bad_responses[:15],
            "failed_requests": self.failed_requests[:15],
        }


# ============================================================
# WAITING / NAVIGATION
# ============================================================

def wait_for_application(page, timeout_ms=APPLICATION_READY_TIMEOUT_MS):
    """
    Wait for a condition, not a fixed delay.

    Render's temporary splash page contains 'Application loading'. If that
    splash is present, wait until it is gone. Ordinary sites proceed at once.
    """
    try:
        page.locator("body").wait_for(state="visible", timeout=10_000)
    except PlaywrightTimeoutError:
        print("[Explorer] Body did not become visible in time.")
        return False

    try:
        page.wait_for_function(
            """() => {
                const title = (document.title || '').toLowerCase();
                const body = (document.body?.innerText || '').toLowerCase();
                const renderSplash =
                    title.includes('render - application loading') ||
                    (body.includes('application loading') && body.length < 2000);
                return !renderSplash;
            }""",
            timeout=timeout_ms,
        )
        return True
    except PlaywrightTimeoutError:
        print("[Explorer] Application-ready condition timed out; inspecting anyway.")
        return False


def settle(page, timeout_ms=5_000):
    """Let client-side apps finish their first requests (best effort)."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass


def visit(page, monitor, url):
    """Navigate to url. Returns (ok, http_status). Error pages (404...) are ok."""
    monitor.reset()
    status = None
    try:
        response = page.goto(
            url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS
        )
        status = response.status if response else None
    except PlaywrightTimeoutError as error:
        print(f"    Navigation timed out: {error}")
        if page.url == "about:blank":
            return False, None
    except Exception as error:
        print(f"    Navigation failed: {error}")
        return False, None

    wait_for_application(page)
    settle(page)
    return True, status


# ============================================================
# PAGE INSPECTION (one browser round-trip instead of hundreds)
# ============================================================

INSPECT_JS = r"""
() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const attr = (el, name) => clean(el.getAttribute(name));
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 &&
           s.visibility !== 'hidden' && s.display !== 'none';
  };
  const labelOf = (el) => {
    if (el.labels && el.labels.length) {
      return clean(Array.from(el.labels).map((l) => l.innerText).join(' '));
    }
    const ref = el.getAttribute('aria-labelledby');
    const node = ref && document.getElementById(ref);
    return node ? clean(node.innerText) : '';
  };
  const take = (selector, limit, mapper) =>
    Array.from(document.querySelectorAll(selector)).slice(0, limit).map(mapper);

  return {
    title: document.title || '',
    lang: document.documentElement.lang || '',
    headings: take('h1,h2,h3,h4,h5,h6', 50, (el) => ({
      level: el.tagName.toLowerCase(), text: clean(el.innerText),
    })).filter((h) => h.text),
    links: take('a[href]', 200, (el) => ({
      text: clean(el.innerText), href: el.href,
      aria_label: attr(el, 'aria-label'), target: attr(el, 'target'),
    })),
    buttons: take(
      "button, input[type=button], input[type=submit], input[type=reset], [role=button]",
      100,
      (el) => ({
        text: clean(el.innerText) || attr(el, 'value'),
        aria_label: attr(el, 'aria-label'), name: attr(el, 'name'),
        id: attr(el, 'id'), type: attr(el, 'type'),
        test_id: attr(el, 'data-testid'),
        disabled: el.disabled === true, visible: isVisible(el),
      })
    ),
    inputs: take('input:not([type=hidden]), textarea, select', 150, (el) => ({
      tag: el.tagName.toLowerCase(), type: attr(el, 'type'),
      name: attr(el, 'name'), id: attr(el, 'id'),
      placeholder: attr(el, 'placeholder'), aria_label: attr(el, 'aria-label'),
      title: attr(el, 'title'), label: labelOf(el),
      test_id: attr(el, 'data-testid'),
      required: el.required === true, visible: isVisible(el),
    })),
    forms: take('form', 50, (el) => ({
      action: attr(el, 'action'), method: (attr(el, 'method') || '').toUpperCase(),
      id: attr(el, 'id'),
      input_count: el.querySelectorAll('input:not([type=hidden]), textarea, select').length,
      has_password: !!el.querySelector('input[type=password]'),
      has_email: !!el.querySelector('input[type=email], input[name*=email i]'),
      text: clean(el.innerText).slice(0, 500),
    })),
    images_missing_alt: document.querySelectorAll('img:not([alt])').length,
    h1_count: document.querySelectorAll('h1').length,
    text: ((document.body && document.body.innerText) || '').trim().slice(0, 4000),
  };
}
"""


def empty_page(url):
    return {
        "url": url, "title": "", "lang": "", "headings": [], "links": [],
        "buttons": [], "inputs": [], "forms": [],
        "images_missing_alt": 0, "h1_count": 0, "text": "",
    }


def classify_form(form):
    combined = f"{form['text']} {form['action']}".lower()
    if any(w in combined for w in ("signup", "sign up", "register", "create account")):
        return "signup"
    if any(w in combined for w in ("login", "log in", "sign in")):
        return "login"
    if form["has_password"] and form["has_email"]:
        return "authentication"
    return "data_form" if form["input_count"] else "unknown"


def inspect_page(page):
    """Collect a bounded snapshot of visible page structure and text."""
    data = empty_page(normalize_url(page.url))

    try:
        data.update(page.evaluate(INSPECT_JS))
    except Exception as error:
        print(f"[Explorer] Page inspection failed: {error}")

    for link in data["links"]:
        href = link.get("href", "")
        if urlparse(href).scheme in ("http", "https"):
            link["href"] = normalize_url(href)
        link["dangerous"] = is_dangerous_link(
            f"{link.get('text', '')} {link.get('aria_label', '')}", href
        )

    for button in data["buttons"]:
        button["dangerous"] = is_dangerous_text(
            f"{button.get('text', '')} {button.get('aria_label', '')} "
            f"{button.get('name', '')}"
        )

    for form in data["forms"]:
        if form.get("action"):
            form["action"] = urljoin(page.url, form["action"])
        form["type"] = classify_form(form)

    data["title"] = safe_text(data["title"])
    # Lets later stages tell "really internal page" from "public page seen again".
    data["text_hash"] = hashlib.md5(data["text"].encode("utf-8")).hexdigest()[:10]
    return data


def extract_page_links(page_data, base_url):
    """Unique same-domain HTTP(S) links, excluding downloads and risky actions."""
    discovered = []
    for link in page_data.get("links", []):
        href = link.get("href")
        if not href or link.get("dangerous"):
            continue
        if not is_same_domain(base_url, href):
            continue
        if urlparse(href).path.lower().endswith(IGNORED_EXTENSIONS):
            continue
        if href not in discovered:
            discovered.append(href)
    return discovered


def detect_page_type(page_data):
    text = f"{page_data.get('title', '')} {page_data.get('text', '')}".lower()

    for form in page_data.get("forms", []):
        if form.get("type") in ("signup", "login"):
            return form["type"]

    for keywords, page_type in (
        (("sign up", "signup", "register", "create account"), "signup"),
        (("login", "log in", "sign in"), "login"),
        (("checkout",), "checkout"),
        (("cart",), "cart"),
        (("product",), "product"),
        (("dashboard",), "dashboard"),
    ):
        if any(keyword in text for keyword in keywords):
            return page_type
    return "general"


def save_website_map(result, output_file="website_map.json"):
    path = Path(output_file)
    path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n[Explorer] Website map saved: {path.resolve()}")


def ask_yes_no(question):
    if not sys.stdin.isatty():
        print(f"\n{question} -> no (non-interactive session)")
        return False
    while True:
        answer = input(f"\n{question} (yes/no): ").strip().lower()
        if answer in ("yes", "y"):
            return True
        if answer in ("no", "n"):
            return False
        print("Please enter yes or no.")


# ============================================================
# ONE CRAWL STAGE (used for both public and authenticated)
# ============================================================

def crawl(
    page, monitor, start_url, root_url, stage, max_pages, max_depth, seen,
    inspect_current_first=False,
):
    """Breadth-first crawl of one stage. Returns a list of page records."""
    label = f"[{stage}]"
    queue = [(start_url, 0)]
    queued = {start_url}
    query_variants = {}
    records = []
    inspect_in_place = inspect_current_first

    while queue and len(records) < max_pages:
        url, depth = queue.pop(0)

        if (stage, url) in seen or depth > max_depth:
            continue
        if not is_same_domain(root_url, url):
            continue
        seen.add((stage, url))

        print("\n" + "-" * 70)
        print(f"{label} Page {len(records) + 1}/{max_pages}  depth={depth}")
        print(f"{label} Visiting: {url}")

        if inspect_in_place:
            inspect_in_place = False
            monitor.reset()
            status = None
            print(f"{label} Inspecting the page that is already open after login.")
        else:
            ok, status = visit(page, monitor, url)
            if not ok:
                continue

        # A redirect may land on a page we already recorded.
        final_url = normalize_url(page.url)
        if final_url != url:
            if (stage, final_url) in seen:
                print(f"{label} Redirected to an already-visited page: {final_url}")
                continue
            seen.add((stage, final_url))

        record = inspect_page(page)
        record.update({
            "depth": depth,
            "stage": stage,
            "requested_url": url,
            "http_status": status,
            "diagnostics": monitor.snapshot(),
        })
        record["page_type"] = detect_page_type(record)
        records.append(record)

        diag = record["diagnostics"]
        print(f"{label} Status: {status}  Title: {record['title']!r}")
        print(
            f"{label} Type: {record['page_type']}  Links: {len(record['links'])}  "
            f"Forms: {len(record['forms'])}  JS errors: "
            f"{len(diag['page_errors']) + len(diag['console_errors'])}"
        )

        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(SCREENSHOT_DIR / f"{stage}_{len(records):02d}.png"),
                full_page=True,
            )
        except Exception as error:
            print(f"{label} Screenshot failed: {error}")

        if depth < max_depth:
            added = 0
            for link in extract_page_links(record, root_url):
                if (stage, link) in seen or link in queued:
                    continue
                parsed = urlparse(link)
                if parsed.query:
                    count = query_variants.get(parsed.path, 0)
                    if count >= MAX_QUERY_VARIANTS_PER_PATH:
                        continue
                    query_variants[parsed.path] = count + 1
                queue.append((link, depth + 1))
                queued.add(link)
                added += 1
            print(f"{label} New URLs queued: {added}")

    print(f"\n{label} Exploration completed. Pages inspected: {len(records)}")
    return records


def explore_authenticated_stage(
    page, context, start_url, max_pages, max_depth, seen
):
    """Log in (per AUTH_MODE), save the session, crawl. Returns (records, session_saved)."""
    auth = authenticate_if_configured(page, start_url, context=context)
    auth_page = auth.get("page", page)
    print("[Auth] Result:", {k: v for k, v in auth.items() if k != "page"})

    if auth.get("authenticated") is not True:
        print(
            "[Stage 2] Authentication was not verified. Skipping authenticated "
            "exploration instead of mislabelling public pages as authenticated."
        )
        return [], False

    current_url = normalize_url(auth_page.url)
    if current_url == "about:blank" or not is_same_domain(start_url, current_url):
        print("[Stage 2] Current page is blank or outside the starting domain.")
        return [], False

    # Generated authenticated tests start from this saved session
    # (see the auth_page fixture in generated_tests/conftest.py).
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(AUTH_STATE_PATH))
    print(f"[Auth] Session saved for generated tests: {AUTH_STATE_PATH}")

    monitor = PageMonitor(auth_page, start_url)
    records = crawl(
        auth_page, monitor, current_url, start_url, "authenticated",
        max_pages, max_depth, seen, inspect_current_first=True,
    )
    return records, True


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def autonomous_explore(
    start_url, max_pages=MAX_PAGES, max_depth=MAX_DEPTH,
    explore_authenticated=None,
):
    """Explore public pages, then optionally authenticated pages.

    explore_authenticated: True/False to decide up front, None to ask.
    """
    parsed = urlparse(start_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Enter a complete URL, including https:// or http://")

    start_url = normalize_url(start_url)

    print("\n" + "=" * 70)
    print("          AUTONOMOUS WEBSITE EXPLORATION")
    print("=" * 70)
    print(f"\n[Explorer] Starting URL: {start_url}")
    print(f"[Explorer] Max pages per stage: {max_pages}   Max depth: {max_depth}")

    pages = []
    seen = set()
    session_saved = False

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=HEADLESS)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(10_000)
        monitor = PageMonitor(page, start_url)

        try:
            print("\n" + "=" * 70)
            print("STAGE 1: PUBLIC WEBSITE EXPLORATION")
            print("=" * 70)
            pages.extend(crawl(
                page, monitor, start_url, start_url, "public",
                max_pages, max_depth, seen,
            ))

            if explore_authenticated is None:
                explore_authenticated = ask_yes_no(
                    "Do you want to explore authenticated pages?"
                )

            if explore_authenticated:
                print("\n" + "=" * 70)
                print("STAGE 2: AUTHENTICATED WEBSITE EXPLORATION")
                print("=" * 70)
                print(
                    "[Auth] Use AUTH_MODE=manual for manual login/signup, "
                    "or AUTH_MODE=login for configured automatic login."
                )
                records, session_saved = explore_authenticated_stage(
                    page, context, start_url, max_pages, max_depth, seen
                )
                pages.extend(records)
            else:
                print("\n[Explorer] Skipping authenticated exploration.")
        finally:
            browser.close()

    result = {
        "website": start_url,
        "total_pages": len(pages),
        "public_pages": sum(1 for p in pages if p.get("stage") == "public"),
        "authenticated_pages": sum(
            1 for p in pages if p.get("stage") == "authenticated"
        ),
        "auth_state_saved": session_saved,
        "pages": pages,
        "visited_urls": list(dict.fromkeys(p["url"] for p in pages)),
    }
    save_website_map(result)

    print("\n" + "=" * 70)
    print("          EXPLORATION COMPLETE")
    print("=" * 70)
    print(f"[Explorer] Total pages: {result['total_pages']}")
    print(f"[Explorer] Public pages: {result['public_pages']}")
    print(f"[Explorer] Authenticated pages: {result['authenticated_pages']}")
    return result


if __name__ == "__main__":
    url = input("Enter website URL to explore: ").strip()
    try:
        explored = autonomous_explore(url)
        if not explored["pages"]:
            print("\n[Explorer] No pages were inspected. Check the URL, network, "
                  "certificate, or website availability.")
    except (ValueError, KeyboardInterrupt) as error:
        print(f"\n[Explorer] Stopped: {error}")
