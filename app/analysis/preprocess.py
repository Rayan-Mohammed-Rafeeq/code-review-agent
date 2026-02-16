from __future__ import annotations

import textwrap


def preprocess_code(*, code: str) -> str:
    """Basic preprocessing.

    - Normalizes newlines
    - Strips trailing whitespace
    - Dedents if the content is uniformly indented
    """
    c = code.replace("\r\n", "\n").replace("\r", "\n")
    c = "\n".join(line.rstrip() for line in c.split("\n"))
    # Dedent is safe for snippets/pasted code; no-op for regular modules.
    return textwrap.dedent(c).lstrip("\n")
