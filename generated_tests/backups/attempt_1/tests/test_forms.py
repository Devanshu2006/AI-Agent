"""Form behaviour tests (expected vs actual) - GENERATED, do not edit by hand.

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
VALIDATION_BLOCKED = 'validation_blocked'
SUBMITTED = 'submitted'
SERVER_ERROR = 'server_error'
NO_EFFECT = 'no_effect'
NO_ERROR = 'no_server_error'
ERRORISH_RE = re.compile("(invalid|required|incorrect|wrong|failed|failure|must |please (enter|provide|fill|select|check)|cannot|can't|can not|not valid|not allowed|too (short|long)|already (exists|registered|taken|in use)|unauthori[sz]ed|denied|error|try again|doesn't match|does not match)", re.I)
SUCCESSISH_RE = re.compile('(success|thank|submitted|welcome|saved|created|sent|confirmed|registered|received|subscribed|logged in)', re.I)
TELEMETRY_RE = re.compile('(/collect|/analytics|/beacon|/track|/log\\b|/logs\\b|/telemetry|/metrics|/sentry|/gtm|/g/collect|/pixel|/events?$)', re.I)
ERROR_TEXT_MARKERS = ('internal server error', 'traceback (most recent call last)', 'cannot get /', 'application error', 'unhandled runtime error', '502 bad gateway', '503 service unavailable')
SNAPSHOT_JS = '\n(idx) => {\n  const clean = (s) => (s || \'\').replace(/\\s+/g, \' \').trim();\n  const vis = (el) => {\n    const r = el.getBoundingClientRect(), s = getComputedStyle(el);\n    return r.width > 0 && r.height > 0 && s.visibility !== \'hidden\' && s.display !== \'none\';\n  };\n  const scope = document.querySelector(\'[data-qa-form="\' + idx + \'"]\');\n  const root = scope || document.body;\n  const invalid = scope && scope.tagName === \'FORM\'\n    ? Array.from(scope.querySelectorAll(\':invalid\'))\n        .filter((e) => ![\'FORM\', \'FIELDSET\'].includes(e.tagName))\n        .slice(0, 15).map((e) => ({ name: e.name || e.id || \'\', message: e.validationMessage || \'\' }))\n    : [];\n  const ariaInvalid = Array.from(root.querySelectorAll(\'[aria-invalid="true"]\')).filter(vis).length;\n  const ALERT = \'[role=alert],[role=status],[aria-live=assertive],[aria-live=polite],\' +\n    \'.error,.errors,.error-message,.invalid-feedback,.field-error,.form-error,.toast,\' +\n    \'.notification,[class*=error i],[class*=invalid i],[class*=toast i],[class*=alert i],\' +\n    \'[class*=danger i],[class*=success i],[data-error]\';\n  const alerts = [];\n  document.querySelectorAll(ALERT).forEach((e) => {\n    if (!vis(e)) return;\n    const t = clean(e.innerText).slice(0, 200);\n    if (t && !alerts.includes(t)) alerts.push(t);\n  });\n  const lines = ((document.body && document.body.innerText) || \'\').split(\'\\n\')\n    .map(clean).filter(Boolean).slice(0, 300).map((l) => l.slice(0, 200));\n  const sub = document.querySelector(\'[data-qa-submit="\' + idx + \'"]\');\n  const fieldCount = Array.from(document.querySelectorAll(\'input:not([type=hidden]),textarea,select\')).filter(vis).length;\n  return {\n    invalid, aria_invalid: ariaInvalid, alerts: alerts.slice(0, 10), lines,\n    submit_disabled: !!(sub && (sub.disabled || sub.getAttribute(\'aria-disabled\') === \'true\')),\n    form_present: !!scope, no_validate: !!(scope && scope.noValidate), field_count: fieldCount,\n    url: location.href,\n  };\n}\n'
STAMP_JS = """(a) => {
  const forms = document.querySelectorAll('form');
  document.querySelectorAll('[data-qa-form]').forEach((e) => e.removeAttribute('data-qa-form'));
  const el = a.pseudo ? document.body : forms[a.idx];
  if (el) el.setAttribute('data-qa-form', String(a.idx));
  return !!el;
}"""


def _strip_hash(url):
    return (url or "").split("#", 1)[0].rstrip("/")


def _classify(obs):
    """Turn raw observations into one outcome. Returns (outcome, signals)."""
    signals = []
    if obs["server_errors"] or obs["error_text"]:
        return SERVER_ERROR, ["5xx response" if obs["server_errors"] else "error page text"]
 
    mutating = obs["mutating"]
    messages = list(obs["new_alerts"]) + list(obs["new_text"])
    errorish = any(ERRORISH_RE.search(m) for m in messages)
    successish = any(SUCCESSISH_RE.search(m) for m in messages)
 
    if mutating:
        if any(r["aborted"] for r in mutating):
            return SUBMITTED, ["request attempted (aborted by agent for safety)"]
        statuses = [r["status"] for r in mutating if r["status"] is not None]
        if any(400 <= s < 500 for s in statuses):
            return VALIDATION_BLOCKED, [f"server answered {sorted(set(statuses))}"]
        if errorish and not successish:
            return VALIDATION_BLOCKED, ["2xx answer but an error message is shown"]
        return SUBMITTED, [f"server answered {sorted(set(statuses))}"]
 
    if _strip_hash(obs["url_after"]) != _strip_hash(obs["url_before"]):
        return SUBMITTED, ["page navigated"]
    if obs["native_blocked"]:
        return VALIDATION_BLOCKED, ["browser validation blocked the submit"]
    if obs["submit_disabled"]:
        return VALIDATION_BLOCKED, ["submit button is disabled"]
    if obs["aria_invalid"]:
        return VALIDATION_BLOCKED, ["fields marked aria-invalid"]
    if errorish and not successish:
        return VALIDATION_BLOCKED, ["error message appeared"]
    if successish:
        return SUBMITTED, ["success message appeared"]
    if obs["form_gone"]:
        return SUBMITTED, ["form disappeared (in-page success)"]
    if obs["new_alerts"]:
        return VALIDATION_BLOCKED, ["alert-like element appeared"]
    return NO_EFFECT, signals


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


def test_form_01_c01_empty_submit(page):
    """data_form form @ https://www.myntra.com/ - Submit with every field empty - must not crash the server"""
    stamp = _open(page, 'https://www.myntra.com/')
    scope = page.locator('body')
    pass  # empty submit: nothing to fill
    obs = _submit_and_observe(
        page, 0, True, scope.get_by_role('button', name='1', exact=True).first,
        True, 'www.myntra.com', '')
    assert obs["outcome"] != SERVER_ERROR, (
        "server error: " + "; ".join(obs["signals"]))


