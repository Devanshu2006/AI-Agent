"""Turns the AI test plan into files on disk."""
import json
import re
from pathlib import Path

GENERATED_ROOT = Path("generated_tests")
PAGES_DIR = GENERATED_ROOT / "pages"
TESTS_DIR = GENERATED_ROOT / "tests"

# Written by bug_detector.py / this module, never by the AI.
RESERVED_FILES = {"__init__.py", "conftest.py", "test_bugs.py", "test_forms.py", "test_flows.py"}

CONFTEST_CODE = '''"""Shared fixtures for generated Playwright tests."""

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
'''



# ============================================================
# CLEANING / SCAFFOLDING
# ============================================================

def clean_old_generated_tests():
    """Remove old Page Objects and tests (including test_bugs.py). Backups stay."""
    print("\n========== CLEANING OLD GENERATED TESTS ==========")
    removed = []
    for directory in (PAGES_DIR, TESTS_DIR):
        if not directory.exists():
            continue
        for file_path in directory.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
            file_path.unlink()
            removed.append(file_path)

    for file_path in removed:
        print(f"[Cleaner] Removed: {file_path}")
    print(f"[Cleaner] Removed {len(removed)} old generated file(s)."
          if removed else "[Cleaner] No old generated test files found.")
    print("[Cleaner] Backups were preserved.")


def create_init_files():
    """Create the package skeleton and the shared conftest.py."""
    for directory in (GENERATED_ROOT, PAGES_DIR, TESTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
        init_file = directory / "__init__.py"
        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")

    (GENERATED_ROOT / "conftest.py").write_text(CONFTEST_CODE, encoding="utf-8")


# ============================================================
# PARSING THE AI RESPONSE
# ============================================================

def parse_json_response(response):
    """Parse an AI reply into Python data, tolerating fences and stray prose."""
    if isinstance(response, (dict, list)):
        return response
    if not isinstance(response, str):
        raise TypeError(
            f"Expected JSON string, dict, or list; received {type(response).__name__}"
        )

    text = response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as first_error:
        # The model sometimes adds a sentence before/after the JSON object.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(
            f"AI returned invalid JSON: {first_error}\nResponse preview: {text[:500]}"
        ) from first_error


# Backwards-compatible name.
clean_json_response = parse_json_response


def save_test_plan(ai_response):
    test_data = parse_json_response(ai_response)
    output_path = Path("test_plan.json")
    output_path.write_text(
        json.dumps(test_data, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[Generator] Test plan saved: {output_path.resolve()}")
    return test_data


# ============================================================
# WRITING GENERATED CODE
# ============================================================

def sanitize_path(relative_path):
    """Normalize AI-generated paths to exactly pages/<name>.py or tests/<name>.py."""
    if not isinstance(relative_path, str):
        raise ValueError("Generated file path must be a string.")

    rel = relative_path.strip().replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    if rel.startswith("generated_tests/"):
        rel = rel[len("generated_tests/"):]

    parts = rel.split("/")
    if (
        len(parts) != 2
        or parts[0] not in ("pages", "tests")
        or not parts[1].endswith(".py")
        or not parts[1][:-3].isidentifier()
    ):
        raise ValueError(
            f"Unsafe or unsupported generated path {relative_path!r} "
            "(expected pages/<name>.py or tests/<name>.py)."
        )

    # pytest only collects test_*.py; a misnamed file would silently never run.
    if parts[0] == "tests" and not parts[1].startswith("test_"):
        parts[1] = "test_" + parts[1]

    if parts[1] in RESERVED_FILES:
        raise ValueError(f"{parts[1]} is reserved and cannot be generated by the AI.")

    return "/".join(parts)


def strip_code_fences(code):
    code = code.strip()
    code = re.sub(r"^```(?:python)?\s*", "", code)
    code = re.sub(r"\s*```$", "", code)
    return code.strip()


def normalize_generated_imports(code):
    """from pages.x import Y  ->  from generated_tests.pages.x import Y"""
    code = re.sub(
        r"(?m)^(\s*from\s+)pages\.([A-Za-z_]\w*)(\s+import\s+)",
        r"\1generated_tests.pages.\2\3",
        code,
    )
    code = re.sub(r"(?m)^(\s*import\s+)pages\.", r"\1generated_tests.pages.", code)
    return code


def generate_code_files(test_data):
    """Write the AI's page objects and tests. Returns the list of written paths."""
    generated_files = []

    for file_info in test_data.get("files", []):
        code = file_info.get("code", "")
        if not file_info.get("path") or not code:
            continue

        try:
            relative_path = sanitize_path(file_info["path"])
        except ValueError as error:
            print(f"\n[Generator] Skipping file: {error}")
            continue

        code = normalize_generated_imports(strip_code_fences(code))

        full_path = GENERATED_ROOT / relative_path
        if str(full_path) in generated_files:
            print(f"[Generator] Warning: {full_path} generated twice; keeping the last.")
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(code + "\n", encoding="utf-8")

        if str(full_path) not in generated_files:
            generated_files.append(str(full_path))
        print(f"[Generator] Created: {full_path}")

    return generated_files
