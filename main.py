from browser import inspect_website

from agent import analyze_website

from generator import (
    create_init_files,
    save_test_plan,
    generate_code_files,
    clean_old_generated_tests
)

from executor import run_tests

from healer import heal_failed_tests

from failure_injector import (
    inject_locator_failure
)


MAX_HEAL_ATTEMPTS = 2

ENABLE_FAILURE_INJECTION = True


def print_header():

    print(
        "\n"
        "============================================================\n"
        "              AI AUTONOMOUS TEST AGENT\n"
        "============================================================"
    )


def main():

    print_header()

    print(
        "\nCapabilities:"
    )

    print(
        "1. Browser inspection"
    )

    print(
        "2. AI test planning"
    )

    print(
        "3. Playwright + pytest generation"
    )

    print(
        "4. Page Object Model"
    )

    print(
        "5. Automatic test execution"
    )

    print(
        "6. AI failure analysis"
    )

    print(
        "7. Safe automatic healing"
    )

    print(
        "8. Patch validation"
    )

    print(
        "9. Automatic rerun"
    )

    print(
        "\n------------------------------------------------------------"
    )

    url = input(
        "\nEnter website URL: "
    ).strip()

    if not url:

        print(
            "\n[Main] URL is required."
        )

        return

    # ========================================================
    # STEP 0
    # ========================================================

    print(
        "\n========== STEP 0: INITIALIZATION =========="
    )

    create_init_files()

    # ========================================================
    # STEP 1
    # ========================================================

    print(
        "\n========== STEP 1: BROWSER INSPECTION =========="
    )

    try:

        website_data = inspect_website(
            url
        )

    except Exception as e:

        print(
            f"\n[Main] Browser inspection failed:"
            f" {e}"
        )

        return

    print(
        f"\nWebsite: "
        f"{website_data.get('url')}"
    )

    print(
        f"Title: "
        f"{website_data.get('title')}"
    )

    print(
        f"Interactive elements: "
        f"{len(website_data.get('elements', []))}"
    )

    print(
        f"Forms: "
        f"{len(website_data.get('forms', []))}"
    )

    # ========================================================
    # STEP 2
    # ========================================================

    print(
        "\n========== STEP 2: AI WEBSITE ANALYSIS =========="
    )

    try:

        ai_response = analyze_website(
            website_data
        )

    except Exception as e:

        print(
            f"\n[Main] AI analysis failed:"
            f" {e}"
        )

        return

    # ========================================================
    # STEP 3
    # ========================================================

    print(
        "\n========== STEP 3: TEST PLAN GENERATION =========="
    )

    test_data = save_test_plan(
        ai_response
    )

    if not test_data:

        print(
            "\n[Main] Test plan generation failed."
        )

        return

    scenarios = test_data.get(
        "test_scenarios",
        []
    )

    print(
        "\nGenerated scenarios:"
    )

    for scenario in scenarios:

        print(
            f"\n{scenario.get('id')} - "
            f"{scenario.get('title')}"
        )

        print(
            f"Type: "
            f"{scenario.get('type')}"
        )

        print(
            f"Priority: "
            f"{scenario.get('priority')}"
        )

    # ========================================================
    # STEP 4
    # ========================================================

    print(
        "\n========== STEP 4: CODE GENERATION =========="
    )

    clean_old_generated_tests()

    generated_files = generate_code_files(
        test_data
    )

    print(
        "\nGenerated files:"
    )

    for file_path in generated_files:

        print(
            file_path
        )

    print(
        "\nScreenshot:"
    )

    print(
        "website.png"
    )

    # ========================================================
    # OPTIONAL FAILURE INJECTION
    # ========================================================

    if ENABLE_FAILURE_INJECTION:

        print(
            "\n"
            "============================================================"
        )

        print(
            "       CONTROLLED SELF-HEALING DEMONSTRATION"
        )

        print(
            "============================================================"
        )

        injected = inject_locator_failure()

        if not injected:

            print(
                "\n[Main] Failure injection failed."
            )

            print(
                "[Main] Running normal test execution."
            )

    # ========================================================
    # STEP 5
    # ========================================================

    execution_result = run_tests(
        attempt=0
    )

    # ========================================================
    # SELF HEALING LOOP
    # ========================================================

    for attempt in range(
        1,
        MAX_HEAL_ATTEMPTS + 1
    ):

        if execution_result.get(
            "status"
        ) == "PASSED":

            break

        print(
            f"\n[Main] Test suite failed."
        )

        print(
            f"[Main] Starting healing attempt "
            f"{attempt}/{MAX_HEAL_ATTEMPTS}"
        )

        healing_result = heal_failed_tests(
            website_data,
            execution_result,
            attempt
        )

        if not healing_result:

            print(
                "\n[Main] Healing process returned no result."
            )

            break

        if not healing_result.get(
            "healed",
            False
        ):

            print(
                "\n[Main] Automatic healing stopped."
            )

            break

        # ====================================================
        # RERUN
        # ====================================================

        print(
            "\n========== STEP 7: RERUN AFTER HEALING =========="
        )

        execution_result = run_tests(
            attempt=attempt
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "                 FINAL RESULT"
    )

    print(
        "============================================================"
    )

    print(
        f"\nStatus: "
        f"{execution_result.get('status')}"
    )

    print(
        f"Passed: "
        f"{execution_result.get('passed', 0)}"
    )

    print(
        f"Failed: "
        f"{execution_result.get('failed', 0)}"
    )

    print(
        f"Errors: "
        f"{execution_result.get('errors', 0)}"
    )

    print(
        f"Skipped: "
        f"{execution_result.get('skipped', 0)}"
    )

    if execution_result.get(
        "failed_tests"
    ):

        print(
            "\nFailed tests:"
        )

        for test in execution_result[
            "failed_tests"
        ]:

            print(
                f"- {test}"
            )

    print(
        "\n============================================================"
    )

    if execution_result.get(
        "status"
    ) == "PASSED":

        print(
            "\nSUCCESS: All generated tests passed."
        )

    else:

        print(
            "\nThe test suite still has unresolved failures."
        )

    print(
        "\n============================================================"
    )


if __name__ == "__main__":

    main()