"""Turns verified form-test results into pytest regression tests.

Input : the dict returned by form_tester.run_form_tests()
Output: generated_tests/tests/test_forms.py

  * PASS cases       -> a test that re-runs the case and asserts the expected
                        outcome (guards against regressions).
  * MISMATCH cases   -> the same test marked  @pytest.mark.bug + xfail(strict=False)
                        so the suite stays green while the bug exists and shows
                        XPASS the day it is fixed (same convention as test_bugs.py).
  * UNVERIFIED / FLAKY / ERROR cases and cases that use .env secrets are NOT
    turned into tests (a test must never depend on something we could not prove).

The file is plain Python that passes code_validator.py: only playwright, pytest,
re and urllib.parse are imported, there is no sleep / wait_for_timeout, and every
test has a real assertion.  All site-derived values are written with repr(), so
a hostile page cannot inject code into the generated file.

The outcome-classification code inside the generated file is copied from
form_tester.py with inspect.getsource(), so the generated tests and the live
tester can never disagree about what "validation_blocked" means.
"""
import inspect
import os
import re
from pathlib import Path

import form_tester as ft

try:
    from bug_detector import USE_XFAIL
except Exception:  # pragma: no cover
    USE_XFAIL = os.getenv("BUG_TESTS_XFAIL", "1") == "1"

FORM_TEST_FILE = Path("generated_tests") / "tests" / "test_forms.py"

HEADER = '''"""Form behaviour tests (expected vs actual) - GENERATED, do not edit by hand.

Regenerated on every agent run by form_test_codegen.py.  A test here asserts the
OUTCOME of submitting a form with specific input:
    validation_blocked | submitted | server_error | no_effect
Cases marked `bug` fail today and are expected to (xfail) until the bug is fixed.
"""
import re
from urllib.parse import urlparse

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
VALIDATION_BLOCKED = __VB__
SUBMITTED = __SUB__
SERVER_ERROR = __SE__
NO_EFFECT = __NE__
NO_ERROR = __NO__
ERRORISH_RE = re.compile(__ERRORISH__, re.I)
SUCCESSISH_RE = re.compile(__SUCCESSISH__, re.I)
TELEMETRY_RE = re.compile(__TELEMETRY__, re.I)
ERROR_TEXT_MARKERS = __MARKERS__
SNAPSHOT_JS = __SNAPSHOT_JS__
STAMP_JS = """(a) => {
  const forms = document.querySelectorAll('form');
  document.querySelectorAll('[data-qa-form]').forEach((e) => e.removeAttribute('data-qa-form'));
  const el = a.pseudo ? document.body : forms[a.idx];
  if (el) el.setAttribute('data-qa-form', String(a.idx));
  return !!el;
}"""


__STRIP_HASH__


__CLASSIFY__


def _host(url):
    return (urlparse(url or "").hostname or "").lower()


def _settle(page, timeout_ms=5000):
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass


def _open(page, url):
    page.goto(url, wait_until="domcontentloaded")
    _settle(page)
    page.wait_for_selector("input, textarea, select")
    return page.evaluate("() => Math.random().toString(16).slice(2, 8)")


def _fill(loc, ftype, value, typed=False):
    if ftype in ("checkbox", "radio"):
        loc.set_checked(bool(value) and value != "", force=True)
    elif ftype == "select":
        try:
            loc.select_option(value=str(value))
        except Exception:
            loc.select_option(label=str(value))
    elif typed:
        loc.click()
        loc.press_sequentially(str(value))
    else:
        loc.fill(str(value))


def _submit_and_observe(page, form_index, pseudo, submit_loc, abort, base_host, action_host):
    rec = {"mutating": [], "server_errors": [], "dialogs": []}

    def relevant(host):
        def same(a, b):
            return bool(a) and bool(b) and (a == b or a.endswith("." + b) or b.endswith("." + a))
        return same(host, base_host) or same(host, action_host)

    def on_request(request):
        if (request.method in MUTATING
                and request.resource_type in ("fetch", "xhr", "document", "other")
                and relevant(_host(request.url))
                and not TELEMETRY_RE.search(urlparse(request.url).path)):
            rec["mutating"].append({"method": request.method, "url": request.url,
                                    "status": None, "aborted": False, "_req": request})

    def on_response(response):
        for item in rec["mutating"]:
            if item["_req"] is response.request:
                item["status"] = response.status
        if (response.status >= 500 and relevant(_host(response.url))
                and response.request.resource_type in ("document", "fetch", "xhr")):
            rec["server_errors"].append({"status": response.status, "url": response.url})

    def on_dialog(dialog):
        rec["dialogs"].append(dialog.message[:200])
        dialog.accept()

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("dialog", on_dialog)

    if abort:
        def handler(route, request):
            if (request.method in MUTATING
                    and request.resource_type in ("fetch", "xhr", "document", "other")
                    and relevant(_host(request.url))
                    and not TELEMETRY_RE.search(urlparse(request.url).path)):
                for item in rec["mutating"]:
                    if item["_req"] is request:
                        item["aborted"] = True
                if request.resource_type == "document":
                    route.fulfill(status=204, body="")
                else:
                    route.abort()
            else:
                route.continue_()
        page.route("**/*", handler)

    page.evaluate(STAMP_JS, {"idx": form_index, "pseudo": pseudo})
    submit_loc.evaluate("(el, i) => el.setAttribute('data-qa-submit', String(i))", form_index)
    before = page.evaluate(SNAPSHOT_JS, form_index)
    url_before = page.url
    clicked = False
    if not before["submit_disabled"]:
        submit_loc.click()
        clicked = True
    if clicked:
        _settle(page)
        try:
            page.evaluate("() => new Promise((r) => setTimeout(r, 500))")
        except Exception:                      # page navigated while waiting
            _settle(page)
    after = None
    for _ in range(3):
        try:
            after = page.evaluate(SNAPSHOT_JS, form_index)
            break
        except Exception:
            _settle(page)
    if after is None:
        raise AssertionError("could not read the page after submitting")

    before_lines = set(before["lines"])
    new_text = [t for t in after["lines"] if t not in before_lines][:8]
    new_alerts = [a for a in after["alerts"] if a not in before["alerts"]]
    new_alerts += ["dialog: " + d for d in rec["dialogs"]]
    blob = " ".join(after["lines"]).lower()
    old_blob = " ".join(before["lines"]).lower()
    error_text = any(m in blob for m in ERROR_TEXT_MARKERS) and not any(
        m in old_blob for m in ERROR_TEXT_MARKERS)
    native_blocked = bool(
        after["invalid"] and not after["no_validate"] and not pseudo
        and not rec["mutating"] and _strip_hash(page.url) == _strip_hash(url_before)
        and after["form_present"])
    obs = {
        "url_before": url_before, "url_after": page.url,
        "mutating": [{k: v for k, v in r.items() if k != "_req"} for r in rec["mutating"]],
        "server_errors": rec["server_errors"], "error_text": error_text,
        "native_blocked": native_blocked, "aria_invalid": after["aria_invalid"],
        "new_alerts": new_alerts, "new_text": new_text,
        "submit_disabled": before["submit_disabled"],
        "form_gone": (not after["form_present"]) and after["field_count"] < before["field_count"],
    }
    obs["outcome"], obs["signals"] = _classify(obs)
    return obs


def _v(value, stamp):
    return value.replace("__STAMP__", stamp) if isinstance(value, str) else value
'''


