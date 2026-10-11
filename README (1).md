# testgen agent

An agent that explores **any website or web app** in a real browser, then writes,
runs and fixes pytest-playwright tests until they pass.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install            # installs chromium, firefox, webkit
export ANTHROPIC_API_KEY=sk-ant-...                  # Windows: set ANTHROPIC_API_KEY=...
```

Optional: `export ANTHROPIC_MODEL=<model string>`.

## Examples

Any public flow, no login:

```bash
python agent.py --url https://example.com \
  --goal "Search for 'laptop', open the first result, add it to the cart" --headed
```

Flow with a login (the model only sees variable *names*, never the values):

```bash
export APP_EMAIL=... APP_PASSWORD=...
python agent.py --url https://app.example.com \
  --goal "Log in and create a new project named with a unique suffix" \
  --secrets APP_EMAIL,APP_PASSWORD
```

Many goals in one run (`goals.txt`, one per line, `#` for comments):

```bash
python agent.py --url https://app.example.com --goals-file goals.txt
```

Mobile emulation, other browsers:

```bash
python agent.py --url https://example.com --goal "..." --device "iPhone 13"
python agent.py --url https://example.com --goal "..." --browser webkit
```

API checks alongside UI tests: mention them in the goal, e.g.
`"Create an order through the UI, then verify GET /api/orders returns it"`.

Match your project's style:

```bash
python agent.py --url ... --goal "..." --context pages/base_page.py tests/test_example.py
```

Steer it: `--instructions "use the staging tenant, ignore the blog section"`.

## Flags

| Flag | Meaning |
|---|---|
| `--url` | Base URL of the site |
| `--goal` / `--goals-file` | What to test, in plain English |
| `--out` | Where tests go (default `tests/generated`) |
| `--context` | Existing files to imitate |
| `--secrets` | Env var names usable in tests |
| `--instructions` | Extra free-form guidance |
| `--browser` | chromium, firefox or webkit |
| `--device` | Emulated device, e.g. `Pixel 7` |
| `--headed` | Show the browser |
| `--max-steps` | Turn cap per goal (default 40) |
| `--timeout` | Browser timeout in seconds (default 60) |

## What it can handle

Forms, SPAs, dropdowns, checkboxes, hover menus, file uploads, iframes, popups
and new tabs, JS dialogs, async updates, multi-user flows, API calls, canvas or
custom widgets (via screenshots), and mobile viewports.

## Not covered

Native mobile apps (Android/iOS) and desktop apps are not browser-based, so
Playwright can't drive them. They need Appium or a desktop driver.

## Always

- Use staging or test accounts. The agent avoids destructive actions, but it is
  driving a real browser against a real site.
- Read the generated tests and check that the assertions prove the flow worked.
- Re-run yourself: `pytest tests/generated --base-url https://your-site.com`
