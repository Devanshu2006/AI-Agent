import os
import json

from dotenv import load_dotenv
from google import genai


# ============================================================
# ENVIRONMENT SETUP
# ============================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env file."
    )


client = genai.Client(
    api_key=api_key
)

MODEL = "gemini-3.5-flash-lite"


# ============================================================
# WEBSITE ANALYSIS + TEST GENERATION
# ============================================================

def analyze_website(website_data):

    prompt = f"""
You are an expert QA automation engineer and test automation architect.

Your job is to analyze the observed website information and generate
realistic, executable Playwright + pytest automation tests.

IMPORTANT:
Use ONLY the information actually observed from the website.

Do NOT invent:

- UI elements
- credentials
- buttons
- URLs
- fields
- workflows
- APIs
- application behavior

============================================================
WEBSITE INFORMATION
============================================================

URL:
{website_data.get("url", "")}

TITLE:
{website_data.get("title", "")}

PAGE TEXT:
{website_data.get("page_text", "")}

INTERACTIVE ELEMENTS:
{json.dumps(
    website_data.get("elements", []),
    indent=2
)}

FORMS:
{json.dumps(
    website_data.get("forms", []),
    indent=2
)}

HEADINGS:
{json.dumps(
    website_data.get("headings", []),
    indent=2
)}

LINKS:
{json.dumps(
    website_data.get("links", []),
    indent=2
)}

============================================================
TEST GENERATION RULES
============================================================

1. Act as a senior QA automation engineer.

2. Generate 3–6 meaningful test scenarios.

3. Prioritize important functionality.

4. Include a mixture of:
   - Positive tests
   - Negative tests
   - Validation tests
   - Important UI behavior

5. Only create tests for functionality supported by observed data.

6. NEVER invent credentials.

7. NEVER invent secret values.

8. NEVER invent application behavior.

9. NEVER perform destructive actions.

10. Use Playwright sync API.

11. Use pytest.

12. Use Page Object Model.

13. Keep Page Objects separate from test files.

14. Page Objects should contain:
   - locators
   - page interaction methods
   - reusable actions

15. Test files should contain:
   - test functions
   - assertions
   - test flow

16. Every test MUST contain at least one meaningful assertion.

17. NEVER generate an empty test.

18. NEVER use:
   - pass
   - time.sleep()
   - arbitrary long sleeps

19. Prefer Playwright automatic waiting.

20. Prefer locators in this order:

   1. get_by_role()
   2. get_by_label()
   3. get_by_placeholder()
   4. get_by_text()
   5. locator()

21. Avoid XPath unless absolutely necessary.

22. Avoid brittle CSS selectors.

23. Do not assume an element exists.

24. Do not invent routes.

============================================================
PACKAGE / IMPORT RULES
============================================================

The generated project has this structure:

generated_tests/
    __init__.py

    pages/
        __init__.py
        login_page.py

    tests/
        __init__.py
        test_login.py

Generated test files MUST import Page Objects using the FULL
package path.

CORRECT:

from generated_tests.pages.login_page import LoginPage

WRONG:

from pages.login_page import LoginPage

WRONG:

from login_page import LoginPage

WRONG:

import pages.login_page

Always use:

from generated_tests.pages.<page_file> import <ClassName>

============================================================
FILE STRUCTURE RULES
============================================================

Page Object files:

pages/

Test files:

tests/

Example:

pages/login_page.py

tests/test_login.py

============================================================
PAGE OBJECT RULES
============================================================

Use this general structure:

from playwright.sync_api import Page


class ExamplePage:

    def __init__(self, page: Page):
        self.page = page

Use meaningful Page Object class names.

============================================================
TEST FILE RULES
============================================================

Example:

import pytest
from playwright.sync_api import Page

from generated_tests.pages.login_page import LoginPage


def test_example(page: Page):

    login_page = LoginPage(page)

    # actions

    # assertion

Every test must contain at least one meaningful assertion.

============================================================
ASSERTION RULES
============================================================

Examples:

assert page.title() == "Expected Title"

assert page.get_by_text("Expected Text").is_visible()

assert page.url == "Expected URL"

assert locator.is_visible()

Only use assertions supported by observed website data.

============================================================
TEST DATA RULES
============================================================

Do NOT invent usernames or passwords.

If valid credentials are not available from observed website data,
do not assume credentials.

If demo credentials are publicly visible on the website,
they may be used.

============================================================
NAVIGATION RULES
============================================================

Use only:

- provided website URL
- observed URLs
- observed href values

Do not invent:

/login
/dashboard
/checkout
/admin

unless actually observed.

============================================================
CODE QUALITY RULES
============================================================

Generated code must:

- be syntactically valid
- be executable
- use correct imports
- follow PEP8 reasonably
- use clear names
- contain no markdown
- contain no explanation outside code

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do NOT return markdown or code fences.

Return raw JSON only.

The JSON MUST have this structure:

{{
    "website": "...",
    "page_type": "...",
    "test_scenarios": [
        {{
            "id": "TC001",
            "title": "...",
            "type": "Positive",
            "priority": "High",
            "steps": [
                "...",
                "..."
            ],
            "expected_result": "..."
        }}
    ],
    "files": [
        {{
            "path": "pages/login_page.py",
            "type": "page_object",
            "code": "complete Python code"
        }},
        {{
            "path": "tests/test_login.py",
            "type": "test",
            "code": "complete Python code"
        }}
    ]
}}

============================================================
FINAL VALIDATION
============================================================

Before returning:

1. JSON must be valid.

2. Python must be syntactically valid.

3. Every test must contain an assertion.

4. No test may contain pass.

5. No test may contain time.sleep().

6. No credentials may be invented.

7. No UI elements may be invented.

8. No destructive actions.

9. Page Objects must be inside pages/.

10. Tests must be inside tests/.

11. Test files must use:

from generated_tests.pages.<page_file> import <ClassName>

12. Never use:

from pages.<page_file> import <ClassName>

13. Never use:

from <page_file> import <ClassName>

14. Use Playwright sync API.

15. Use pytest.

16. Follow Page Object Model.

Return ONLY JSON.
"""

    response = client.interactions.create(
        model=MODEL,
        input=prompt,
        store=False
    )

    return response.output_text


