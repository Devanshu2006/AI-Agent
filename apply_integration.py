"""Wire the form tester into the existing pipeline. Run ONCE from the project root:

    python apply_integration.py

What it changes (exact-text replacements, all-or-nothing):
  main.py    import the new modules, add "STEP 2b: LIVE FORM TESTING", merge the
             confirmed form bugs into bug_report.json, generate test_forms.py
  agent.py   when form results exist, tell the test planner which forms are already
             covered so the LLM does not duplicate them (focus on flows / navigation)
  healer.py  protect generated_tests/tests/test_forms.py from "self-healing"
             (a failing form test means the APP changed, not that the test is wrong)

Safe to run twice (already-patched files are skipped). Originals are saved as
<file>.bak_before_formtests.
"""
import shutil
import sys
from pathlib import Path

EDITS = {
    "main.py": [
        (
            "from healer import heal_failed_tests\n",
            "from healer import heal_failed_tests\n"
            "from form_test_codegen import generate_form_tests\n"
            "from form_tester import run_form_tests\n",
        ),
        (
            "    # STEP 3: PLAN + GENERATE + VALIDATE\n",
            "    # STEP 2b: LIVE FORM TESTING (expected vs actual)\n"
            "    website_data[\"form_tests\"] = None\n"
            "    if os.getenv(\"FORM_TESTS\", \"1\") == \"1\":\n"
            "        print(\n"
            "            \"\\n========== STEP 2b: LIVE FORM TESTING ==========\"\n"
            "        )\n"
            "        try:\n"
            "            form_results = run_form_tests(website_data)\n"
            "            website_data[\"form_tests\"] = form_results\n"
            "            for form_bug in form_results.get(\"bugs\", []):\n"
            "                form_bug[\"id\"] = f\"BUG{len(bugs) + 1:03d}\"\n"
            "                bugs.append(form_bug)\n"
            "            if form_results.get(\"bugs\"):\n"
            "                save_bug_report(bugs, effective_url)\n"
            "        except Exception as error:\n"
            "            print(\n"
            "                f\"\\n[Agent] Form testing failed (continuing): {error}\"\n"
            "            )\n"
            "\n"
            "    # STEP 3: PLAN + GENERATE + VALIDATE\n",
        ),
        (
            "                generate_bug_tests(bugs)\n",
            "                generate_bug_tests(bugs)\n"
            "\n"
            "                # Deterministic form tests (verified expected vs actual).\n"
            "                generate_form_tests(website_data.get(\"form_tests\"))\n",
        ),
    ],
    "agent.py": [
        (
            "from google import genai\n",
            "from google import genai\n"
            "\n"
            "from form_tester import FORM_COVERAGE_RULE, summarize_form_tests\n",
        ),
        (
            "    data_json = json.dumps(context, indent=1, ensure_ascii=False, default=str)\n",
            "    form_summary = summarize_form_tests(website_data.get(\"form_tests\"))\n"
            "    form_rule = \"\"\n"
            "    if form_summary:\n"
            "        context[\"form_tests_already_covered\"] = form_summary\n"
            "        form_rule = FORM_COVERAGE_RULE\n"
            "    data_json = json.dumps(context, indent=1, ensure_ascii=False, default=str)\n",
        ),
        (
            "        + PLAN_INSTRUCTIONS\n        + PLAN_FORMAT\n",
            "        + form_rule\n        + PLAN_INSTRUCTIONS\n        + PLAN_FORMAT\n",
        ),
    ],
    "healer.py": [
        (
            'PROTECTED_FILES = {"__init__.py", "conftest.py", "test_bugs.py"}',
            'PROTECTED_FILES = {"__init__.py", "conftest.py", "test_bugs.py", "test_forms.py"}',
        ),
    ],
}


def main():
    root = Path.cwd()
    plan, problems = {}, []

    for filename, edits in EDITS.items():
        path = root / filename
        if not path.exists():
            problems.append(f"{filename}: not found (run this from the project root)")
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new in edits:
            if new in text:
                continue                      # already applied
            count = text.count(old)
            if count != 1:
                problems.append(
                    f"{filename}: expected exactly 1 match, found {count} for:\n"
                    f"    {old.strip().splitlines()[0][:80]!r}\n"
                    "    (the file was probably edited since this patch was written)")
                continue
            text = text.replace(old, new, 1)
        if text != original:
            plan[path] = (original, text)

    if problems:
        print("NOTHING WAS CHANGED. Problems found:\n")
        print("\n".join(problems))
        sys.exit(1)

    if not plan:
        print("Already integrated - nothing to do.")
        return

    for path, (original, text) in plan.items():
        shutil.copy2(path, str(path) + ".bak_before_formtests")
        path.write_text(text, encoding="utf-8")
        print(f"patched {path.name}  (backup: {path.name}.bak_before_formtests)")
    print("\nDone. Next: python main.py   (or set FORM_TESTS=0 to disable the new step)")


if __name__ == "__main__":
    main()
