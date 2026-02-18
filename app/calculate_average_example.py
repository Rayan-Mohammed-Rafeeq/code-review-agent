"""Small example module used by docs/tests.

This intentionally stays tiny but demonstrates common static-analysis gotchas:
- mutable default arguments
- division by zero on empty input

Note: the standard guard `if __name__ == "__main__":` is correct Python and should not
be flagged as an undefined name in normal linting.
"""

from __future__ import annotations

from typing import Iterable


def calculate_average(numbers: Iterable[float] | None = None) -> float:
    """Return the arithmetic mean of *numbers*.

    Raises:
        ValueError: if *numbers* is empty.
    """

    if numbers is None:
        numbers = []

    total = 0.0
    count = 0
    for n in numbers:
        total += float(n)
        count += 1

    if count == 0:
        raise ValueError("numbers must not be empty")

    return total / count


def main() -> None:
    data = []
    # Example usage. (If you run this file directly, it will raise on empty input.)
    print(calculate_average(data))


if __name__ == "__main__":
    main()
