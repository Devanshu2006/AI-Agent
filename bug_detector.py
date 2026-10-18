"""Bug detection and bug-test generation.

Detection is DETERMINISTIC (HTTP statuses, JS/console errors, failed requests,
visible server-error text, basic accessibility gaps). An LLM is not asked to
"spot bugs" in page text, because that produces false positives.

For every confirmed bug a regression test is generated from a fixed template.
The test asserts the CORRECT behaviour, so it fails while the bug exists.
By default it is marked xfail(strict=False):
  * XFAIL in pytest output  -> bug still present (suite stays green)
  * XPASS in pytest output  -> bug is fixed; delete the xfail marker
Set BUG_TESTS_XFAIL=0 if you prefer the bug tests to fail loudly.

Only repr()-escaped values from the crawled site are ever written into the
generated code, so a hostile page cannot inject code into the test file.
"""
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

GENERATED_TESTS_DIR = Path("generated_tests") / "tests"
BUG_TEST_FILE = GENERATED_TESTS_DIR / "test_bugs.py"
BUG_REPORT_FILE = Path("bug_report.json")
USE_XFAIL = os.getenv("BUG_TESTS_XFAIL", "1") == "1"

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

ERROR_TEXT_MARKERS = (
    "internal server error",
    "traceback (most recent call last)",
    "cannot get /",
    "application error",
    "unhandled runtime error",
    "502 bad gateway",
    "503 service unavailable",
)

STATIC_RESOURCE_TYPES = ("script", "stylesheet", "image", "font")
NON_LABELLED_INPUT_TYPES = ("hidden", "submit", "button", "reset", "image")


def _key(url):
    return (url or "").lower().rstrip("/")


def is_bad_response(response):
    """5xx and 404s are bugs; other 4xx on XHR (401/403/422...) are often expected."""
    status = response.get("status", 0)
    return (
        status >= 500
        or status == 404
        or (response.get("type") in STATIC_RESOURCE_TYPES and status >= 400)
    )


# ============================================================
# DETECTION
# ============================================================

