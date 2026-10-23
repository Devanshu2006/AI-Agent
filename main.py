
import os
import sys
import shutil
import tempfile
from pathlib import Path

from agent import analyze_website
from autonomous_explorer import autonomous_explore
from bug_detector import (
    detect_bugs,
    generate_bug_tests,
    print_bug_summary,
    save_bug_report,
)
from code_validator import collect_validation_errors
from executor import run_tests
from failure_injector import inject_locator_failure
from generator import (
    GENERATED_ROOT,
    clean_old_generated_tests,
    create_init_files,
    generate_code_files,
    parse_json_response,
    save_test_plan,
)
from healer import heal_failed_tests
from form_test_codegen import generate_form_tests
from form_tester import run_form_tests
from flow_test_codegen import generate_flow_tests
from flow_tester import run_flow_tests


# ============================================================
# CONFIGURATION
# ============================================================

MAX_HEAL_ATTEMPTS = 2
MAX_GENERATION_ATTEMPTS = 3

ENABLE_FAILURE_INJECTION = False

MAX_EXPLORE_PAGES = 25
MAX_EXPLORE_DEPTH = 3

PROJECT_ROOT = Path(__file__).resolve().parent
GENERATED_ROOT_PATH = PROJECT_ROOT / GENERATED_ROOT


# ============================================================
# DISPLAY HELPERS
# ============================================================

def print_test_plan(test_plan):
    scenarios = test_plan.get("test_scenarios", [])

    print("\n========== GENERATED TEST SCENARIOS ==========")

    for scenario in scenarios:
        print(
            f"\n{scenario.get('id', '')} - "
            f"{scenario.get('title', '')}"
        )
        print(
            f"Type: {scenario.get('type', '')} | "
            f"Priority: {scenario.get('priority', '')}"
        )
        print(
            f"Expected: {scenario.get('expected_result', '')}"
        )


def print_final_result(execution_result, bugs):
    status = execution_result.get("status", "UNKNOWN")

    print("\n" + "=" * 70)
    print("                FINAL TEST RESULT")
    print("=" * 70)

    print(f"\nStatus  : {status}")
    print(f"Passed  : {execution_result.get('passed', 0)}")
    print(f"Failed  : {execution_result.get('failed', 0)}")
    print(f"Errors  : {execution_result.get('errors', 0)}")
    print(f"Skipped : {execution_result.get('skipped', 0)}")
    print(f"XFailed : {execution_result.get('xfailed', 0)}")
    print(f"Bug findings: {len(bugs)}")

    print(
        "\nSUCCESS: All executed tests passed."
        if status == "PASSED"
        else "\nRESULT: Some tests need investigation."
    )


# ============================================================
# SAFE SUITE BACKUP / RESTORE
# ============================================================

def backup_generated_suite():
    """
    Preserve the currently working page objects and tests
    before replacing the generated suite.
    """

    backup_root = Path(
        tempfile.mkdtemp(prefix="ai_agent_suite_backup_")
    )

    saved_anything = False

    for folder_name in ("pages", "tests"):
        source = GENERATED_ROOT_PATH / folder_name
        destination = backup_root / folder_name

        if source.exists():
            shutil.copytree(source, destination)
            saved_anything = True

    return backup_root, saved_anything


def restore_generated_suite(backup_root):
    """
    Restore the previous generated pages and tests.
    This is called when generation or validation fails.
    """

    for folder_name in ("pages", "tests"):
        current = GENERATED_ROOT_PATH / folder_name
        saved = backup_root / folder_name

        if current.exists():
            shutil.rmtree(current)

        if saved.exists():
            shutil.copytree(saved, current)

    print(
        "\n[Agent] Previous generated suite restored."
    )


def remove_backup(backup_root):
    if backup_root and backup_root.exists():
        shutil.rmtree(backup_root, ignore_errors=True)


# ============================================================
# GENERATION VALIDATION
# ============================================================

def get_generated_file_types(written_files):
    """
    Accept paths such as:
      generated_tests/pages/home_page.py
      generated_tests\\pages\\home_page.py
      pages/home_page.py
      tests/test_home.py
    """

    has_pages = False
    has_tests = False

    for file_path in written_files or []:
        normalized = str(file_path).replace("\\", "/")
        normalized = normalized.removeprefix("./")
        normalized = normalized.lstrip("/")

        if normalized.startswith("generated_tests/"):
            normalized = normalized[len("generated_tests/"):]

        parts = normalized.split("/")

        if len(parts) < 2 or not normalized.endswith(".py"):
            continue

        if parts[0] == "pages":
            has_pages = True

        elif parts[0] == "tests":
            has_tests = True

    return has_pages, has_tests


