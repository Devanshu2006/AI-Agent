
"""Flow engine: runs a user journey (search -> open product -> add to bag ...).
 
A flow is plain data - a list of steps; each step has an ACTION and CHECKS
(expected outcomes).  Elements are described by INTENT ("the search box",
"the first product", "the cart link") and found at run time by in-page
heuristics, so the same flow works on many shops without per-site selectors.
 
    flow = {
      "id": "search_valid", "start_url": "https://shop.example/",
      "gates": {"cart": False},
      "steps": [
        {"action": "goto"},
        {"action": "search", "value": "shirt",
         "checks": [{"type": "results_nonempty"}]},
        {"action": "click", "target": {"kind": "product_link", "index": 0},
         "checks": [{"type": "product_page"}]},
      ]}
    result = run_flow(page, flow)       # -> {"verdict": "PASS" | "FAIL" | ...}
 
This module is DELIBERATELY self-contained (only re, urllib.parse, playwright):
flow_test_codegen.py copies its source verbatim into the generated
tests/test_flows.py, so generated tests and the live tester can never disagree.
 
SAFETY: the engine never clicks anything that looks like checkout / pay / buy /
delete / logout (DANGER_RE) and never types anything except search terms.
Clicking "add to cart" is only possible when flow["gates"]["cart"] is True.
"""
import re
from urllib.parse import urlparse
 
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
 
DANGER_RE = re.compile(
    r"(check ?out|buy ?now|\bpay\b|payment|place (an? )?order|confirm order|"
    r"proceed to (pay|buy)|delete|remove account|log ?out|sign ?out|donat|"
    r"transfer|withdraw|unsubscribe|cancel (order|subscription))", re.I)
EMPTY_RE = re.compile(
    r"(no (results|products|items|matches|listings)( found)?|0 (results|items|products)|"
    r"nothing (found|matched)|couldn'?t find|could not find|did not match|"
    r"no matching|not found|try (a )?different|no products|no exact matches|"
    r"sorry,? we (have|found) no)", re.I)
# Checks that rest on heuristics (wording, layout, ordering). Failing one means
# "a human should look" (verdict REVIEW), never "confirmed bug".
SOFT_CHECKS = ("results_empty_or_message", "has_heading", "product_page",
               "list_changed", "text_visible", "no_error_text")
LOGIN_HINT_RE = re.compile(
    r"(log ?in|sign ?in|sign ?up|register|mobile number|phone number|e-?mail|"
    r"password|otp|continue with)", re.I)
LOGIN_URL_RE = re.compile(r"(log-?in|sign-?in|signin|auth|register|sign-?up)", re.I)
CART_TOAST_RE = re.compile(
    r"(added to (your )?(cart|bag|basket)|go to (cart|bag|basket)|"
    r"view (cart|bag|basket)|item added|added successfully)", re.I)
CART_URL_RE = re.compile(r"(cart|bag|basket|trolley)", re.I)
ERROR_MARKERS = (
    "internal server error", "traceback (most recent call last)", "cannot get /",
    "application error", "unhandled runtime error", "502 bad gateway",
    "503 service unavailable", "500 internal", "something went wrong",
)
TELEMETRY_RE = re.compile(
    r"(/collect|/analytics|/beacon|/track|/log\b|/logs\b|/telemetry|/metrics|"
    r"/sentry|/gtm|/pixel|/events?$)", re.I)
AUTH_PATTERNS = {
    "cart": r"\b(cart|bag|basket|trolley)\b",
    "wishlist": r"(wish ?list|favou?rites?|saved items)",
    "orders": r"(my[ -]?orders|track[ -]?orders?|order history|/orders)",
    "account": r"(my account|\bprofile\b|\baccount\b)",
}
ACTIONS = ("goto", "search", "click", "choose_sort", "choose_variant", "back", "observe")
TARGET_KINDS = ("nav_link", "product_link", "cart_link", "auth_link",
                "add_to_cart", "link_text")
CHECK_TYPES = (
    "no_server_error", "no_http_error", "not_blank", "url_changed", "url_same_site",
    "url_matches", "results_nonempty", "results_empty_or_message", "list_changed",
    "has_heading", "product_page", "add_to_cart_present", "cart_changed",
    "auth_gate_or_page", "text_visible", "no_error_text",
)
POLLABLE = ("results_nonempty", "results_empty_or_message", "list_changed",
            "cart_changed", "product_page", "text_visible", "has_heading")
 