def detect_bugs(website_data):
    """Return a list of bug dicts found in the explorer's website_data."""
    pages = website_data.get("pages", [])

    linked_from = defaultdict(list)
    for page in pages:
        for link in page.get("links", []):
            target = _key(link.get("href", ""))
            if page.get("url") and page["url"] not in linked_from[target]:
                linked_from[target].append(page["url"])

    findings = {}

    def add(category, severity, page, title, evidence, expected):
        key = (category, _key(page["url"]), page.get("stage"))
        if key in findings:
            return
        
        findings[key] = {
            "category": category,
            "severity": severity,
            "title": title,
            "url": page["url"],
            "stage": page.get("stage", "public"),
            "requires_auth": page.get("stage") == "authenticated",
            "evidence": [
                str(item)[:300] for item in evidence[:4]
            ],
            "expected": expected,

            # Initial classification: a detector finding is not
            # automatically a confirmed application defect.
            "status": "Needs Review",
            "confidence": "Unverified",
            "verification_attempts": 0,
            "recommended_action": (
                "Reproduce the issue and collect fresh evidence "
                "before confirming severity."
            ),
        }


    for page in pages:
        url = page.get("url", "")
        if not url:
            continue

        status = page.get("http_status")
        diag = page.get("diagnostics", {})
        healthy = not status or status < 400

        # --- the page itself fails to load ---------------------------------
        if status and status >= 400:
            evidence = [f"HTTP {status} when opening {url}"]
            sources = [
                s for s in linked_from.get(_key(url), [])
                if _key(s) != _key(url)
            ][:3]
            if sources:
                evidence.append("Linked from: " + ", ".join(sources))
            add("broken_page", "Critical" if status >= 500 else "High", page,
                f"Page returns HTTP {status}", evidence,
                "The page loads with a successful (<400) status")
            continue  # error pages naturally lack titles, headings, etc.

        # --- runtime errors -------------------------------------------------
        if diag.get("page_errors"):
            add("javascript_error", "High", page,
                "Uncaught JavaScript error on page load",
                diag["page_errors"], "No uncaught JavaScript errors on load")

        if diag.get("console_errors"):
            add("console_error", "Medium", page,
                "Errors logged to the browser console",
                diag["console_errors"], "No console errors on load")

        bad = [
            r for r in diag.get("bad_responses", [])
            if is_bad_response(r)
            and not (r.get("type") == "document" and _key(r["url"]) == _key(url))
        ]
        if bad:
            severity = "High" if any(r["status"] >= 500 for r in bad) else "Medium"
            add("failed_request", severity, page,
                "Requests made by the page fail",
                [f"HTTP {r['status']} {r['url']} ({r['type']})" for r in bad],
                "All same-site requests succeed")

        if diag.get("failed_requests"):
            add("network_failure", "Medium", page,
                "Network requests fail outright",
                [f"{r['url']} -> {r['failure']}" for r in diag["failed_requests"]],
                "No same-site requests fail at the network level")

        # --- visible server errors on a 200 page ---------------------------
        text = (page.get("text") or "").lower()
        found = [m for m in ERROR_TEXT_MARKERS if m in text]
        if found:
            add("error_text_visible", "High", page,
                "Server/application error text is visible to users",
                [f"Page text contains: {m!r}" for m in found],
                "No raw error messages are shown to users")

        # --- basic quality / accessibility ---------------------------------
        if not (page.get("title") or "").strip():
            add("missing_title", "Low", page, "Page has no <title>",
                ["document.title is empty"], "Page has a descriptive title")

        if page.get("h1_count", 0) == 0 and text.strip():
            add("missing_h1", "Low", page, "Page has no <h1> heading",
                ["No <h1> element found"], "Page has a main heading")

        if page.get("images_missing_alt", 0) > 0:
            add("images_missing_alt", "Low", page,
                "Images without alt attribute",
                [f"{page['images_missing_alt']} <img> element(s) have no alt"],
                "Every image has an alt attribute")

        unlabeled = [
            i for i in page.get("inputs", [])
            if i.get("visible")
            and i.get("type") not in NON_LABELLED_INPUT_TYPES
            and not (i.get("label") or i.get("aria_label") or i.get("title"))
        ]
        if unlabeled:
            names = [i.get("name") or i.get("id") or i.get("type") for i in unlabeled]
            add("unlabeled_input", "Low", page,
                "Form fields without an accessible label",
                [f"Unlabelled fields: {', '.join(map(str, names))}"],
                "Every visible field has a label or aria-label")

    bugs = sorted(
        findings.values(),
        key=lambda b: (SEVERITY_ORDER[b["severity"]], b["url"], b["category"]),
    )
    for index, bug in enumerate(bugs, start=1):
        bug["id"] = f"BUG{index:03d}"
    return bugs


# ============================================================
# REPORTING
# ============================================================