def build_suite(website_data, bugs):
    """
    Generate and validate a suite with retries.

    The previously working suite is backed up before generation.
    If all generation attempts fail, the previous suite is restored.
    """

    feedback = None
    backup_root = None
    generation_succeeded = False

    try:
        for attempt in range(
            1, MAX_GENERATION_ATTEMPTS + 1
        ):
            print(
                "\n========== "
                f"AI GENERATION ATTEMPT "
                f"{attempt}/{MAX_GENERATION_ATTEMPTS} "
                "=========="
            )

            try:
                raw_plan = analyze_website(
                    website_data,
                    bugs=bugs,
                    feedback=feedback,
                )

                plan = parse_json_response(raw_plan)

            except (ValueError, TypeError) as error:
                print(
                    f"[Agent] Invalid AI response: {error}"
                )

                feedback = (
                    "Return a valid JSON test plan. "
                    f"Previous response error: {error}"
                )
                continue

            except RuntimeError as error:
                print(
                    f"[Agent] AI planning failed: {error}"
                )

                feedback = str(error)
                continue

            if not isinstance(plan, dict):
                feedback = (
                    "Return the test plan as a JSON object."
                )
                continue

            scenarios = plan.get("test_scenarios")

            if not isinstance(scenarios, list) or not scenarios:
                print(
                    "[Agent] No usable test scenarios returned."
                )

                feedback = (
                    "Include a non-empty test_scenarios list."
                )
                continue

            # Save the first known-good suite before replacing it.
            if backup_root is None:
                backup_root, _ = backup_generated_suite()

            save_test_plan(plan)
            print_test_plan(plan)

            print(
                "\n========== PREPARING GENERATED SUITE =========="
            )

            # Only clean after a plan exists.
            clean_old_generated_tests()
            create_init_files()

            print(
                "\n========== GENERATING PAGE OBJECTS AND TESTS =========="
            )

            try:
                written = generate_code_files(plan)

                has_pages, has_tests = (
                    get_generated_file_types(written)
                )

                if not has_pages or not has_tests:
                    raise ValueError(
                        "Generation must produce at least one "
                        "pages/<name>.py file and one "
                        "tests/test_<name>.py file."
                    )

                # Bug tests are generated by the local detector,
                # not by the AI planner.
                generate_bug_tests(bugs)

                # Deterministic form tests (verified expected vs actual).
                generate_form_tests(website_data.get("form_tests"))

                # Deterministic user-journey tests (verified flows).
                generate_flow_tests(website_data.get("flow_tests"))

                errors = collect_validation_errors()

                if errors:
                    raise ValueError(
                        "Generated code validation failed:\n"
                        + "\n".join(
                            str(error) for error in errors[:15]
                        )
                    )

                print(
                    "\n[Agent] Generated suite validated successfully."
                )

                generation_succeeded = True
                return plan

            except Exception as error:
                print(
                    "\n[Agent] Generation/validation failed:"
                )
                print(error)

                feedback = (
                    "Fix the previous generated suite. "
                    "Ensure valid paths, imports, Python syntax, "
                    "Page Objects, and pytest tests. "
                    "Validation feedback:\n"
                    + str(error)[:4000]
                )

                # The next attempt will regenerate the suite.
                continue

        print(
            "\n[Agent] All generation attempts failed."
        )

        return None

    finally:
        if backup_root is not None:
            if not generation_succeeded:
                restore_generated_suite(backup_root)

            remove_backup(backup_root)


# ============================================================
# BUG REPORTING
# ============================================================

