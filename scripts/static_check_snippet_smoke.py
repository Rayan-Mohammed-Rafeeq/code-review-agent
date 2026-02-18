from __future__ import annotations

import os
import sys

# Allow running as: `python scripts\static_check_snippet_smoke.py`
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.static_checks import run_static_analysis


def main() -> None:
    code = """\
def calculate_average(numbers=[]):
    total = 0
    for n in numbers:
        total += n

    return total / len(numbers)


def main():
    data = []
    print(calculate_average(data))


if __name__ == \"__main__\":
    main()
"""

    res = run_static_analysis(code=code, filename="input.py")
    print(res.flake8)


if __name__ == "__main__":
    main()