# ---------------------------------------------------------------- in-page JS
_CARDS_JS = r"""
const price = /(\u20b9|\$|\u20ac|\u00a3|\brs\.?)\s?\d/i;
const cards = () => {
  const out = [], seen = new Set();
  document.querySelectorAll('a[href]').forEach((el) => {
    if (!vis(el) || inChrome(el) || inFooter(el)) return;
    if (!el.querySelector('img, picture')) return;
    let u; try { u = new URL(el.href, location.href); } catch (e) { return; }
    if (u.origin !== location.origin) return;
    const holder = el.closest('li, article, [class*=card i], [class*=product i], [class*=item i]') || el.parentElement;
    const text = clean((holder && holder.innerText) || el.innerText);
    const looks = price.test(text) || /(product|\/p\/|\/item|\/dp\/|\/pd\/|-p-|\d{5,})/i.test(u.pathname);
    if (!looks) return;
    const key = u.pathname + u.search;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ el, href: u.href, text: text.slice(0, 80) });
  });
  return out;
};
"""
 
_COMMON_JS = r"""
const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
const vis = (el) => {
  const r = el.getBoundingClientRect(), s = getComputedStyle(el);
  return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
};
const inChrome = (el) => !!el.closest('header, nav, [role=banner], [role=navigation]');
const inFooter = (el) => !!el.closest('footer, [role=contentinfo]');
const txt = (el) => clean(el.innerText) || clean(el.getAttribute('aria-label')) ||
  clean(el.getAttribute('title')) || clean(el.getAttribute('value')) || clean(el.getAttribute('alt'));
"""
 
