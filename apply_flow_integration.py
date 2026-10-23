
"""Wire the FLOW tester into the pipeline. Run ONCE from the project root,
AFTER apply_integration.py (the form-testing patch):
 
    python apply_flow_integration.py
 
Changes (exact-text replacements, all-or-nothing, safe to run twice):
  main.py    "STEP 2c: USER-JOURNEY TESTING" + generate tests/test_flows.py
  agent.py   tell the LLM planner which journeys are already covered, and that a
             login-protected page legitimately redirects guests to a login page
  healer.py  protect tests/test_flows.py from "self-healing"
  generator.py  generated tests use the SAME 1440x900 window as the explorer (fixes
             'element is not visible' on responsive sites) and reserve the new test file names
Originals are saved as <file>.bak_before_flowtests.
"""
import shutil
import sys
from pathlib import Path
 
EDITS = {
    "main.py": [
        (
            "from form_tester import run_form_tests\n",
            "from form_tester import run_form_tests\n"
            "from flow_test_codegen import generate_flow_tests\n"
            "from flow_tester import run_flow_tests\n",
        ),
        (
            "    # STEP 3: PLAN + GENERATE + VALIDATE\n",
            "    # STEP 2c: USER-JOURNEY (FLOW) TESTING\n"
            "    website_data[\"flow_tests\"] = None\n"
            "    if os.getenv(\"FLOW_TESTS\", \"1\") == \"1\":\n"
            "        print(\n"
            "            \"\\n========== STEP 2c: USER-JOURNEY TESTING ==========\"\n"
            "        )\n"
            "        try:\n"
            "            flow_results = run_flow_tests(website_data)\n"
            "            website_data[\"flow_tests\"] = flow_results\n"
            "            for flow_bug in flow_results.get(\"bugs\", []):\n"
            "                flow_bug[\"id\"] = f\"BUG{len(bugs) + 1:03d}\"\n"
            "                bugs.append(flow_bug)\n"
            "            if flow_results.get(\"bugs\"):\n"
            "                save_bug_report(bugs, effective_url)\n"
            "        except Exception as error:\n"
            "            print(\n"
            "                f\"\\n[Agent] Flow testing failed (continuing): {error}\"\n"
            "            )\n"
            "\n"
            "    # STEP 3: PLAN + GENERATE + VALIDATE\n",
        ),
        (
            "                generate_form_tests(website_data.get(\"form_tests\"))\n",
            "                generate_form_tests(website_data.get(\"form_tests\"))\n"
            "\n"
            "                # Deterministic user-journey tests (verified flows).\n"
            "                generate_flow_tests(website_data.get(\"flow_tests\"))\n",
        ),
    ],
    "agent.py": [
        (
            "from form_tester import FORM_COVERAGE_RULE, summarize_form_tests\n",
            "from form_tester import FORM_COVERAGE_RULE, summarize_form_tests\n"
            "from flow_tester import FLOW_COVERAGE_RULE, summarize_flow_tests\n",
        ),
        (
            "        form_rule = FORM_COVERAGE_RULE\n",
            "        form_rule = FORM_COVERAGE_RULE\n"
            "    flow_summary = summarize_flow_tests(website_data.get(\"flow_tests\"))\n"
            "    flow_rule = \"\"\n"
            "    if flow_summary:\n"
            "        context[\"flow_tests_already_covered\"] = flow_summary\n"
            "        flow_rule = FLOW_COVERAGE_RULE\n",
        ),
        (
            "        + form_rule\n",
            "        + form_rule\n"
            "        + flow_rule\n",
        ),
    ],
    "healer.py": [
        (
            '"test_bugs.py", "test_forms.py"}',
            '"test_bugs.py", "test_forms.py", "test_flows.py"}',
        ),
    ],
    # The explorer looks at pages in a 1440x900 window; the generated tests used the
    # pytest-playwright default (1280x720), where responsive sites HIDE elements the
    # explorer saw ("element is not visible"). Make the test window match.
    "generator.py": [
        (
            "    args = dict(browser_context_args)\n",
            "    args = dict(browser_context_args)\n"
            "    args.setdefault(\"viewport\", {\"width\": 1440, \"height\": 900})  # same size the explorer used\n",
        ),
        (
            'RESERVED_FILES = {"__init__.py", "conftest.py", "test_bugs.py"}',
            'RESERVED_FILES = {"__init__.py", "conftest.py", "test_bugs.py", "test_forms.py", "test_flows.py"}',
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
                continue                              # already applied
            count = text.count(old)
            if count != 1:
                hint = ""
                if "form_tester" in old or "form_tests" in old or "test_forms" in old:
                    hint = "\n    (run apply_integration.py first - the form-testing patch is a prerequisite)"
                problems.append(
                    f"{filename}: expected exactly 1 match, found {count} for:\n"
                    f"    {old.strip().splitlines()[0][:80]!r}{hint}")
                continue
            text = text.replace(old, new, 1)
        if text != original:
            plan[path] = (original, text)
 
    if problems:
        print("NOTHING WAS CHANGED. Problems found:\n")
        print("\n".join(problems))
        sys.exit(1)
    if not plan:
        print("Flow testing is already integrated - nothing to do.")
        return
    for path, (original, text) in plan.items():
        shutil.copy2(path, str(path) + ".bak_before_flowtests")
        path.write_text(text, encoding="utf-8")
        print(f"patched {path.name}  (backup: {path.name}.bak_before_flowtests)")
    print("\nDone. Run: python main.py   (set FLOW_TESTS=0 to disable the new step)")
 
 
if __name__ == "__main__":
    main()
 