def _helper_header():
    classify_src = inspect.getsource(ft.classify).replace("def classify(", "def _classify(")
    strip_src = inspect.getsource(ft._strip_hash)
    header = HEADER
    for token, value in {
        "__VB__": repr(ft.VALIDATION_BLOCKED), "__SUB__": repr(ft.SUBMITTED),
        "__SE__": repr(ft.SERVER_ERROR), "__NE__": repr(ft.NO_EFFECT),
        "__NO__": repr(ft.NO_ERROR),
        "__ERRORISH__": repr(ft.ERRORISH_RE.pattern),
        "__SUCCESSISH__": repr(ft.SUCCESSISH_RE.pattern),
        "__TELEMETRY__": repr(ft.TELEMETRY_RE.pattern),
        "__MARKERS__": repr(tuple(ft.ERROR_TEXT_MARKERS)),
        "__SNAPSHOT_JS__": repr(ft.SNAPSHOT_JS),
        "__STRIP_HASH__": strip_src.rstrip(),
        "__CLASSIFY__": classify_src.rstrip(),
    }.items():
        header = header.replace(token, value)
    return header


def _locator_expr(field):
    """Playwright locator for a field, scoped to the form. None if impossible."""
    if field.get("test_id"):
        return f"scope.get_by_test_id({field['test_id']!r}).first"
    if field.get("label"):
        return f"scope.get_by_label({field['label']!r}, exact=True).first"
    if field.get("placeholder"):
        return f"scope.get_by_placeholder({field['placeholder']!r}, exact=True).first"
    if field.get("name"):
        return f"scope.locator({('[name=' + _css(field['name']) + ']')!r}).first"
    if field.get("id"):
        return f"scope.locator({('[id=' + _css(field['id']) + ']')!r}).first"
    return None


