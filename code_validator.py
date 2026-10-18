"""Validates generated Page Object / pytest files before they are executed.

Beyond syntax, this enforces a safety policy. The generated code is written by
an LLM that has read untrusted website text, and we then RUN it on this
machine, so it must not be able to touch the filesystem, shell or network:
  * imports are limited to an allow-list
  * eval/exec/open/... are rejected
  * time.sleep / wait_for_timeout / about:blank / `assert True` are rejected
  * every test must contain a real assertion
"""
import ast
import sys
from pathlib import Path

ALLOWED_MODULES = (
    "playwright", "pytest", "re", "typing", "collections", "dataclasses",
    "urllib.parse", "generated_tests",
)
FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "__import__", "input", "breakpoint"}
FORBIDDEN_ATTRIBUTES = {"sleep", "wait_for_timeout"}
ASSERTION_PREFIXES = ("assert_", "verify_", "expect_", "should_")
EXCLUDED_DIRS = {"backups", "__pycache__", ".venv", "venv", "test-output"}
SKIP_POLICY_FILES = {"conftest.py", "__init__.py"}  # written by our own code


def _module_allowed(name):
    return any(name == m or name.startswith(m + ".") for m in ALLOWED_MODULES)


def _has_assertion(function_node):
    for node in ast.walk(function_node):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "expect":
                return True
            if isinstance(func, ast.Attribute) and func.attr.startswith(ASSERTION_PREFIXES):
                return True
    return False


def _policy_issues(tree, is_test_file):
    """Return a list of (line, message)."""
    issues = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _module_allowed(alias.name):
                    issues.append((node.lineno, f"import of '{alias.name}' is not allowed"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level or not _module_allowed(module):
                issues.append((node.lineno, f"import from '{'.' * node.level}{module}' is not allowed"))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                issues.append((node.lineno, f"call to {node.func.id}() is not allowed"))
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                issues.append((node.lineno, f".{node.attr} is not allowed; use auto-waiting and expect()"))
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str) and "about:blank" in node.value:
                issues.append((node.lineno, "about:blank is not a valid test target"))
        elif isinstance(node, ast.Assert):
            if isinstance(node.test, ast.Constant) and node.test.value:
                issues.append((node.lineno, "assertion on a constant (e.g. assert True) proves nothing"))

    if is_test_file:
        tests = [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name.startswith("test")
        ]
        if not tests:
            issues.append((1, "no test functions found"))
        for function_node in tests:
            if not _has_assertion(function_node):
                issues.append((function_node.lineno, f"{function_node.name} has no assertion"))

    return issues


def validate_python_file(file_path: Path, is_test_file=False, check_policy=True):
    """Return a list of problem strings for one file (empty list = valid)."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        return [f"SyntaxError at line {exc.lineno}, column {exc.offset}: {exc.msg}"]
    except (UnicodeDecodeError, OSError) as exc:
        return [f"File could not be read: {exc}"]

    if not check_policy:
        return []
    return [f"line {line}: {msg}" for line, msg in sorted(_policy_issues(tree, is_test_file))]


def collect_validation_errors(project_dir="generated_tests"):
    """Quietly validate all active generated files. Returns 'file: problem' strings."""
    root = Path(project_dir).resolve()
    if not root.is_dir():
        return [f"Generated directory not found: {root}"]

    files = sorted(
        f for f in root.rglob("*.py")
        if not any(part in EXCLUDED_DIRS for part in f.relative_to(root).parts)
    )
    if not files:
        return ["No active Python files found to validate."]

    errors = []
    for file_path in files:
        relative = file_path.relative_to(root)
        is_test = relative.parts[0] == "tests" and file_path.name.startswith("test_")
        for problem in validate_python_file(
            file_path,
            is_test_file=is_test,
            check_policy=file_path.name not in SKIP_POLICY_FILES,
        ):
            errors.append(f"{relative.as_posix()}: {problem}")
    return errors


def validate_generated_code(project_dir="generated_tests") -> bool:
    """Validate and print a report. True when every file is valid and policy-clean."""
    print("\n" + "=" * 65)
    print("             GENERATED CODE VALIDATION")
    print("=" * 65)

    errors = collect_validation_errors(project_dir)
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        print("-" * 65)
        print(f"[BLOCKED] {len(errors)} problem(s) found. Fix them before running the tests.")
        print("=" * 65)
        return False

    print("[SUCCESS] All generated Python files passed validation.")
    print("=" * 65)
    return True


if __name__ == "__main__":
    sys.exit(0 if validate_generated_code() else 1)