RESOLVE_JS = ("(a) => {" + _COMMON_JS + _CARDS_JS + r"""
  const danger = new RegExp(a.danger, 'i');
  const none = { found: false };
  const mark = (el) => {
    document.querySelectorAll('[data-qa-flow]').forEach((e) => e.removeAttribute('data-qa-flow'));
    el.setAttribute('data-qa-flow', '1');
    return { found: true, text: txt(el).slice(0, 80), href: el.href || '',
             tag: el.tagName.toLowerCase(), target: el.getAttribute('target') || '',
             disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true' };
  };
  const SKIPNAV = /(cart|bag|basket|wish ?list|log ?in|sign ?(in|up)|account|orders?|profile|help|track|download|app\b)/i;
  const navItems = () => {
    const seen = new Set(), items = [];
    document.querySelectorAll('header a[href], nav a[href], [role=navigation] a[href], [role=banner] a[href]').forEach((el) => {
      if (!vis(el)) return;
      const t = txt(el);
      if (!t || t.length > 30) return;
      let u; try { u = new URL(el.href, location.href); } catch (e) { return; }
      if (u.origin !== location.origin) return;
      if (u.pathname === '/' || (u.pathname === location.pathname && !u.search)) return;
      if (danger.test(t) || SKIPNAV.test(t + ' ' + u.pathname)) return;
      const key = u.pathname + u.search;
      if (seen.has(key)) return;
      seen.add(key);
      items.push(el);
    });
    return items;
  };
  switch (a.kind) {
    case 'search_box': {
      const sel = 'input[type=search], input[role=searchbox], input[name=q], input[name=query], input[name=search], input[name=keyword], input[name=s], input[name=k]';
      const score = (el) => {
        const h = (el.name + ' ' + el.id + ' ' + el.placeholder + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('role') || '')).toLowerCase();
        let s = 0;
        if (/search/.test(h)) s += 3;
        if (el.matches(sel)) s += 2;
        if (inChrome(el)) s += 1;
        return s;
      };
      const c = Array.from(document.querySelectorAll('input[type=text], input:not([type]), ' + sel))
        .filter((el) => vis(el) && !el.disabled && !el.readOnly)
        .map((el) => [score(el), el]).filter((x) => x[0] >= 2).sort((x, y) => y[0] - x[0]);
      return c.length ? mark(c[0][1]) : none;
    }
    case 'search_opener': {
      const c = Array.from(document.querySelectorAll('button, a, [role=button]')).filter(vis).filter((el) =>
        /search/i.test((el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '') + ' ' + clean(el.innerText)) &&
        !danger.test(txt(el)));
      return c.length ? mark(c[0]) : none;
    }
    case 'nav_list': return { found: true, texts: navItems().map((e) => txt(e)) };
    case 'nav_link': {
      const items = navItems();
      let idx = a.index || 0;
      if (a.text) {
        const j = items.findIndex((e) => txt(e).toLowerCase() === String(a.text).toLowerCase());
        if (j >= 0) idx = j;
      }
      if (idx >= items.length) return { found: false, count: items.length };
      const r = mark(items[idx]); r.count = items.length; return r;
    }
    case 'product_cards': {
      const c = cards();
      return { found: true, count: c.length, sig: c.slice(0, 12).map((x) => x.href).join('|'),
               names: c.slice(0, 8).map((x) => x.text) };
    }
    case 'product_link': {
      const c = cards();
      return (a.index || 0) < c.length ? mark(c[a.index || 0].el) : none;
    }
    case 'sort_native': {
      for (const s of Array.from(document.querySelectorAll('select')).filter(vis)) {
        const opts = Array.from(s.options).map((o) => clean(o.text));
        if (opts.length < 2 || !opts.some((t) => /(price|relevan|popular|newest|latest|low|high|rating|discount)/i.test(t))) continue;
        let idx = opts.findIndex((t, i) => i !== s.selectedIndex && /price.*low|low.*high|low to high/i.test(t));
        if (idx < 0) idx = opts.findIndex((t, i) => i !== s.selectedIndex && /(price|newest|latest|popular|rating|discount|high)/i.test(t));
        if (idx < 0) idx = s.selectedIndex === 0 ? 1 : 0;
        const r = mark(s); r.option_index = idx; r.option_text = opts[idx]; return r;
      }
      return none;
    }
    case 'sort_opener': {
      const c = Array.from(document.querySelectorAll('button, [role=button], a, div, span')).filter(vis).filter((el) => {
        const t = clean(el.innerText);
        return t.length <= 30 && /^sort( by)?\b/i.test(t) && !inFooter(el);
      }).sort((x, y) => clean(x.innerText).length - clean(y.innerText).length);
      return c.length ? mark(c[0]) : none;
    }
    case 'sort_option': {
      const c = Array.from(document.querySelectorAll('li, a, button, label, div, span, [role=option], [role=menuitem]')).filter(vis).filter((el) => {
        const t = clean(el.innerText);
        return t.length <= 40 && /price.*low|low.*high|low to high/i.test(t);
      }).sort((x, y) => clean(x.innerText).length - clean(y.innerText).length);
      return c.length ? mark(c[0]) : none;
    }
    case 'add_to_cart': {
      const c = Array.from(document.querySelectorAll('button, a, [role=button], input[type=submit], input[type=button]')).filter(vis).filter((el) => {
        const t = txt(el);
        return t.length <= 40 && /(^add( item)?$|add (item )?to (cart|bag|basket|trolley))/i.test(t) &&
          !/(buy|check ?out)/i.test(t);
      });
      return c.length ? mark(c[0]) : none;
    }
    case 'variant': {
      const SIZE = /^(xxs|xs|s|m|l|xl|xxl|xxxl|2xl|3xl|\d{1,2}(\.\d)?|free size|one size)$/i;
      for (const s of Array.from(document.querySelectorAll('select')).filter(vis)) {
        if (inChrome(s)) continue;
        const opts = Array.from(s.options);
        const lab = (s.name + ' ' + s.id + ' ' + ((s.labels && s.labels[0]) ? s.labels[0].innerText : '')).toLowerCase();
        if (!/(size|variant|colou?r|option)/.test(lab) && !opts.some((o) => SIZE.test(clean(o.text)))) continue;
        const idx = opts.findIndex((o) => o.value !== '' && !o.disabled);
        if (idx >= 0) { const r = mark(s); r.option_index = idx; r.select = true; return r; }
      }
      const c = Array.from(document.querySelectorAll('button, label, li, a, span, div, [role=button], [role=radio]')).filter((el) => {
        if (!vis(el) || inChrome(el) || inFooter(el)) return false;
        const t = clean(el.innerText);
        if (!t || t.length > 12 || !SIZE.test(t)) return false;
        const cls = (typeof el.className === 'string' ? el.className : '').toLowerCase();
        return !(el.disabled || el.getAttribute('aria-disabled') === 'true' || /(disabled|unavailable|sold|out-of-stock|oos)/.test(cls));
      });
      return c.length ? mark(c[0]) : none;
    }
    case 'cart_link': {
      const c = Array.from(document.querySelectorAll('a[href], button, [role=button], [role=link]')).filter(vis).filter((el) => {
        let p = ''; try { p = new URL(el.href, location.href).pathname; } catch (e) {}
        return /\b(cart|bag|basket|trolley)\b/i.test(txt(el) + ' ' + (el.getAttribute('aria-label') || '') + ' ' + p) &&
          !danger.test(txt(el)) && !/add (item )?to/i.test(txt(el));
      }).sort((x, y) => (inChrome(y) ? 1 : 0) - (inChrome(x) ? 1 : 0));
      return c.length ? mark(c[0]) : none;
    }
    case 'auth_link': {
      const re = new RegExp(a.pattern, 'i');
      const c = Array.from(document.querySelectorAll('a[href], button, [role=button], [role=link]')).filter(vis).filter((el) => {
        const t = txt(el);
        if (t.length > 40 || danger.test(t) || /add (item )?to/i.test(t)) return false;
        let p = ''; try { p = new URL(el.href, location.href).pathname; } catch (e) {}
        if ((el.getAttribute('href') || '').startsWith('#')) return false;
        return re.test(t + ' ' + (el.getAttribute('aria-label') || '') + ' ' + p);
      }).sort((x, y) => (inChrome(y) ? 1 : 0) - (inChrome(x) ? 1 : 0));
      return c.length ? mark(c[0]) : none;
    }
    case 'link_text': {
      const want = String(a.text || '').toLowerCase();
      const c = Array.from(document.querySelectorAll('a[href], button, [role=button]')).filter(vis)
        .filter((el) => txt(el).toLowerCase() === want && !danger.test(txt(el)));
      return c.length ? mark(c[0]) : none;
    }
  }
  return none;
}""")
 
