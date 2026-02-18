import pytest

from app.calculate_average_example import calculate_average


def test_calculate_average_happy_path() -> None:
    assert calculate_average([1, 2, 3]) == 2.0


def test_calculate_average_empty_raises() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        calculate_average([])


def test_calculate_average_no_mutable_default_state_leak() -> None:
    # Calling with no args shouldn't share state between calls.
    with pytest.raises(ValueError):
        calculate_average()
    with pytest.raises(ValueError):
        calculate_average()
