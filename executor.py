import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated_tests"
TESTS_DIR = GENERATED_DIR / "tests"

HEADED = os.getenv("TEST_HEADED", "1") == "1"
BROWSER_CHANNEL = os.getenv("BROWSER_CHANNEL", "chrome")  # "" = bundled Chromium
TEST_TIMEOUT_SECONDS = int(os.getenv("TEST_TIMEOUT_SECONDS", "900"))



def parse_test_results(xml_path, full_output):
    """Parse pytest results, keeping XPASS separate from ordinary passes."""

    result = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "failed_tests": [],
        "error_tests": [],
        "failure_details": [],
        "xpassed_tests": [],
    }

    # Detect XPASS results from pytest's verbose output.
    # Example: test_bug001_broken_page[chromium] XPASS [ 4%]
    for line in full_output.splitlines():
        if re.search(r"\bXPASS\b", line):
            result["xpassed_tests"].append(line.strip())

    # Prefer the explicit pytest summary when available.
    xpassed_summary = re.search(
        r"(\d+)\s+xpassed\b", full_output, re.IGNORECASE
    )

    if xpassed_summary:
        result["xpassed"] = int(xpassed_summary.group(1))
    else:
        result["xpassed"] = len(result["xpassed_tests"])

    if xml_path.exists():
        try:
            root = ET.parse(xml_path).getroot()

            for testcase in root.iter("testcase"):
                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped = testcase.find("skipped")

                name = (
                    f"{testcase.get('classname', '')}::"
                    f"{testcase.get('name', '')}"
                ).strip(":")

                if failure is not None or error is not None:
                    problem = failure if failure is not None else error

                    if failure is not None:
                        result["failed"] += 1
                        result["failed_tests"].append(name)
                    else:
                        result["errors"] += 1
                        result["error_tests"].append(name)

                    result["failure_details"].append({
                        "test": name,
                        "message": (problem.get("message") or "")[:500],
                        "details": (problem.text or "")[-1500:],
                    })

                elif skipped is not None:
                    if skipped.get("type") == "pytest.xfail":
                        result["xfailed"] += 1
                    else:
                        result["skipped"] += 1
                else:
                    result["passed"] += 1

            # JUnit may report non-strict XPASS as passed.
            # Move those results into their own category.
            result["passed"] = max(
                0, result["passed"] - result["xpassed"]
            )

            return result

        except (ET.ParseError, OSError) as exc:
            print(f"[Executor] Could not parse XML report: {exc}")

    # Fallback when the XML report is missing or invalid.
    patterns = {
        "passed": r"(\d+)\s+passed\b",
        "failed": r"(\d+)\s+failed\b",
        "errors": r"(\d+)\s+errors?\b",
        "skipped": r"(\d+)\s+skipped\b",
        "xfailed": r"(\d+)\s+xfailed\b",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, full_output, re.IGNORECASE)
        if match:
            result[key] = int(match.group(1))

    # In the summary-line fallback, "passed" already excludes XPASS
    # in normal pytest output, so do not subtract xpassed again.
    return result



def build_command(xml_path):
    command = [
        sys.executable, "-m", "pytest", str(TESTS_DIR),
        "-v", "--tb=short",
        f"--junitxml={xml_path}",
        "--screenshot=only-on-failure",
        f"--output={GENERATED_DIR / 'test-output'}",
    ]
    if HEADED:
        command.append("--headed")
    if BROWSER_CHANNEL:
        command.append(f"--browser-channel={BROWSER_CHANNEL}")
    return command


def run_tests(attempt=0):
    print(f"\n========== TEST EXECUTION (ATTEMPT {attempt}) ==========")

    if not TESTS_DIR.exists():
        raise FileNotFoundError(f"Generated tests directory not found: {TESTS_DIR}")

    xml_path = GENERATED_DIR / f"test_results_attempt_{attempt}.xml"
    if xml_path.exists():
        xml_path.unlink()  # never read a previous run's report

    command = build_command(xml_path)
    print("\n[Executor] Running:")
    print(subprocess.list2cmdline(command))

    base = {
        "timestamp": datetime.now().isoformat(),
        "attempt": attempt,
        "python_executable": sys.executable,
        "command": subprocess.list2cmdline(command),
    }

    try:
        process = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=TEST_TIMEOUT_SECONDS,
        )
        stdout, stderr = process.stdout or "", process.stderr or ""
        full_output = stdout + "\n" + stderr
        print("\n" + full_output)

        counts = parse_test_results(xml_path, full_output)

        execution_error = None
        if process.returncode == 5:
            execution_error = "pytest collected no tests (is every file named test_*.py?)"
        # Non-zero exit with no reported failures = collection/config/startup error.
        if process.returncode != 0 and counts["failed"] == 0 and counts["errors"] == 0:
            counts["errors"] = 1

        result = {
            **base,
            "exit_code": process.returncode,
            **counts,
            "status": "PASSED" if process.returncode == 0 else "FAILED",
            "junit_report": str(xml_path),
            "stdout": stdout,
            "stderr": stderr,
            "full_output": full_output,
        }
        if execution_error:
            result["execution_error"] = execution_error

    except subprocess.TimeoutExpired:
        message = f"pytest exceeded {TEST_TIMEOUT_SECONDS}s and was stopped"
        result = _failed_result(base, -1, message)
    except OSError as exc:
        result = _failed_result(base, -1, str(exc))

    report_name = (
        "execution_report.json" if attempt == 0
        else f"execution_report_attempt_{attempt}.json"
    )
    report_path = GENERATED_DIR / report_name
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)

    print(f"\n[Executor] Report saved: {report_path}")
    print(
        f"[Executor] Results: Passed={result['passed']}, Failed={result['failed']}, "
        f"Errors={result['errors']}, Skipped={result['skipped']}, "
        f"KnownBugs(xfail)={result['xfailed']}"
    )
    return result


def _failed_result(base, exit_code, message):
    return {
        **base,
        "exit_code": exit_code,
        "passed": 0, "failed": 0, "errors": 1, "skipped": 0, "xfailed": 0,
        "failed_tests": [], "error_tests": [], "failure_details": [],
        "status": "FAILED",
        "execution_error": message,
        "stdout": "", "stderr": message, "full_output": message,
    }
