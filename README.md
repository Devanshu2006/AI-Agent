# testgen agent

Give it a URL. It explores the site in a real browser, **fills in the forms with
test inputs, compares the actual result with the expected one**, writes Page
Objects + pytest tests, runs them, and self-heals broken locators.

```
explore → detect bugs → LIVE FORM TESTING → AI test plan → generate POM/tests
        → validate → run pytest → self-heal → report
```

## Setup

```bash
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
copy env.example .env                                # then fill in GEMINI_API_KEY
python apply_integration.py                          # once: wires the form tester into main.py
python main.py https://your-site.example
```

## What "live form testing" does

For each form found, the agent builds cases **with the expected outcome decided
first**, runs each in a fresh browser, and compares:

| Case | Expected |
|---|---|
| empty submit | `validation_blocked` (or "no server error" if nothing is required) |
| each required field missing | `validation_blocked` |
| invalid e-mail / URL / out-of-range number / pattern / too short | `validation_blocked` |
| spaces-only in a required field | `validation_blocked` |
| 300-character values | no server error |
| valid data in every field | `submitted` |
| wrong credentials (login) | `validation_blocked` |
| `.env` test credentials (login) | `submitted` |
| extra cases from Gemini (only with evidence from labels / min / max / pattern) | as decided by the model |

The **actual** outcome is read from the browser: native validation, disabled
button, 4xx answer, visible error text, request sent, page navigated, 5xx.
A mismatch is **replayed** and only reported if it reproduces.

Outputs: `form_test_results.json` (every case, expected vs actual, evidence),
confirmed bugs merged into `bug_report.json`, and `generated_tests/tests/test_forms.py`
(PASS cases = regression tests; confirmed bugs = `@pytest.mark.bug` + xfail, same
convention as `test_bugs.py`; XPASS means the bug was fixed).

## Safety model - please read

* Card, CVV, bank, OTP and ID-number fields are **never filled**; the form is skipped.
* **Real submissions happen only on hosts in `FORM_TEST_ALLOWED_HOSTS`** (plus
  localhost). On any other site, POST/PUT/PATCH/DELETE from signup, login, contact,
  newsletter, payment and ordering forms - and from every "valid data" case - are
  **aborted inside the browser** and reported as `UNVERIFIED`, never as a bug.
  Client-side behaviour (native validation, disabled buttons, JS messages) is still tested.
* On an allowed host the tests really submit forms: use a test/staging environment.
* Synthetic e-mails always end in `@example.com`. `.env` secrets are used through
  placeholders and never written to reports or generated code.
* Only test sites you own or have permission to test.

## Try it on the demo site (planted bugs)

```bash
python demo_site/app.py            # terminal 1
python main.py http://127.0.0.1:5000   # terminal 2
```
Expected: 3 bugs - spaces-only name accepted (/contact), invalid e-mail accepted
(/signup), 500 error on a long name (/signup).

## Known limits

* Native inputs only: custom widgets (React-Select, date pickers, rich-text editors),
  file uploads, CAPTCHA and OTP steps are skipped or not understood.
* Multi-step wizards: only the first step is tested.
* Message detection looks for English error / success words.
* `no_effect` results on search/data forms are `UNVERIFIED` (client-side widgets often
  react invisibly).

## Add to `.gitignore`

```
.env
.venv/
__pycache__/
.pytest_cache/
artifacts/
generated_tests/auth_state.json      # a logged-in session - treat like a password
*.bak_before_formtests
```