STATE_JS = ("() => {" + _COMMON_JS + _CARDS_JS + r"""
  const body = clean(document.body ? document.body.innerText : '').replace(/[\u2018\u2019\u02bc]/g, "'");
  const c = cards();
  const cartEls = Array.from(document.querySelectorAll('[class*=cart i],[class*=bag i],[class*=basket i],[aria-label*=cart i],[aria-label*=bag i],[data-testid*=cart i],[id*=cart i],[id*=bag i]')).filter(vis);
  let cart = null;
  cartEls.forEach((e) => {
    const m = clean(e.innerText).match(/\b(\d{1,3})\b/);
    if (m) cart = Math.max(cart === null ? 0 : cart, parseInt(m[1], 10));
  });
  const imgs = Array.from(document.querySelectorAll('img')).filter((i) => vis(i) && i.getBoundingClientRect().width > 80);
  let bgImage = false;
  const boxes = document.querySelectorAll('div, span, a, figure, li, section, picture, video');
  for (let i = 0; i < boxes.length && i < 900 && !bgImage; i++) {
    const r = boxes[i].getBoundingClientRect();
    if (r.width < 120 || r.height < 120) continue;
    if (boxes[i].tagName === 'VIDEO' || /url\(/.test(getComputedStyle(boxes[i]).backgroundImage || '')) bgImage = true;
  }
  return {
    url: location.href, title: document.title || '', text_len: body.length, text: body.slice(0, 8000),
    h1: Array.from(document.querySelectorAll('h1')).filter(vis).map((e) => clean(e.innerText)).filter(Boolean).slice(0, 3),
    headings: Array.from(document.querySelectorAll('h1, h2')).filter(vis).map((e) => clean(e.innerText)).filter(Boolean).slice(0, 5),
    has_price: price.test(body), has_image: imgs.length > 0 || bgImage,
    card_count: c.length, card_sig: c.slice(0, 12).map((x) => x.href).join('|'),
    card_names: c.slice(0, 6).map((x) => x.text), cart_count: cart,
    has_input: Array.from(document.querySelectorAll('input:not([type=hidden])')).some(vis),
  };
}""")
 
DISMISS_JS = ("() => {" + _COMMON_JS + r"""
  const scopes = document.querySelectorAll('[role=dialog], [class*=cookie i], [id*=cookie i], [class*=consent i], [id*=consent i], [class*=gdpr i]');
  const OK = /^(accept( all)?( cookies)?|allow( all)?( cookies)?|i agree|agree|got it|ok|okay|no,? thanks|not now|maybe later|dismiss|close|\u00d7|\u2715|x)$/i;
  for (const sc of scopes) {
    if (!vis(sc)) continue;
    for (const b of sc.querySelectorAll('button, [role=button], a, input[type=button]')) {
      if (!vis(b)) continue;
      const t = clean(b.innerText) || clean(b.getAttribute('aria-label')) || clean(b.value);
      if (OK.test(t)) { b.click(); return t; }
    }
  }
  return '';
}""")
 
 
# ------------------------------------------------------------------ helpers
def _host(url):
    return (urlparse(url or "").hostname or "").lower()
 
 
