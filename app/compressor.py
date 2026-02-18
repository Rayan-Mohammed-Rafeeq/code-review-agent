from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass


@dataclass(frozen=True)
class CompressedContext:
    text: str


def compress_python_code(code: str) -> CompressedContext:
    stripped = _strip_comments(code)
    tree: ast.Module = ast.parse(stripped)
    tree = _strip_docstrings_ast(tree)  # type: ignore[assignment]

    lines: list[str] = ["# Compressed Python context"]

    for node in tree.body:
        _emit_top_level(node, lines, indent=0)

    return CompressedContext(text="\n".join(lines).strip() + "\n")


def _strip_comments(code: str) -> str:
    """Remove comment tokens while preserving spacing/newlines enough to keep code parseable."""
    tokens: list[tokenize.TokenInfo] = []
    reader = io.StringIO(code).readline

    for tok in tokenize.generate_tokens(reader):
        if tok.type == tokenize.COMMENT:
            continue
        tokens.append(tok)

    return tokenize.untokenize(tokens)


def _strip_docstrings_ast(tree: ast.AST) -> ast.AST:
    class Transformer(ast.NodeTransformer):
        def _strip_body(self, body: list[ast.stmt]) -> list[ast.stmt]:
            if not body:
                return body
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                return body[1:]
            return body

        def visit_Module(self, node: ast.Module) -> ast.AST:  # type: ignore[override]
            node.body = self._strip_body(node.body)
            self.generic_visit(node)
            return node

        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:  # type: ignore[override]
            node.body = self._strip_body(node.body)
            self.generic_visit(node)
            return node

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:  # type: ignore[override]
            node.body = self._strip_body(node.body)
            self.generic_visit(node)
            return node

        def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:  # type: ignore[override]
            node.body = self._strip_body(node.body)
            self.generic_visit(node)
            return node

    return Transformer().visit(tree)  # type: ignore[no-any-return]


def _emit_top_level(node: ast.AST, lines: list[str], indent: int) -> None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            as_part = f" as {alias.asname}" if alias.asname else ""
            lines.append(_indent(indent) + f"import {alias.name}{as_part}")
        return

    if isinstance(node, ast.ImportFrom):
        mod = node.module or ""
        names = []
        for a in node.names:
            as_part = f" as {a.asname}" if a.asname else ""
            names.append(f"{a.name}{as_part}")
        level = "." * (node.level or 0)
        lines.append(_indent(indent) + f"from {level}{mod} import {', '.join(names)}")
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        lines.append(_indent(indent) + _format_function_signature(node))
        _emit_control_flow(node.body, lines, indent + 1)
        return

    if isinstance(node, ast.ClassDef):
        bases = [ast.unparse(b) for b in node.bases] if node.bases else []
        base_str = f"({', '.join(bases)})" if bases else ""
        lines.append(_indent(indent) + f"class {node.name}{base_str}:")
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lines.append(_indent(indent + 1) + _format_function_signature(child))
                _emit_control_flow(child.body, lines, indent + 2)
        return


def _emit_control_flow(stmts: list[ast.stmt], lines: list[str], indent: int) -> None:
    for st in stmts:
        if isinstance(st, ast.If):
            lines.append(_indent(indent) + f"if {ast.unparse(st.test)}:")
            _emit_control_flow(st.body, lines, indent + 1)
            if st.orelse:
                lines.append(_indent(indent) + "else:")
                _emit_control_flow(st.orelse, lines, indent + 1)
        elif isinstance(st, ast.For):
            lines.append(_indent(indent) + f"for {ast.unparse(st.target)} in {ast.unparse(st.iter)}:")
            _emit_control_flow(st.body, lines, indent + 1)
        elif isinstance(st, ast.While):
            lines.append(_indent(indent) + f"while {ast.unparse(st.test)}:")
            _emit_control_flow(st.body, lines, indent + 1)
        elif isinstance(st, ast.Try):
            lines.append(_indent(indent) + "try:")
            _emit_control_flow(st.body, lines, indent + 1)
            for h in st.handlers:
                t = ast.unparse(h.type) if h.type else "Exception"
                n = f" as {h.name}" if h.name else ""
                lines.append(_indent(indent) + f"except {t}{n}:")
                _emit_control_flow(h.body, lines, indent + 1)
            if st.finalbody:
                lines.append(_indent(indent) + "finally:")
                _emit_control_flow(st.finalbody, lines, indent + 1)
        elif isinstance(st, ast.With):
            items = ", ".join(ast.unparse(i) for i in st.items)
            lines.append(_indent(indent) + f"with {items}:")
            _emit_control_flow(st.body, lines, indent + 1)
        elif isinstance(st, ast.Match):
            lines.append(_indent(indent) + f"match {ast.unparse(st.subject)}:")
            for c in st.cases:
                guard = f" if {ast.unparse(c.guard)}" if c.guard else ""
                lines.append(_indent(indent + 1) + f"case {ast.unparse(c.pattern)}{guard}:")
                _emit_control_flow(c.body, lines, indent + 2)
        elif isinstance(st, ast.Return):
            expr = ast.unparse(st.value) if st.value else ""
            lines.append(_indent(indent) + f"return {expr}".rstrip())
        elif isinstance(st, ast.Raise):
            expr = ast.unparse(st.exc) if st.exc else ""
            lines.append(_indent(indent) + f"raise {expr}".rstrip())
        else:
            calls = _find_external_calls(st)
            if calls:
                for c in calls:
                    lines.append(_indent(indent) + f"call {c}")


def _find_external_calls(node: ast.AST) -> list[str]:
    calls: set[str] = set()

    class V(ast.NodeVisitor):
        def visit_Call(self, n: ast.Call) -> None:  # type: ignore[override]
            name = _call_name(n.func)
            if name:
                calls.add(name)
            self.generic_visit(n)

    V().visit(node)

    filtered = [c for c in calls if not _is_builtin_call(c)]
    return sorted(filtered)


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        left = _call_name(func.value)
        if left:
            return f"{left}.{func.attr}"
        return func.attr
    return None


_BUILTIN_CALLS = {
    "print",
    "len",
    "range",
    "enumerate",
    "sum",
    "min",
    "max",
    "sorted",
    "map",
    "filter",
    "list",
    "dict",
    "set",
    "tuple",
    "int",
    "str",
    "float",
    "bool",
    "zip",
    "open",
}


def _is_builtin_call(call: str) -> bool:
    root = call.split(".", 1)[0]
    return root in _BUILTIN_CALLS


def _format_function_signature(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    async_prefix = "async " if isinstance(fn, ast.AsyncFunctionDef) else ""
    args = [a.arg for a in fn.args.posonlyargs]
    if fn.args.posonlyargs:
        args.append("/")
    args += [a.arg for a in fn.args.args]
    if fn.args.vararg:
        args.append("*" + fn.args.vararg.arg)
    elif fn.args.kwonlyargs:
        args.append("*")
    args += [a.arg for a in fn.args.kwonlyargs]
    if fn.args.kwarg:
        args.append("**" + fn.args.kwarg.arg)

    ret = ""
    if fn.returns is not None:
        ret = f" -> {ast.unparse(fn.returns)}"

    return f"{async_prefix}def {fn.name}({', '.join(args)}){ret}:"


def _indent(n: int) -> str:
    return "  " * n
