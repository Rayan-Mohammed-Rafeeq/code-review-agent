import os

import pytest


def test_frontend_reviewcode_filename_mapping_mentions_java_extension():
    """Regression test for the bug where the frontend sent filename=input.java.

    The frontend can't infer the public class name, but it must at least use the
    correct language extension mapping rather than `input.${language}`.
    """
    path = os.path.join(os.path.dirname(__file__), os.pardir, "frontend", "client", "services", "api.ts")
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()

    assert "extByLang" in txt
    assert "java: 'java'" in txt
    assert "rust: 'rs'" in txt
    assert "go: 'go'" in txt


@pytest.mark.parametrize(
    "language,expected_ext",
    [
        ("javascript", "js"),
        ("typescript", "ts"),
        ("java", "java"),
        ("csharp", "cs"),
        ("go", "go"),
        ("rust", "rs"),
    ],
)
def test_frontend_language_map_contains_expected_extensions(language: str, expected_ext: str):
    path = os.path.join(os.path.dirname(__file__), os.pardir, "frontend", "client", "services", "api.ts")
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()

    assert f"{language}: '{expected_ext}'" in txt