def _same_site(a, b):
    return bool(a) and bool(b) and (a == b or a.endswith("." + b) or b.endswith("." + a))
 
 
def _strip(url):
    return (url or "").split("#", 1)[0].rstrip("/")
 
 
def _settle(page, timeout_ms=5000):
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass
 
 
def _pause(page, ms):
    try:
        page.evaluate("(ms) => new Promise((r) => setTimeout(r, ms))", ms)
    except Exception:                      # page navigated while waiting
        _settle(page, 3000)
 
 
def _state(page):
    for _ in range(3):
        try:
            return page.evaluate(STATE_JS)
        except Exception:
            _settle(page, 3000)
    return {"url": page.url, "title": "", "text_len": 0, "text": "", "h1": [],
            "headings": [], "has_price": False, "has_image": False, "card_count": 0,
            "card_sig": "", "card_names": [], "cart_count": None, "has_input": False}
 
 
def resolve(page, target):
    arg = dict(target)
    arg["danger"] = DANGER_RE.pattern
    if arg.get("kind") == "auth_link":
        arg["pattern"] = AUTH_PATTERNS.get(arg.get("which", ""), AUTH_PATTERNS["account"])
    for _ in range(3):
        try:
            return page.evaluate(RESOLVE_JS, arg)
        except Exception:
            _settle(page, 3000)
    return {"found": False}
 
 
def dismiss_overlays(page):
    for _ in range(2):
        try:
            clicked = page.evaluate(DISMISS_JS)
        except Exception:
            return
        if not clicked:
            return
        _pause(page, 300)
 
 
def catalog(page):
    """What can this page do? Used by the planner."""
    info = {"search": False, "search_opener": False, "nav_texts": [], "product_count": 0,
            "product_names": [], "sort": False, "auth": [], "add_to_cart": False}
    info["search"] = bool(resolve(page, {"kind": "search_box"}).get("found"))
    if not info["search"]:
        info["search_opener"] = bool(resolve(page, {"kind": "search_opener"}).get("found"))
    info["nav_texts"] = resolve(page, {"kind": "nav_list"}).get("texts", [])
    cards = resolve(page, {"kind": "product_cards"})
    info["product_count"] = cards.get("count", 0)
    info["product_names"] = cards.get("names", [])
    info["sort"] = bool(resolve(page, {"kind": "sort_native"}).get("found")
                        or resolve(page, {"kind": "sort_opener"}).get("found"))
    for which in AUTH_PATTERNS:
        hit = resolve(page, {"kind": "auth_link", "which": which})
        if hit.get("found"):
            info["auth"].append({"which": which, "text": hit.get("text", ""),
                                 "href": hit.get("href", "")})
    info["add_to_cart"] = bool(resolve(page, {"kind": "add_to_cart"}).get("found"))
    return info
 
 
