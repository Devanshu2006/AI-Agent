import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

from agent import analyze_failure


GENERATED_ROOT = "generated_tests"

ALLOWED_DIRECTORIES = (
    os.path.join(
        GENERATED_ROOT,
        "pages"
    ),
    os.path.join(
        GENERATED_ROOT,
        "tests"
    )
)


# ============================================================
# COLLECT GENERATED PYTHON FILES
# ============================================================

def collect_generated_files():

    generated_files = []

    for root, _, files in os.walk(
        GENERATED_ROOT
    ):

        if "backups" in root:
            continue

        for filename in files:

            if not filename.endswith(".py"):
                continue

            path = os.path.join(
                root,
                filename
            )

            generated_files.append(
                path
            )

    return generated_files


# ============================================================
# READ GENERATED FILES
# ============================================================

def read_generated_files():

    result = {}

    for file_path in collect_generated_files():

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                result[file_path] = file.read()

        except Exception as e:

            print(
                f"[Healer] Could not read "
                f"{file_path}: {e}"
            )

    return result


# ============================================================
# PATH VALIDATION
# ============================================================

def is_allowed_file(file_path):

    normalized = os.path.normpath(
        file_path
    )

    for allowed_directory in ALLOWED_DIRECTORIES:

        allowed_normalized = os.path.normpath(
            allowed_directory
        )

        if (
            normalized.startswith(
                allowed_normalized
                + os.sep
            )
        ):

            return True

    return False


# ============================================================
# BACKUP
# ============================================================

def backup_generated_files(
    attempt
):

    backup_directory = os.path.join(
        GENERATED_ROOT,
        "backups",
        f"attempt_{attempt}"
    )

    os.makedirs(
        backup_directory,
        exist_ok=True
    )

    backed_up_files = []

    for file_path in collect_generated_files():

        relative_path = os.path.relpath(
            file_path,
            GENERATED_ROOT
        )

        backup_path = os.path.join(
            backup_directory,
            relative_path
        )

        os.makedirs(
            os.path.dirname(
                backup_path
            ),
            exist_ok=True
        )

        shutil.copy2(
            file_path,
            backup_path
        )

        backed_up_files.append(
            backup_path
        )

    print(
        f"\n[Healer] Backup created:"
        f" {backup_directory}"
    )

    return backup_directory


# ============================================================
# RESTORE BACKUP
# ============================================================

def restore_backup(
    backup_directory
):

    if not os.path.exists(
        backup_directory
    ):

        print(
            "[Healer] Backup directory "
            "does not exist."
        )

        return False

    for root, _, files in os.walk(
        backup_directory
    ):

        for filename in files:

            backup_path = os.path.join(
                root,
                filename
            )

            relative_path = os.path.relpath(
                backup_path,
                backup_directory
            )

            target_path = os.path.join(
                GENERATED_ROOT,
                relative_path
            )

            os.makedirs(
                os.path.dirname(
                    target_path
                ),
                exist_ok=True
            )

            shutil.copy2(
                backup_path,
                target_path
            )

    print(
        "[Healer] Previous generated code restored."
    )

    return True


# ============================================================
# APPLY PATCH
# ============================================================

def apply_patch(
    patch
):

    file_path = patch.get(
        "file",
        ""
    )

    operation = patch.get(
        "operation",
        ""
    )

    old_text = patch.get(
        "old_text",
        ""
    )

    new_text = patch.get(
        "new_text",
        ""
    )

    if not is_allowed_file(
        file_path
    ):

        return False, (
            "File is outside allowed "
            "generated directories."
        )

    if operation != "replace":

        return False, (
            "Only replace operation is allowed."
        )

    if not old_text:

        return False, (
            "old_text is empty."
        )

    if not os.path.exists(
        file_path
    ):

        return False, (
            "Target file does not exist."
        )

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()

    except Exception as e:

        return False, str(e)

    occurrence_count = content.count(
        old_text
    )

    if occurrence_count != 1:

        return False, (
            "old_text must occur exactly once. "
            f"Found: {occurrence_count}"
        )

    new_content = content.replace(
        old_text,
        new_text,
        1
    )

    try:

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                new_content
            )

    except Exception as e:

        return False, str(e)

    print(
        f"[Healer] Patch applied:"
        f" {file_path}"
    )

    return True, "Patch applied successfully."


# ============================================================
# SYNTAX VALIDATION
# ============================================================

def validate_generated_code():

    print(
        "\n[Healer] Validating generated Python..."
    )

    command = [
        sys.executable,
        "-m",
        "compileall",
        "-q",
        GENERATED_ROOT
    ]

    process = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if process.returncode == 0:

        print(
            "[Healer] Syntax validation PASSED."
        )

        return True

    print(
        "[Healer] Syntax validation FAILED."
    )

    print(
        process.stdout
    )

    print(
        process.stderr
    )

    return False


# ============================================================
# SAVE HEALING REPORT
# ============================================================

def save_healing_report(
    attempt,
    result
):

    report_path = os.path.join(
        GENERATED_ROOT,
        f"healing_report_attempt_{attempt}.json"
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
        f"[Healer] Healing report saved:"
        f" {report_path}"
    )


