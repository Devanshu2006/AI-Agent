import subprocess
import json
import os
import re
import sys
from datetime import datetime


def run_tests(attempt=0):

    print(
        f"\n========== STEP 5: TEST EXECUTION "
        f"(ATTEMPT {attempt}) =========="
    )

    python_executable = sys.executable

    command = [
        python_executable,
        "-m",
        "pytest",
        "generated_tests/tests",
        "-v",
        "--headed",
        "--browser-channel=chrome",
        "--tb=long"
    ]

    print("\n[Executor] Python:")
    print(python_executable)

    print("\n[Executor] Running:")
    print(" ".join(command))

    process = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    stdout = process.stdout
    stderr = process.stderr

    full_output = (
        stdout
        + "\n"
        + stderr
    )

    print("\n")
    print(full_output)

    passed = 0
    failed = 0
    skipped = 0
    errors = 0

    match = re.search(
        r"(\d+)\s+passed",
        full_output
    )

    if match:
        passed = int(match.group(1))

    match = re.search(
        r"(\d+)\s+failed",
        full_output
    )

    if match:
        failed = int(match.group(1))

    match = re.search(
        r"(\d+)\s+skipped",
        full_output
    )

    if match:
        skipped = int(match.group(1))

    match = re.search(
        r"(\d+)\s+error",
        full_output
    )

    if match:
        errors = int(match.group(1))

    failed_tests = []

    failed_pattern = re.compile(
        r"(generated_tests[\\/].*?::.*?)(?:\s+FAILED|\s+ERROR)"
    )

    for match in failed_pattern.finditer(
        full_output
    ):

        test_name = match.group(1)

        if test_name not in failed_tests:

            failed_tests.append(
                test_name
            )

    if process.returncode != 0:

        if failed == 0 and errors == 0:

            errors = 1

    status = (
        "PASSED"
        if process.returncode == 0
        else "FAILED"
    )

    result = {
        "timestamp": datetime.now().isoformat(),
        "attempt": attempt,
        "python_executable": python_executable,
        "command": " ".join(command),
        "exit_code": process.returncode,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "failed_tests": failed_tests,
        "status": status,
        "stdout": stdout,
        "stderr": stderr,
        "full_output": full_output
    }

    os.makedirs(
        "generated_tests",
        exist_ok=True
    )

    if attempt == 0:

        report_name = (
            "execution_report.json"
        )

    else:

        report_name = (
            f"execution_report_attempt_{attempt}.json"
        )

    report_path = os.path.join(
        "generated_tests",
        report_name
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=4
        )

    print(
        f"\n[Executor] Report saved:"
        f" {report_path}"
    )

    return result