def record_app_bug(
    bugs,
    website_url,
    execution_result,
    healing_result,
):
    """Record an application bug only when the healer classifies it."""

    bug = {
        "id": f"BUG{len(bugs) + 1:03d}",
        "category": "functional_failure",
        "severity": "High",
        "title": (
            "Potential application bug detected during testing"
        ),
        "url": website_url,
        "stage": "needs_triage",
        "requires_auth": False,
        "evidence": [
            healing_result.get("root_cause", "")
        ] + [
            detail.get("test", "")
            for detail in execution_result.get(
                "failure_details", []
            )[:3]
        ],
        "expected": (
            "Review the failed assertions, logs, and screenshots "
            "before confirming this as a real application bug."
        ),
    }

    bugs.append(bug)
    save_bug_report(bugs, website_url)

    print(
        f"\n[Bugs] {bug['id']} recorded for manual triage."
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    print("\n" + "=" * 70)
    print("             AI AUTONOMOUS TEST AGENT")
    print("=" * 70)

    print(
        "\nPipeline: explore -> detect bugs -> plan -> generate "
        "-> validate -> execute -> heal -> report"
    )

    if len(sys.argv) > 1:
        website_url = sys.argv[1].strip()
    else:
        website_url = input(
            "\nEnter website URL: "
        ).strip()

    if not website_url:
        print("\n[Agent] URL cannot be empty.")
        return False

    # STEP 1: EXPLORE
    print(
        "\n========== STEP 1: WEBSITE EXPLORATION =========="
    )

    try:
        website_data = autonomous_explore(
            website_url,
            max_pages=MAX_EXPLORE_PAGES,
            max_depth=MAX_EXPLORE_DEPTH,
        )
    except Exception as error:
        print(
            f"\n[Agent] Exploration failed: {error}"
        )
        return False

    if (
        not isinstance(website_data, dict)
        or not website_data.get("pages")
    ):
        print(
            "\n[Agent] No pages were successfully explored."
        )
        return False

    effective_url = (
        website_data.get("website") or website_url
    )

    print(
        f"\n[Agent] Explored pages: "
        f"{len(website_data['pages'])}"
    )

    # STEP 2: DETECT BUGS
    print(
        "\n========== STEP 2: BUG DETECTION =========="
    )

    try:
        bugs = detect_bugs(website_data) or []
        save_bug_report(bugs, effective_url)
        print_bug_summary(bugs)

    except Exception as error:
        print(
            f"\n[Agent] Bug detection failed: {error}"
        )
        return False

    # STEP 2b: LIVE FORM TESTING (expected vs actual)
    website_data["form_tests"] = None
    if os.getenv("FORM_TESTS", "1") == "1":
        print(
            "\n========== STEP 2b: LIVE FORM TESTING =========="
        )
        try:
            form_results = run_form_tests(website_data)
            website_data["form_tests"] = form_results
            for form_bug in form_results.get("bugs", []):
                form_bug["id"] = f"BUG{len(bugs) + 1:03d}"
                bugs.append(form_bug)
            if form_results.get("bugs"):
                save_bug_report(bugs, effective_url)
        except Exception as error:
            print(
                f"\n[Agent] Form testing failed (continuing): {error}"
            )

    # STEP 2c: USER-JOURNEY (FLOW) TESTING
    website_data["flow_tests"] = None
    if os.getenv("FLOW_TESTS", "1") == "1":
        print(
            "\n========== STEP 2c: USER-JOURNEY TESTING =========="
        )
        try:
            flow_results = run_flow_tests(website_data)
            website_data["flow_tests"] = flow_results
            for flow_bug in flow_results.get("bugs", []):
                flow_bug["id"] = f"BUG{len(bugs) + 1:03d}"
                bugs.append(flow_bug)
            if flow_results.get("bugs"):
                save_bug_report(bugs, effective_url)
        except Exception as error:
            print(
                f"\n[Agent] Flow testing failed (continuing): {error}"
            )

    # STEP 3: PLAN + GENERATE + VALIDATE
    print(
        "\n========== STEP 3: TEST GENERATION =========="
    )

    suite = build_suite(website_data, bugs)

    if suite is None:
        print(
            "\n[Agent] No valid new suite was generated. "
            "The previous generated suite, if present, "
            "has been restored."
        )
        print(
            "[Agent] Check test_plan.json, website_map.json, "
            "and the generation errors above."
        )
        return False

    # STEP 4: OPTIONAL FAILURE INJECTION
    if ENABLE_FAILURE_INJECTION:
        print(
            "\n========== FAILURE INJECTION =========="
        )

        try:
            if not inject_locator_failure():
                print(
                    "[Agent] Failure injection was unsuccessful."
                )
        except Exception as error:
            print(
                f"[Agent] Failure injection error: {error}"
            )

    # STEP 5: EXECUTION
    print(
        "\n========== STEP 4: TEST EXECUTION =========="
    )

    try:
        execution_result = run_tests(attempt=0)
    except Exception as error:
        print(
            f"\n[Agent] Test execution failed: {error}"
        )
        return False

    if not isinstance(execution_result, dict):
        print(
            "[Agent] Executor returned an invalid result."
        )
        return False

    # STEP 6: SELF-HEALING
    healing_attempt = 0
    last_healing = {}

    while (
        execution_result.get("status") != "PASSED"
        and healing_attempt < MAX_HEAL_ATTEMPTS
    ):
        healing_attempt += 1

        print("\n" + "=" * 70)
        print(
            "          SELF-HEALING ATTEMPT "
            f"{healing_attempt}/{MAX_HEAL_ATTEMPTS}"
        )
        print("=" * 70)

        try:
            last_healing = heal_failed_tests(
                website_data,
                execution_result,
                healing_attempt,
            ) or {}

        except Exception as error:
            print(
                f"[Agent] Self-healing error: {error}"
            )
            break

        if not last_healing.get("healed"):
            print(
                "\n[Agent] Healing did not produce a verified fix."
            )
            break

        print(
            "\n[Agent] Healing reported success. "
            "Rerunning tests for verification..."
        )

        try:
            execution_result = run_tests(
                attempt=healing_attempt
            )
        except Exception as error:
            print(
                f"[Agent] Rerun failed: {error}"
            )
            break

        if not isinstance(execution_result, dict):
            print(
                "[Agent] Executor returned an invalid rerun result."
            )
            return False

    # STEP 7: BUG TRIAGE
    if (
        execution_result.get("status") != "PASSED"
        and last_healing.get("failure_category")
        == "application_bug"
    ):
        record_app_bug(
            bugs,
            effective_url,
            execution_result,
            last_healing,
        )

    # STEP 8: FINAL REPORT
    print_final_result(execution_result, bugs)

    return execution_result.get("status") == "PASSED"


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n[Agent] Interrupted by user.")
        sys.exit(130)

    except Exception as error:
        print(
            f"\n[Agent] Unexpected fatal error: {error}"
        )
        sys.exit(1)