def save_bug_report(bugs, website_url="", path=BUG_REPORT_FILE):
    payload = {
        "website": website_url,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "bug_count": len(bugs),
        "bugs": bugs,
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    print(f"[Bugs] Bug report saved: {Path(path).resolve()}")


def print_bug_summary(bugs):
    print("\n" + "=" * 70)
    print("                  BUGS FOUND DURING EXPLORATION")
    print("=" * 70)
    if not bugs:
        print("\nNo bugs detected by the automatic checks.")
        return
    for bug in bugs:
        print(f"\n{bug['id']} [{bug['severity']}] {bug['title']}")
        print(f"  Page: {bug['url']}  ({bug['stage']})")
        for line in bug["evidence"][:2]:
            print(f"  - {line}")


# ============================================================
# BUG TEST GENERATION (fixed templates, no LLM involved)
# ============================================================

TEST_FILE_HEADER = '''"""Auto-generated regression tests for bugs found during exploration.

Each test asserts the CORRECT behaviour, so it fails while the bug exists.
XFAIL = bug still present. XPASS = bug fixed -> remove the xfail marker.
Generated by bug_detector.py - regenerated on every run.
"""
from urllib.parse import urlparse

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

STATIC_RESOURCE_TYPES = ("script", "stylesheet", "image", "font")
ERROR_TEXT_MARKERS = __MARKERS__


def _same_host(url, host):
    return (urlparse(url).hostname or "").lower() == host


def _is_bad(response):
    status = response.status
    return (
        status >= 500
        or status == 404
        or (response.request.resource_type in STATIC_RESOURCE_TYPES and status >= 400)
    )


def _settle(page):
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PlaywrightTimeoutError:
        pass
'''

TEST_BODIES = {
    "broken_page": '''    response = __FX__.goto(__URL__, wait_until="domcontentloaded")
    assert response is not None and response.status < 400, "Page did not load successfully"
''',
    "javascript_error": '''    errors = []
    __FX__.on("pageerror", lambda exc: errors.append(str(exc)))
    __FX__.goto(__URL__, wait_until="domcontentloaded")
    _settle(__FX__)
    assert not errors, f"Uncaught JavaScript errors: {errors}"
''',
    "console_error": '''    errors = []
    __FX__.on(
        "console",
        lambda msg: errors.append(msg.text)
        if msg.type == "error" and not msg.text.startswith("Failed to load resource")
        else None,
    )
    __FX__.goto(__URL__, wait_until="domcontentloaded")
    _settle(__FX__)
    assert not errors, f"Console errors: {errors}"
''',
    "failed_request": '''    failed = []
    __FX__.on(
        "response",
        lambda r: failed.append((r.status, r.url))
        if _same_host(r.url, __HOST__) and _is_bad(r)
        else None,
    )
    __FX__.goto(__URL__, wait_until="domcontentloaded")
    _settle(__FX__)
    assert not failed, f"Failing requests: {failed}"
''',
    "network_failure": '''    failed = []
    __FX__.on(
        "requestfailed",
        lambda r: failed.append(r.url)
        if _same_host(r.url, __HOST__) and "ERR_ABORTED" not in str(r.failure)
        else None,
    )
    __FX__.goto(__URL__, wait_until="domcontentloaded")
    _settle(__FX__)
    assert not failed, f"Requests failed at network level: {failed}"
''',
    "error_text_visible": '''    __FX__.goto(__URL__, wait_until="domcontentloaded")
    _settle(__FX__)
    body = __FX__.locator("body").inner_text().lower()
    shown = [m for m in ERROR_TEXT_MARKERS if m in body]
    assert not shown, f"Error text visible to users: {shown}"
''',
    "missing_title": '''    __FX__.goto(__URL__, wait_until="domcontentloaded")
    assert __FX__.title().strip(), "Page has no <title>"
''',
    "missing_h1": '''    __FX__.goto(__URL__, wait_until="domcontentloaded")
    _settle(__FX__)
    assert __FX__.locator("h1").count() >= 1, "Page has no <h1>"
''',
    "images_missing_alt": '''    __FX__.goto(__URL__, wait_until="domcontentloaded")
    _settle(__FX__)
    assert __FX__.locator("img:not([alt])").count() == 0, "Images without alt text"
''',
    "unlabeled_input": '''    __FX__.goto(__URL__, wait_until="domcontentloaded")
    _settle(__FX__)
    unlabeled = __FX__.evaluate(
        """() => Array.from(document.querySelectorAll(
            'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=image]), textarea, select'
        )).filter((el) => {
            const box = el.getBoundingClientRect();
            return box.width > 0 && box.height > 0 &&
                !(el.labels && el.labels.length) &&
                !el.getAttribute('aria-label') &&
                !el.getAttribute('aria-labelledby') &&
                !el.getAttribute('title');
        }).map((el) => el.name || el.id || el.type)"""
    )
    assert not unlabeled, f"Fields without an accessible label: {unlabeled}"
''',
}


def _render_test(bug):
    fixture = "auth_page" if bug["requires_auth"] else "page"
    body = (
        TEST_BODIES[bug["category"]]
        .replace("__FX__", fixture)
        .replace("__URL__", repr(bug["url"]))
        .replace("__HOST__", repr((urlparse(bug["url"]).hostname or "").lower()))
    )
    decorators = "@pytest.mark.bug\n"
    if USE_XFAIL:
        reason = f"{bug['id']}: {bug['title']}"
        decorators += f"@pytest.mark.xfail(strict=False, reason={reason!r})\n"
    name = f"test_{bug['id'].lower()}_{bug['category']}"
    return f"{decorators}def {name}({fixture}):\n{body}"


def generate_bug_tests(bugs, path=BUG_TEST_FILE):
    """Write tests/test_bugs.py. Returns the path, or None when there are no bugs."""
    path = Path(path)
    if not bugs:
        print("[Bugs] No bugs found, so no bug tests were generated.")
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    header = TEST_FILE_HEADER.replace("__MARKERS__", repr(ERROR_TEXT_MARKERS))
    tests = [_render_test(b) for b in bugs if b["category"] in TEST_BODIES]
    path.write_text(header + "\n\n" + "\n\n".join(tests) + "\n", encoding="utf-8")
    print(f"[Bugs] Generated {len(tests)} bug test(s): {path}")
    return str(path)