def test_form_01_c02_valid_submit(page):
    """data_form form @ https://www.myntra.com/ - Submit with valid data in every field - the app must accept it"""
    stamp = _open(page, 'https://www.myntra.com/')
    scope = page.locator('body')
    _fill(scope.get_by_placeholder('Search for products, brands and more', exact=True).first, 'text', _v('test', stamp), False)
    obs = _submit_and_observe(
        page, 0, True, scope.get_by_role('button', name='1', exact=True).first,
        True, 'www.myntra.com', '')
    assert obs["outcome"] == 'submitted', (
        "expected submitted but got " + obs["outcome"] + ": " + "; ".join(obs["signals"]))


def test_form_01_c03_long_value(page):
    """data_form form @ https://www.myntra.com/ - 300-character values in text fields must not crash the server"""
    stamp = _open(page, 'https://www.myntra.com/')
    scope = page.locator('body')
    _fill(scope.get_by_placeholder('Search for products, brands and more', exact=True).first, 'text', _v('A' * 300, stamp), False)
    obs = _submit_and_observe(
        page, 0, True, scope.get_by_role('button', name='1', exact=True).first,
        True, 'www.myntra.com', '')
    assert obs["outcome"] != SERVER_ERROR, (
        "server error: " + "; ".join(obs["signals"]))