# ============================================================
# MAIN HEALING FUNCTION
# ============================================================

def heal_failed_tests(
    website_data,
    execution_result,
    attempt
):

    print(
        f"\n========== STEP 6: AI SELF HEALING "
        f"(ATTEMPT {attempt}) =========="
    )

    # --------------------------------------------------------
    # CHECK WHETHER THERE IS ACTUALLY A FAILURE
    # --------------------------------------------------------

    if (
        execution_result.get("failed", 0) == 0
        and
        execution_result.get("errors", 0) == 0
    ):

        print(
            "\n[Healer] No failures detected."
        )

        result = {
            "safe_to_auto_heal": False,
            "healed": False,
            "reason": "No failures"
        }

        save_healing_report(
            attempt,
            result
        )

        return result

    # --------------------------------------------------------
    # READ GENERATED CODE
    # --------------------------------------------------------

    generated_files = read_generated_files()

    # --------------------------------------------------------
    # ASK AI TO ANALYZE FAILURE
    # --------------------------------------------------------

    print(
        "\n[Healer] Sending failure to AI..."
    )

    try:

        ai_response = analyze_failure(
            website_data,
            execution_result,
            generated_files
        )

    except Exception as e:

        print(
            f"\n[Healer] AI analysis failed:"
            f" {e}"
        )

        result = {
            "safe_to_auto_heal": False,
            "healed": False,
            "reason": f"AI analysis failed: {e}"
        }

        save_healing_report(
            attempt,
            result
        )

        return result

    # --------------------------------------------------------
    # CLEAN AI RESPONSE
    # --------------------------------------------------------

    ai_response = ai_response.strip()

    if ai_response.startswith(
        "```json"
    ):

        ai_response = ai_response[7:]

    elif ai_response.startswith(
        "```"
    ):

        ai_response = ai_response[3:]

    if ai_response.endswith(
        "```"
    ):

        ai_response = ai_response[:-3]

    ai_response = ai_response.strip()

    # --------------------------------------------------------
    # PARSE AI JSON
    # --------------------------------------------------------

    try:

        healing_plan = json.loads(
            ai_response
        )

    except json.JSONDecodeError as e:

        print(
            "\n[Healer] AI returned invalid JSON."
        )

        print(e)

        print(
            "\nAI response:"
        )

        print(ai_response)

        result = {
            "safe_to_auto_heal": False,
            "healed": False,
            "reason": "Invalid AI healing response",
            "ai_response": ai_response
        }

        save_healing_report(
            attempt,
            result
        )

        return result

    print(
        "\n[Healer] AI diagnosis:"
    )

    print(
        healing_plan.get(
            "root_cause",
            "Unknown"
        )
    )

    print(
        "\n[Healer] Failure category:"
    )

    print(
        healing_plan.get(
            "failure_category",
            "Unknown"
        )
    )

    print(
        "\n[Healer] Confidence:"
    )

    print(
        healing_plan.get(
            "confidence",
            "Unknown"
        )
    )

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    if not healing_plan.get(
        "safe_to_auto_heal",
        False
    ):

        print(
            "\n[Healer] AI marked this failure "
            "as unsafe to auto-heal."
        )

        result = {
            **healing_plan,
            "healed": False
        }

        save_healing_report(
            attempt,
            result
        )

        return result

    patches = healing_plan.get(
        "patches",
        []
    )

    if not patches:

        print(
            "\n[Healer] No patches proposed."
        )

        result = {
            **healing_plan,
            "healed": False
        }

        save_healing_report(
            attempt,
            result
        )

        return result

    # --------------------------------------------------------
    # CREATE BACKUP
    # --------------------------------------------------------

    backup_directory = backup_generated_files(
        attempt
    )

    applied_patches = []

    # --------------------------------------------------------
    # APPLY ALL PATCHES
    # --------------------------------------------------------

    for patch in patches:

        success, message = apply_patch(
            patch
        )

        if not success:

            print(
                f"\n[Healer] Patch rejected:"
                f" {message}"
            )

            restore_backup(
                backup_directory
            )

            result = {
                **healing_plan,
                "healed": False,
                "reason": message,
                "applied_patches": []
            }

            save_healing_report(
                attempt,
                result
            )

            return result

        applied_patches.append(
            patch
        )

    # --------------------------------------------------------
    # VALIDATE PATCH
    # --------------------------------------------------------

    syntax_valid = validate_generated_code()

    if not syntax_valid:

        print(
            "\n[Healer] Invalid patch detected."
        )

        restore_backup(
            backup_directory
        )

        result = {
            **healing_plan,
            "healed": False,
            "reason": "Patch failed syntax validation",
            "applied_patches": applied_patches
        }

        save_healing_report(
            attempt,
            result
        )

        return result

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    print(
        "\n[Healer] Patch validated successfully."
    )

    print(
        "[Healer] Ready for test rerun."
    )

    result = {
        **healing_plan,
        "healed": True,
        "backup_directory": backup_directory,
        "applied_patches": applied_patches,
        "timestamp": datetime.now().isoformat()
    }

    save_healing_report(
        attempt,
        result
    )

    return result