# ------------------------------------------------------------------- checks
def _evaluate_check(page, check, before, after, delta, ctx):
    """Returns (ok, evidence)."""
    kind = check["type"]
    if kind == "no_server_error":
        if delta["server_errors"]:
            e = delta["server_errors"][0]
            return False, "HTTP %s from %s" % (e["status"], e["url"][:120])
        low = after["text"].lower()
        new = [m for m in ERROR_MARKERS if m in low and m not in before["text"].lower()]
        if new:
            return False, "error text on page: %r" % new[0]
        return True, "no 5xx responses, no error text"
    if kind == "no_http_error":
        if delta["bad_docs"]:
            e = delta["bad_docs"][0]
            return False, "page answered HTTP %s (%s)" % (e["status"], e["url"][:120])
        return True, "page loaded without an HTTP error"
    if kind == "not_blank":
        ok = after["text_len"] >= 80
        return ok, "page text length %d" % after["text_len"]
    if kind == "url_changed":
        ok = _strip(after["url"]) != _strip(before["url"])
        return ok, "%s -> %s" % (before["url"][:90], after["url"][:90])
    if kind == "url_same_site":
        ok = _same_site(_host(after["url"]), _host(ctx["start_url"]))
        return ok, "landed on %s" % after["url"][:100]
    if kind == "url_matches":
        parsed = urlparse(after["url"])
        ok = bool(re.search(check.get("pattern", ""), parsed.path + "?" + parsed.query, re.I))
        return ok, "url %s vs /%s/" % (after["url"][:100], check.get("pattern", ""))
    if kind == "results_nonempty":
        return after["card_count"] >= 1, "%d product card(s): %s" % (
            after["card_count"], "; ".join(after["card_names"][:3])[:150])
    if kind == "results_empty_or_message":
        message = bool(EMPTY_RE.search(after["text"]))
        ok = after["card_count"] == 0 or message
        return ok, "%d product card(s), 'no results' message shown: %s" % (
            after["card_count"], message)
    if kind == "list_changed":
        changed = after["card_sig"] != before["card_sig"] or _strip(after["url"]) != _strip(before["url"])
        return changed and after["card_count"] >= 1, (
            "%d card(s); list changed: %s" % (after["card_count"], changed))
    if kind == "has_heading":
        bad = re.search(r"(404|not found|error)", after["title"], re.I)
        ok = bool(after["h1"] or after["headings"]) and not bad
        return ok, "headings %s, title %r" % (after["headings"][:2], after["title"][:60])
    if kind == "product_page":
        missing = []
        if not (after["h1"] or after["headings"]):
            missing.append("heading")
        if not after["has_price"]:
            missing.append("price")
        if not after["has_image"]:
            missing.append("image")
        return not missing, ("product page complete (heading, price, image)" if not missing
                             else "product page is missing: " + ", ".join(missing))
    if kind == "add_to_cart_present":
        hit = resolve(page, {"kind": "add_to_cart"})
        return bool(hit.get("found")), ("add-to-cart control: %r" % hit.get("text", "")
                                        if hit.get("found") else "no add-to-cart control found")
    if kind == "cart_changed":
        b, a = before["cart_count"], after["cart_count"]
        count_up = a is not None and (b is None and a > 0 or b is not None and a > b)
        toast = bool(CART_TOAST_RE.search(after["text"])) and not CART_TOAST_RE.search(before["text"])
        to_cart = _strip(after["url"]) != _strip(before["url"]) and bool(CART_URL_RE.search(after["url"]))
        return count_up or toast or to_cart, (
            "cart badge %s -> %s, confirmation message: %s, went to cart page: %s" % (b, a, toast, to_cart))
    if kind == "auth_gate_or_page":
        parsed = urlparse(after["url"])
        on_target = bool(re.search(check.get("path", "."), parsed.path + "?" + parsed.query, re.I)) \
            and not LOGIN_URL_RE.search(parsed.path)
        gate = bool(LOGIN_URL_RE.search(after["url"])) or (
            bool(LOGIN_HINT_RE.search(after["text"])) and after["has_input"])
        return on_target or gate, "landed on %s (login gate: %s)" % (after["url"][:100], gate)
    if kind == "text_visible":
        ok = bool(re.search(check.get("pattern", ""), after["text"], re.I))
        return ok, "text /%s/ %s" % (check.get("pattern", ""), "found" if ok else "not found")
    if kind == "no_error_text":
        low = after["text"].lower()
        hit = [m for m in ERROR_MARKERS if m in low]
        return not hit, ("error text: %r" % hit[0]) if hit else "no error text"
    return False, "unknown check %r" % kind
 
 
def _norm_checks(step):
    out = []
    for c in step.get("checks", []):
        out.append({"type": c} if isinstance(c, str) else dict(c))
    return out
 
 
# --------------------------------------------------------------- step runner
def _guard(info):
    text = "%s %s" % (info.get("text", ""), urlparse(info.get("href", "")).path)
    return bool(DANGER_RE.search(text))
 
 
def _click_resolved(page, info):
    """Click the element marked by resolve(). Returns how it was clicked."""
    if _guard(info):
        raise RuntimeError("refused to click %r: looks dangerous" % info.get("text", ""))
    loc = page.locator('[data-qa-flow="1"]').first
    if info.get("target") == "_blank":
        loc.evaluate("(el) => el.removeAttribute('target')")
    try:
        loc.scroll_into_view_if_needed(timeout=3000)
        loc.click(timeout=8000)
        return "click"
    except Exception as first:
        try:
            loc.click(timeout=3000, force=True)
            return "forced click"
        except Exception:
            href = info.get("href", "")
            if href.startswith("http") and _same_site(_host(href), _host(page.url)):
                page.goto(href, wait_until="domcontentloaded", timeout=45000)
                return "opened its link (click was blocked)"
            raise first
 
 
