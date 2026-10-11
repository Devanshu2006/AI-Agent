import shutil
import json
import os
import re


GENERATED_ROOT = "generated_tests"

def clean_old_generated_tests():
    """
    Remove old generated Page Objects and test files
    before creating a new test suite.

    Backups are preserved.
    """

    print("\n========== CLEANING OLD GENERATED TESTS ==========")

    pages_dir = os.path.join(GENERATED_ROOT, "pages")
    tests_dir = os.path.join(GENERATED_ROOT, "tests")

    removed_files = []

    # Clean old Page Object files
    if os.path.exists(pages_dir):
        for filename in os.listdir(pages_dir):
            file_path = os.path.join(pages_dir, filename)

            # Keep __init__.py
            if filename == "__init__.py":
                continue

            if os.path.isfile(file_path) and filename.endswith(".py"):
                os.remove(file_path)
                removed_files.append(file_path)

    # Clean old test files
    if os.path.exists(tests_dir):
        for filename in os.listdir(tests_dir):
            file_path = os.path.join(tests_dir, filename)

            # Keep __init__.py
            if filename == "__init__.py":
                continue

            if os.path.isfile(file_path) and filename.endswith(".py"):
                os.remove(file_path)
                removed_files.append(file_path)

    if removed_files:
        for file_path in removed_files:
            print(f"[Cleaner] Removed: {file_path}")

        print(
            f"[Cleaner] Removed {len(removed_files)} old generated file(s)."
        )
    else:
        print("[Cleaner] No old generated test files found.")

    print("[Cleaner] Backups were preserved.")

def clean_json_response(response):

    response = response.strip()

    if response.startswith("```json"):
        response = response[7:]

    elif response.startswith("```"):
        response = response[3:]

    if response.endswith("```"):
        response = response[:-3]

    return response.strip()


def save_test_plan(ai_response):

    ai_response = clean_json_response(
        ai_response
    )

    try:

        test_data = json.loads(
            ai_response
        )

    except json.JSONDecodeError as e:

        print(
            "\n[Generator] Invalid JSON returned by AI."
        )

        print(e)

        print("\nAI response:")
        print(ai_response)

        return None

    os.makedirs(
        GENERATED_ROOT,
        exist_ok=True
    )

    plan_path = os.path.join(
        GENERATED_ROOT,
        "test_plan.json"
    )

    with open(
        plan_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            test_data,
            file,
            indent=4
        )

    print(
        f"\n[Generator] Test plan saved:"
        f" {plan_path}"
    )

    return test_data


def sanitize_path(relative_path):

    relative_path = relative_path.replace(
        "\\",
        "/"
    )

    if relative_path.startswith("/"):
        raise ValueError(
            "Absolute paths are not allowed."
        )

    if ".." in relative_path.split("/"):
        raise ValueError(
            "Parent directory traversal is not allowed."
        )

    if not (
        relative_path.startswith("pages/")
        or
        relative_path.startswith("tests/")
    ):

        raise ValueError(
            "Generated files must be inside "
            "pages/ or tests/."
        )

    return relative_path


def normalize_generated_imports(
    code,
    file_type
):

    if file_type == "test":

        code = re.sub(
            r"from\s+pages\.([a-zA-Z0-9_]+)\s+import",
            r"from generated_tests.pages.\1 import",
            code
        )

        code = re.sub(
            r"(?<!generated_tests\.)import\s+pages\.",
            "import generated_tests.pages.",
            code
        )

    return code


def create_init_files():

    directories = [
        GENERATED_ROOT,
        os.path.join(
            GENERATED_ROOT,
            "pages"
        ),
        os.path.join(
            GENERATED_ROOT,
            "tests"
        )
    ]

    for directory in directories:

        os.makedirs(
            directory,
            exist_ok=True
        )

    init_files = [

        os.path.join(
            GENERATED_ROOT,
            "__init__.py"
        ),

        os.path.join(
            GENERATED_ROOT,
            "pages",
            "__init__.py"
        ),

        os.path.join(
            GENERATED_ROOT,
            "tests",
            "__init__.py"
        )
    ]

    for init_file in init_files:

        if not os.path.exists(
            init_file
        ):

            with open(
                init_file,
                "w",
                encoding="utf-8"
            ) as file:

                file.write("")


def generate_code_files(
    test_data
):

    generated_files = []

    files = test_data.get(
        "files",
        []
    )

    for file_info in files:

        relative_path = file_info.get(
            "path",
            ""
        )

        code = file_info.get(
            "code",
            ""
        )

        file_type = file_info.get(
            "type",
            ""
        )

        if not relative_path:
            continue

        if not code:
            continue

        try:

            relative_path = sanitize_path(
                relative_path
            )

        except ValueError as e:

            print(
                f"\n[Generator] Skipping file:"
                f" {e}"
            )

            continue

        code = code.strip()

        if code.startswith(
            "```python"
        ):

            code = code[9:]

        elif code.startswith(
            "```"
        ):

            code = code[3:]

        if code.endswith(
            "```"
        ):

            code = code[:-3]

        code = code.strip()

        code = normalize_generated_imports(
            code,
            file_type
        )

        full_path = os.path.join(
            GENERATED_ROOT,
            relative_path
        )

        directory = os.path.dirname(
            full_path
        )

        os.makedirs(
            directory,
            exist_ok=True
        )

        with open(
            full_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                code
            )

        generated_files.append(
            full_path
        )

        print(
            f"[Generator] Created:"
            f" {full_path}"
        )

    return generated_files