# ============================================================
# AI FAILURE ANALYSIS
# ============================================================

def analyze_failure(
    website_data,
    failure_data,
    generated_files
):

    prompt = f"""
You are an expert QA automation engineer responsible for safely
healing automatically generated Playwright + pytest tests.

A generated test suite has failed.

Analyze the failure and determine whether it can be safely fixed
automatically.

============================================================
WEBSITE INFORMATION
============================================================

{json.dumps(
    website_data,
    indent=2
)}

============================================================
EXECUTION FAILURE
============================================================

{json.dumps(
    failure_data,
    indent=2
)}

============================================================
GENERATED FILES
============================================================

{json.dumps(
    generated_files,
    indent=2
)}

============================================================
AUTO-HEALING RULES
============================================================

You may ONLY patch:

generated_tests/pages/*.py

generated_tests/tests/*.py

Never modify:

- application source code
- browser.py
- agent.py
- generator.py
- executor.py
- healer.py
- main.py
- .env
- configuration files
- database files

Only operation allowed:

replace

The old_text MUST already exist exactly in the file.

============================================================
SAFE HEALING CASES
============================================================

Safe cases include:

- incorrect locator
- incorrect selector
- wrong Page Object locator
- incorrect import
- missing Page Object method
- incorrect generated assertion
- incorrect generated test logic
- incorrect generated navigation
- incorrect generated element reference

============================================================
DO NOT AUTO-HEAL
============================================================

Set safe_to_auto_heal to false for:

- application bugs
- server errors
- unavailable website
- network failures
- environment problems
- missing dependencies
- missing browser
- authentication secrets
- unknown credentials
- database failures
- external service failures
- uncertain root cause

============================================================
IMPORTANT
============================================================

Never modify application code.

Never invent credentials.

Never invent UI elements.

Never remove meaningful assertions simply to make a test pass.

Never delete a test because it failed.

Never replace an assertion with:

assert True

Never add:

pass

Never add:

time.sleep()

Prefer Playwright automatic waiting.

If the failure is an incorrect Page Object locator,
fix the locator.

If the failure is an incorrect import,
fix the import.

Correct import:

from generated_tests.pages.<page_file> import <ClassName>

Incorrect:

from pages.<page_file> import <ClassName>

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use:

{{
    "safe_to_auto_heal": true,
    "failure_category": "locator",
    "root_cause": "...",
    "confidence": "High",
    "suggested_fix": "...",
    "patches": [
        {{
            "file": "generated_tests/pages/login_page.py",
            "operation": "replace",
            "old_text": "exact existing code",
            "new_text": "replacement code",
            "reason": "..."
        }}
    ]
}}

If no safe fix exists:

{{
    "safe_to_auto_heal": false,
    "failure_category": "unknown",
    "root_cause": "...",
    "confidence": "Low",
    "suggested_fix": "...",
    "patches": []
}}

Return ONLY JSON.
"""

    response = client.interactions.create(
        model=MODEL,
        input=prompt,
        store=False
    )

    return response.output_text