def _do_action(page, flow, step, ctx, out):
    """Perform the action. Returns None if fine, or a reason string if unresolved."""
    action = step["action"]
    if action == "goto":
        url = flow["start_url"] if step.get("url") in (None, "", "start") else step["url"]
        if not _same_site(_host(url), _host(flow["start_url"])):
            return "refused to leave the site: %s" % url
        for attempt in range(2):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                break
            except Exception as error:
                if attempt == 1 or "ERR_" not in str(error):
                    raise
                _pause(page, 2000)             # network blip - try once more
        _settle(page)
        dismiss_overlays(page)
        return None
    if action == "search":
        value = step.get("value", flow.get("term", ""))
        info = resolve(page, {"kind": "search_box"})
        if not info.get("found"):
            opener = resolve(page, {"kind": "search_opener"})
            if opener.get("found"):
                _click_resolved(page, opener)
                _pause(page, 400)
                info = resolve(page, {"kind": "search_box"})
        if not info.get("found"):
            return "could not find a search box"
        out["target"] = "search box"
        box = page.locator('[data-qa-flow="1"]').first
        box.click(timeout=8000)
        box.fill(value)
        box.press("Enter")
        return None
    if action == "click":
        target = dict(step.get("target", {}))
        if target.get("kind") not in TARGET_KINDS:
            return "unsupported target %r" % target.get("kind")
        info = resolve(page, target)
        if not info.get("found"):
            return "could not find %s" % target.get("kind")
        out["target"] = "%s %r -> %s" % (target["kind"], info.get("text", ""), info.get("href", "")[:80])
        how = _click_resolved(page, info)
        if how != "click":
            out["target"] += " [%s]" % how
        return None
    if action == "choose_sort":
        info = resolve(page, {"kind": "sort_native"})
        if info.get("found"):
            out["target"] = "sort: %s" % info.get("option_text", "")
            page.locator('[data-qa-flow="1"]').first.select_option(index=info["option_index"])
            return None
        opener = resolve(page, {"kind": "sort_opener"})
        if not opener.get("found"):
            return "could not find a sort control"
        _click_resolved(page, opener)
        _pause(page, 400)
        option = resolve(page, {"kind": "sort_option"})
        if not option.get("found"):
            return "could not find a 'price low to high' sort option"
        out["target"] = "sort: %s" % option.get("text", "")
        _click_resolved(page, option)
        return None
    if action == "choose_variant":
        info = resolve(page, {"kind": "variant"})
        if not info.get("found"):
            return "could not find a size / variant option"
        out["target"] = "variant %r" % info.get("text", "")
        if info.get("select"):
            page.locator('[data-qa-flow="1"]').first.select_option(index=info["option_index"])
        else:
            _click_resolved(page, info)
        return None
    if action == "back":
        page.go_back(wait_until="domcontentloaded")
        _settle(page)
        return None
    if action == "observe":
        return None
    return "unknown action %r" % action
 
 
def _run_step(page, flow, step, index, rec, ctx):
    out = {"index": index, "action": step["action"], "note": step.get("note", ""),
           "target": "", "checks": [], "status": "PASS"}
    gate = step.get("gate")
    if gate and not flow.get("gates", {}).get(gate):
        out["status"] = "GATED"
        out["note"] = "skipped: '%s' steps are not allowed on this host" % gate
        return out
 
    before = _state(page)
    marks = {"server_errors": len(rec["server_errors"]), "bad_docs": len(rec["bad_docs"]),
             "page_errors": len(rec["page_errors"])}
    try:
        problem = _do_action(page, flow, step, ctx, out)
    except Exception as error:
        problem = "%s: %s" % (type(error).__name__, str(error)[:160])
    if problem:
        out["status"] = "SKIPPED" if step.get("optional") else "UNRESOLVED"
        out["note"] = problem
        return out
 
    if step["action"] != "observe":
        _settle(page, 5000)
        _pause(page, 400)
    after = _state(page)
 
    delta = {"server_errors": rec["server_errors"][marks["server_errors"]:],
             "bad_docs": rec["bad_docs"][marks["bad_docs"]:]}
    checks = [{"type": "no_server_error"}] + _norm_checks(step)
    if step["action"] in ("goto", "search", "click", "back"):
        checks.append({"type": "not_blank"})
 
    def run_all(cs):
        return [(c, ) + _evaluate_check(page, c, before, after, delta, ctx) for c in cs]
 
    results = run_all(checks)
    polls = 0
    while polls < 8 and any(not ok and c["type"] in POLLABLE for c, ok, _ in results):
        _pause(page, 600)
        after = _state(page)
        delta = {"server_errors": rec["server_errors"][marks["server_errors"]:],
                 "bad_docs": rec["bad_docs"][marks["bad_docs"]:]}
        results = run_all(checks)
        polls += 1
 
    for c, ok, evidence in results:
        soft = c["type"] in SOFT_CHECKS
        out["checks"].append({"type": c["type"], "ok": ok, "evidence": evidence, "soft": soft})
        if not ok and not soft:
            out["status"] = "FAIL"
        elif not ok and soft and out["status"] == "PASS":
            out["status"] = "REVIEW"
    out["url_before"], out["url_after"] = before["url"], after["url"]
    out["page_errors"] = len(rec["page_errors"]) - marks["page_errors"]
    ctx["last_state"] = after
    return out
 
 
