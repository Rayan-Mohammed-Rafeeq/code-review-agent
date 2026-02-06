from app.compressor import compress_python_code


def test_compress_strips_docstring_and_comments():
    code = '''
"""module doc"""

# comment

def f(x: int) -> int:
    """doc"""
    # inside
    if x > 0:
        return x
    return -x
'''
    out = compress_python_code(code).text
    assert "module doc" not in out
    assert "# comment" not in out
    assert "\"\"\"doc\"\"\"" not in out
    assert "def f" in out
    assert "if x > 0" in out


def test_compress_emits_imports_and_external_calls():
    code = '''
import os
from requests import get

def g(url: str):
    r = get(url)
    os.path.join("a", "b")
    print(r)
    return r
'''
    out = compress_python_code(code).text
    assert "import os" in out
    assert "from requests import get" in out
    assert "def g(url" in out
    assert "call get" in out
    assert "call os.path.join" in out
    assert "call print" not in out
