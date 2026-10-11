import os


GENERATED_ROOT = "generated_tests"


def inject_locator_failure():

    print(
        "\n========== FAILURE INJECTION =========="
    )

    python_files = []

    for root, _, files in os.walk(
        GENERATED_ROOT
    ):

        if "backups" in root:
            continue

        for filename in files:

            if filename.endswith(".py"):

                python_files.append(
                    os.path.join(
                        root,
                        filename
                    )
                )

    if not python_files:

        print(
            "[Injector] No generated Python files found."
        )

        return False

    # --------------------------------------------------------
    # Find a Page Object file
    # --------------------------------------------------------

    page_files = [
        file_path
        for file_path in python_files
        if os.path.normpath(
            os.path.join(
                GENERATED_ROOT,
                "pages"
            )
        )
        in os.path.normpath(file_path)
    ]

    if not page_files:

        print(
            "[Injector] No Page Object found."
        )

        return False

    target_file = page_files[0]

    print(
        f"[Injector] Target:"
        f" {target_file}"
    )

    try:

        with open(
            target_file,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()

    except Exception as e:

        print(
            f"[Injector] Could not read file:"
            f" {e}"
        )

        return False

    # --------------------------------------------------------
    # Try to corrupt a common locator
    # --------------------------------------------------------

    replacements = [

        (
            'get_by_role("textbox"',
            'get_by_role("invalid_test_role"'
        ),

        (
            "get_by_role('textbox'",
            "get_by_role('invalid_test_role'"
        ),

        (
            'get_by_label("Username")',
            'get_by_label("INVALID_USERNAME_FIELD")'
        ),

        (
            "get_by_label('Username')",
            "get_by_label('INVALID_USERNAME_FIELD')"
        ),

        (
            'get_by_placeholder("Username")',
            'get_by_placeholder("INVALID_USERNAME")'
        ),

        (
            "get_by_placeholder('Username')",
            "get_by_placeholder('INVALID_USERNAME')"
        ),

        (
            'get_by_text("Username")',
            'get_by_text("INVALID_USERNAME_TEXT")'
        ),

        (
            "get_by_text('Username')",
            "get_by_text('INVALID_USERNAME_TEXT')"
        )
    ]

    for old_text, new_text in replacements:

        if old_text in content:

            broken_content = content.replace(
                old_text,
                new_text,
                1
            )

            with open(
                target_file,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(
                    broken_content
                )

            print(
                "\n[Injector] Intentional failure injected."
            )

            print(
                f"[Injector] Changed:"
            )

            print(
                f"    {old_text}"
            )

            print(
                f"    ↓"
            )

            print(
                f"    {new_text}"
            )

            return True

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    print(
        "\n[Injector] Could not find a suitable locator."
    )

    print(
        "[Injector] No changes were made."
    )

    return False