def _attach(page, rec, base_host):
    def same(host):
        return _same_site(host, base_host)
 
    def on_response(resp):
        try:
            kind = resp.request.resource_type
            path = urlparse(resp.url).path
            if not same(_host(resp.url)) or TELEMETRY_RE.search(path):
                return
            if resp.status >= 500 and kind in ("document", "fetch", "xhr"):
                rec["server_errors"].append({"status": resp.status, "url": resp.url})
            if (kind == "document" and resp.status >= 400
                    and resp.frame == page.main_frame):
                rec["bad_docs"].append({"status": resp.status, "url": resp.url})
        except Exception:
            pass
 
    def on_dialog(dialog):
        try:
            dialog.dismiss()
        except Exception:
            pass
 
    page.on("response", on_response)
    page.on("pageerror", lambda exc: rec["page_errors"].append(str(exc)[:200]))
    page.on("dialog", on_dialog)
 
 
def run_flow(page, flow):
    """Run one flow on `page`. Never raises; returns a result dict.
 
    verdict: PASS | FAIL (a HARD check failed on an element we found - a real finding)
             REVIEW (only SOFT heuristic checks failed - a human should look)
             UNVERIFIED (we could not find an element - not a site bug)
             GATED (stopped before a step that is not allowed on this host)
    """
    rec = {"server_errors": [], "bad_docs": [], "page_errors": []}
    _attach(page, rec, _host(flow["start_url"]))
    page.set_default_timeout(8000)
    ctx = {"start_url": flow["start_url"]}
    steps, verdict, failed, reviews = [], "PASS", None, []
    for index, step in enumerate(flow["steps"]):
        out = _run_step(page, flow, step, index, rec, ctx)
        steps.append(out)
        if out["status"] == "REVIEW":
            for c in out["checks"]:
                if not c["ok"]:
                    reviews.append({"step": index, "check": c["type"], "evidence": c["evidence"]})
            continue                       # soft problem: keep walking the journey
        if out["status"] == "FAIL":
            verdict = "FAIL"
            failed = {"step": index,
                      "check": next(c["type"] for c in out["checks"] if not c["ok"] and not c["soft"])}
            break
        if out["status"] == "UNRESOLVED":
            verdict = "UNVERIFIED"
            break
        if out["status"] == "GATED":
            verdict = "GATED"
            break
    if verdict == "PASS" and reviews:
        verdict = "REVIEW"
    summary = "%s: %s" % (flow.get("id", "flow"), verdict)
    if verdict == "FAIL":
        bad = steps[failed["step"]]
        detail = next(c["evidence"] for c in bad["checks"] if not c["ok"] and not c["soft"])
        summary += " at step %d (%s) - failed check '%s': %s" % (
            failed["step"] + 1, bad["action"], failed["check"], detail)
    elif verdict == "REVIEW":
        summary += " - needs a human look: " + "; ".join(
            "step %d '%s': %s" % (r["step"] + 1, r["check"], r["evidence"]) for r in reviews)
    elif verdict in ("UNVERIFIED", "GATED"):
        last = steps[-1]
        summary += " at step %d (%s): %s" % (last["index"] + 1, last["action"], last["note"])
    return {"verdict": verdict, "failed": failed, "reviews": reviews, "summary": summary,
            "steps": steps, "page_errors": len(rec["page_errors"])}
 