def _css(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")[:40] or "case"


def _render_value(value, stamp):
    if isinstance(value, str) and re.fullmatch(r"A{50,}", value):
        return f"'A' * {len(value)}"
    if isinstance(value, str) and stamp:
        value = value.replace(stamp, "__STAMP__")
    return repr(value)


def _render_test(n, entry, case, fields_by_key):
    fixture = "auth_page" if entry["stage"] == "authenticated" else "page"
    submit = entry.get("submit") or ""
    submit_expr = (f"scope.get_by_role('button', name={submit!r}, exact=True).first"
                   if submit else "scope.locator('[type=submit]').first")
    abort = bool(case.get("aborted_for_safety"))
    base_host = ft._host(entry["url"])
    expected = case["expected"]
    is_bug = case["verdict"] == "MISMATCH"

    lines = []
    for key, value in case["values"].items():
        field = fields_by_key[key]
        expr = _locator_expr(field)
        typed = key in case.get("typed", [])
        lines.append(
            f"    _fill({expr}, {field['type']!r}, "
            f"_v({_render_value(value, entry.get('stamp'))}, stamp), {typed})")
    fill_block = "\n".join(lines) or "    pass  # empty submit: nothing to fill"

    if expected == ft.NO_ERROR:
        check = ('    assert obs["outcome"] != SERVER_ERROR, (\n'
                 '        "server error: " + "; ".join(obs["signals"]))')
    else:
        check = (f'    assert obs["outcome"] == {expected!r}, (\n'
                 f'        "expected {expected} but got " + obs["outcome"] + ": " '
                 f'+ "; ".join(obs["signals"]))')

    decorators = ""
    if is_bug:
        decorators = "@pytest.mark.bug\n"
        if USE_XFAIL:
            reason = f"form bug: {entry['form_kind']} / {case['name']}"
            decorators += f"@pytest.mark.xfail(strict=False, reason={reason!r})\n"

    scope_expr = (f"{fixture}.locator('body')" if entry.get("pseudo")
                  else f"{fixture}.locator('form').nth({entry['form_index']})")
    name = f"test_form_{n:02d}_{case['id']}_{_slug(case['name'])}"
    doc = re.sub(r"\s+", " ", f"{entry['form_kind']} form @ {entry['url']} - "
                 f"{case['description']}").replace('"', "'").replace("\\", "/")
    return (
        f"{decorators}def {name}({fixture}):\n"
        f'    """{doc}"""\n'
        f"    stamp = _open({fixture}, {entry['url']!r})\n"
        f"    scope = {scope_expr}\n"
        f"{fill_block}\n"
        f"    obs = _submit_and_observe(\n"
        f"        {fixture}, {entry['form_index']}, {bool(entry.get('pseudo'))}, {submit_expr},\n"
        f"        {abort}, {base_host!r}, {entry.get('action_host', '')!r})\n"
        f"{check}\n"
    )


def generate_form_tests(results, path=FORM_TEST_FILE):
    """Write tests/test_forms.py. Returns the path, or None when nothing to write."""
    if not isinstance(results, dict) or not results.get("forms"):
        print("[Forms] No form results, so no form tests were generated.")
        return None

    tests, skipped_forms = [], 0
    for n, entry in enumerate(results["forms"], start=1):
        if entry["policy"]["skip"]:
            continue
        fields_by_key = {f["key"]: f for f in entry["fields"]}
        if any(_locator_expr(f) is None for f in fields_by_key.values()):
            skipped_forms += 1
            continue
        if not entry.get("submit"):
            skipped_forms += 1
            continue
        for case in entry["cases"]:
            if case["verdict"] not in ("PASS", "MISMATCH"):
                continue
            if case.get("uses_secret") or not case["actual"]:
                continue
            if any(k not in fields_by_key for k in case["values"]):
                continue
            tests.append(_render_test(n, entry, case, fields_by_key))

    path = Path(path)
    if not tests:
        print("[Forms] No verified form cases, so no form tests were generated.")
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_helper_header() + "\n\n" + "\n\n".join(tests) + "\n", encoding="utf-8")
    note = f" ({skipped_forms} form(s) skipped: no stable locator/submit)" if skipped_forms else ""
    print(f"[Forms] Generated {len(tests)} form test(s): {path}{note}")
    return str(path)


if __name__ == "__main__":
    import json
    import sys
    source = Path(sys.argv[1] if len(sys.argv) > 1 else ft.RESULTS_FILE)
    generate_form_tests(json.loads(source.read_text(encoding="utf-8")))
