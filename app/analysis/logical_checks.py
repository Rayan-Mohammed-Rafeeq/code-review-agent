from __future__ import annotations

import ast
from collections import defaultdict

from app.analysis.models import Category, Issue, Severity


def _mk_issue(*, filename: str, line: int, severity: Severity, desc: str, sugg: str, code: str) -> Issue:
    return Issue(
        file=filename,
        line=max(1, int(line or 1)),
        category=Category.bug,
        severity=severity,
        description=desc,
        suggestion=sugg,
        source="custom_rules",
        code=code,
    )


def run_logical_checks(*, code: str, filename: str, strict: bool) -> list[Issue]:
    """Lightweight AST heuristics to catch common logical correctness bugs.

    Goals: high precision, low runtime. This is NOT symbolic execution.
    """
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError:
        return []

    issues: list[Issue] = []

    # 1) Unreachable code after `return` / `raise` in the same block.
    class _Unreachable(ast.NodeVisitor):
        def _scan_block(self, body: list[ast.stmt]):
            terminated = False
            for stmt in body:
                if terminated:
                    issues.append(
                        _mk_issue(
                            filename=filename,
                            line=getattr(stmt, "lineno", 1),
                            severity=Severity.medium if strict else Severity.low,
                            desc="Unreachable code: statements after return/raise in the same block won't run.",
                            sugg="Remove dead code or move it before the return/raise.",
                            code="L100-unreachable",
                        )
                    )
                    break

                if isinstance(stmt, (ast.Return, ast.Raise)):
                    terminated = True

        def _scan_stmt(self, stmt: ast.stmt) -> None:
            # Recursively scan nested statement blocks for unreachable code.
            if isinstance(stmt, ast.If):
                self._scan_block(stmt.body)
                self._scan_block(stmt.orelse)
                for s in stmt.body:
                    self._scan_stmt(s)
                for s in stmt.orelse:
                    self._scan_stmt(s)
            elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
                self._scan_block(stmt.body)
                self._scan_block(stmt.orelse)
                for s in stmt.body:
                    self._scan_stmt(s)
                for s in stmt.orelse:
                    self._scan_stmt(s)
            elif isinstance(stmt, ast.Try):
                self._scan_block(stmt.body)
                self._scan_block(stmt.orelse)
                self._scan_block(stmt.finalbody)
                for h in stmt.handlers:
                    self._scan_block(h.body)
                    for s in h.body:
                        self._scan_stmt(s)
                for s in stmt.body + stmt.orelse + stmt.finalbody:
                    self._scan_stmt(s)
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                self._scan_block(stmt.body)
                for s in stmt.body:
                    self._scan_stmt(s)
            elif isinstance(stmt, ast.Match):
                for c in stmt.cases:
                    self._scan_block(c.body)
                    for s in c.body:
                        self._scan_stmt(s)

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._scan_block(node.body)
            for s in node.body:
                self._scan_stmt(s)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._scan_block(node.body)
            for s in node.body:
                self._scan_stmt(s)
            self.generic_visit(node)

    _Unreachable().visit(tree)

    # 2) Suspicious boolean precedence: `a or b and c` without parentheses.
    class _BoolPrec(ast.NodeVisitor):
        def visit_BoolOp(self, node: ast.BoolOp):
            # Look for nested BoolOp of different operator types.
            if isinstance(node.op, ast.Or):
                for v in node.values:
                    if isinstance(v, ast.BoolOp) and isinstance(v.op, ast.And):
                        issues.append(
                            _mk_issue(
                                filename=filename,
                                line=getattr(node, "lineno", 1),
                                severity=Severity.medium,
                                desc="Mixed boolean operators without parentheses can be a logic bug (and/or precedence).",
                                sugg="Add parentheses to make intended precedence explicit.",
                                code="L200-bool-precedence",
                            )
                        )
                        break
            self.generic_visit(node)

    _BoolPrec().visit(tree)

    # 3) `is` used with a literal (except None/True/False): often a logic bug.
    class _IsLiteral(ast.NodeVisitor):
        def visit_Compare(self, node: ast.Compare):
            # handle `a is 5` / `a is 'x'`
            def _is_literal(n: ast.AST) -> bool:
                if isinstance(n, ast.Constant):
                    return n.value not in (None, True, False)
                return False

            if any(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops):
                left_lit = _is_literal(node.left)
                right_lit = any(_is_literal(c) for c in node.comparators)
                if left_lit or right_lit:
                    issues.append(
                        _mk_issue(
                            filename=filename,
                            line=getattr(node, "lineno", 1),
                            severity=Severity.high if strict else Severity.medium,
                            desc="Using 'is' to compare to a literal is usually wrong; 'is' checks identity, not equality.",
                            sugg="Use '==' / '!=' for value comparison; keep 'is' for None/True/False singletons.",
                            code="L300-is-literal",
                        )
                    )
            self.generic_visit(node)

    _IsLiteral().visit(tree)

    # 4) Division result used in range/indices: `/` produces float in py3.
    class _DivRange(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "range":
                for a in node.args:
                    if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Div):
                        issues.append(
                            _mk_issue(
                                filename=filename,
                                line=getattr(node, "lineno", 1),
                                severity=Severity.medium,
                                desc="range() argument uses '/', which produces float in Python 3; this will raise TypeError.",
                                sugg="Use '//' for integer division or wrap with int(...).",
                                code="L400-range-div",
                            )
                        )
                        break
            self.generic_visit(node)

    _DivRange().visit(tree)

    # 5) Duplicate dictionary keys (within a single literal): last one wins silently.
    class _DupDict(ast.NodeVisitor):
        def visit_Dict(self, node: ast.Dict):
            seen = set()
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, (str, int, float, bool, type(None))):
                    if k.value in seen:
                        issues.append(
                            _mk_issue(
                                filename=filename,
                                line=getattr(k, "lineno", 1),
                                severity=Severity.low if not strict else Severity.medium,
                                desc=f"Duplicate dict key {k.value!r}; earlier value will be overwritten.",
                                sugg="Remove the duplicate key or merge values intentionally.",
                                code="L500-duplicate-dict-key",
                            )
                        )
                        break
                    seen.add(k.value)
            self.generic_visit(node)

    _DupDict().visit(tree)

    # 6) Condition likely always-true/false: `if x == x` or `if x != x` (ignoring NaN edge).
    class _SelfCompare(ast.NodeVisitor):
        def visit_Compare(self, node: ast.Compare):
            if len(node.ops) == 1 and len(node.comparators) == 1:
                op = node.ops[0]
                right = node.comparators[0]
                if isinstance(node.left, ast.Name) and isinstance(right, ast.Name) and node.left.id == right.id:
                    if isinstance(op, ast.Eq):
                        issues.append(
                            _mk_issue(
                                filename=filename,
                                line=getattr(node, "lineno", 1),
                                severity=Severity.low,
                                desc=f"Self-comparison '{node.left.id} == {right.id}' is almost always true and may be a logic bug.",
                                sugg="Check the intended variable; this can happen due to copy/paste mistakes.",
                                code="L600-self-compare",
                            )
                        )
                    elif isinstance(op, ast.NotEq):
                        issues.append(
                            _mk_issue(
                                filename=filename,
                                line=getattr(node, "lineno", 1),
                                severity=Severity.medium,
                                desc=f"Self-comparison '{node.left.id} != {right.id}' is almost always false and may be a logic bug.",
                                sugg="Check the intended variable; this can happen due to copy/paste mistakes.",
                                code="L600-self-compare",
                            )
                        )
            self.generic_visit(node)

    _SelfCompare().visit(tree)

    # 7) Duplicate conditions in if/elif chain (exact AST match) – often a copy/paste logic bug.
    class _DupIfCond(ast.NodeVisitor):
        def visit_If(self, node: ast.If):
            conds = []
            cur = node
            while isinstance(cur, ast.If):
                conds.append(cur.test)
                if len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
                    cur = cur.orelse[0]
                else:
                    break

            dumps = defaultdict(int)
            for c in conds:
                dumps[ast.dump(c, include_attributes=False)] += 1

            for k, v in dumps.items():
                if v > 1:
                    issues.append(
                        _mk_issue(
                            filename=filename,
                            line=getattr(node, "lineno", 1),
                            severity=Severity.medium if strict else Severity.low,
                            desc="Duplicate condition in if/elif chain; one branch may be dead or incorrect.",
                            sugg="Fix the duplicated condition; consider consolidating or correcting the intended logic.",
                            code="L700-duplicate-if-condition",
                        )
                    )
                    break

            self.generic_visit(node)

    _DupIfCond().visit(tree)

    # 8) Likely inverted boolean logic in trivial predicate functions.
    # Example:
    #   def is_even(n):
    #       if n % 2 == 1:
    #           return True
    #       else:
    #           return False
    # This is a common off-by-one/inversion bug.
    class _InvertedPredicate(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef):
            # Only target very simple predicate-style functions.
            if not node.body or len(node.body) != 1:
                return
            stmt = node.body[0]
            if not isinstance(stmt, ast.If):
                return

            # Must have explicit else.
            if not stmt.orelse:
                return

            def _bool_return_only(block: list[ast.stmt]) -> bool | None:
                if len(block) != 1:
                    return None
                r = block[0]
                if not isinstance(r, ast.Return):
                    return None
                if isinstance(r.value, ast.Constant) and isinstance(r.value.value, bool):
                    return bool(r.value.value)
                return None

            then_ret = _bool_return_only(stmt.body)
            else_ret = _bool_return_only(stmt.orelse)
            if then_ret is None or else_ret is None:
                return
            if then_ret == else_ret:
                return

            fname = (node.name or "").lower()

            def _is_mod2_compare_to_1(test: ast.AST) -> bool:
                # (x % 2) == 1  OR  1 == (x % 2)
                if not isinstance(test, ast.Compare):
                    return False
                if len(test.ops) != 1 or len(test.comparators) != 1:
                    return False
                if not isinstance(test.ops[0], (ast.Eq, ast.NotEq)):
                    return False

                left = test.left
                right = test.comparators[0]

                def _is_mod2(expr: ast.AST) -> bool:
                    return (
                        isinstance(expr, ast.BinOp)
                        and isinstance(expr.op, ast.Mod)
                        and isinstance(expr.right, ast.Constant)
                        and expr.right.value == 2
                    )

                def _is_one(expr: ast.AST) -> bool:
                    return isinstance(expr, ast.Constant) and expr.value == 1

                return (_is_mod2(left) and _is_one(right)) or (_is_one(left) and _is_mod2(right))

            def _is_mod2_compare_to_0(test: ast.AST) -> bool:
                # (x % 2) == 0  OR  0 == (x % 2)
                if not isinstance(test, ast.Compare):
                    return False
                if len(test.ops) != 1 or len(test.comparators) != 1:
                    return False
                if not isinstance(test.ops[0], (ast.Eq, ast.NotEq)):
                    return False

                left = test.left
                right = test.comparators[0]

                def _is_mod2(expr: ast.AST) -> bool:
                    return (
                        isinstance(expr, ast.BinOp)
                        and isinstance(expr.op, ast.Mod)
                        and isinstance(expr.right, ast.Constant)
                        and expr.right.value == 2
                    )

                def _is_zero(expr: ast.AST) -> bool:
                    return isinstance(expr, ast.Constant) and expr.value == 0

                return (_is_mod2(left) and _is_zero(right)) or (_is_zero(left) and _is_mod2(right))

            # We only flag when the function name suggests the *opposite* of the condition.
            # - is_even + (n % 2 == 1) returning True
            # - is_odd + (n % 2 == 0) returning True
            # and the overall returns map directly: then->True else->False
            # (or then->False else->True; we can still reason about intent).
            intent_even = any(k in fname for k in ("is_even", "iseven", "even"))
            intent_odd = any(k in fname for k in ("is_odd", "isodd", "odd"))

            # Determine the semantics of the test: does it match "odd" or "even"?
            test_is_odd = _is_mod2_compare_to_1(stmt.test)
            test_is_even = _is_mod2_compare_to_0(stmt.test)

            if not (intent_even or intent_odd):
                return
            if not (test_is_odd or test_is_even):
                return

            # If the branch returns True when the test indicates the opposite of the name, flag.
            # Example: intent_even + test_is_odd + then_ret True
            if intent_even and test_is_odd and then_ret is True and else_ret is False:
                issues.append(
                    _mk_issue(
                        filename=filename,
                        line=getattr(stmt, "lineno", getattr(node, "lineno", 1)),
                        severity=Severity.high if strict else Severity.medium,
                        desc="Likely inverted predicate: function name suggests 'even' but condition checks for odd and returns True.",
                        sugg="Swap the True/False returns or change the condition to (n % 2 == 0); simplest: `return n % 2 == 0`. ",
                        code="L800-inverted-predicate",
                    )
                )
            elif intent_odd and test_is_even and then_ret is True and else_ret is False:
                issues.append(
                    _mk_issue(
                        filename=filename,
                        line=getattr(stmt, "lineno", getattr(node, "lineno", 1)),
                        severity=Severity.high if strict else Severity.medium,
                        desc="Likely inverted predicate: function name suggests 'odd' but condition checks for even and returns True.",
                        sugg="Swap the True/False returns or change the condition to (n % 2 == 1); simplest: `return n % 2 == 1`. ",
                        code="L800-inverted-predicate",
                    )
                )

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            # same logic
            self.visit_FunctionDef(node)  # type: ignore[arg-type]

    _InvertedPredicate().visit(tree)

    # 9) Potential ZeroDivisionError: division by len(x) without any evident empty-check.
    # Heuristic: flag `... / len(name)` when the same name isn't guarded by `if name` / `if len(name)`.
    class _DivByLen(ast.NodeVisitor):
        def __init__(self):
            self.guarded: set[str] = set()

        def visit_If(self, node: ast.If):
            # Track simple guards like: `if numbers:` or `if len(numbers) > 0:`
            name = None
            t = node.test
            if isinstance(t, ast.Name):
                name = t.id
            elif isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not) and isinstance(t.operand, ast.Name):
                name = t.operand.id
            elif isinstance(t, ast.Call) and isinstance(t.func, ast.Name) and t.func.id == "len" and len(t.args) == 1:
                a0 = t.args[0]
                if isinstance(a0, ast.Name):
                    name = a0.id
            elif isinstance(t, ast.Compare):
                left = t.left
                if (
                    isinstance(left, ast.Call)
                    and isinstance(left.func, ast.Name)
                    and left.func.id == "len"
                    and len(left.args) == 1
                ):
                    a0 = left.args[0]
                    if isinstance(a0, ast.Name):
                        name = a0.id
            if name:
                self.guarded.add(name)
            self.generic_visit(node)

        def visit_BinOp(self, node: ast.BinOp):
            if isinstance(node.op, (ast.Div, ast.FloorDiv)):
                r = node.right
                if isinstance(r, ast.Call) and isinstance(r.func, ast.Name) and r.func.id == "len" and len(r.args) == 1:
                    a0 = r.args[0]
                    if isinstance(a0, ast.Name):
                        var = a0.id
                        if var not in self.guarded:
                            issues.append(
                                _mk_issue(
                                    filename=filename,
                                    line=getattr(node, "lineno", 1),
                                    severity=Severity.high if strict else Severity.medium,
                                    desc=f"Potential ZeroDivisionError: dividing by len({var}) without handling empty input.",
                                    sugg=f"Validate input before dividing (e.g., `if not {var}: ...`) or raise a clear exception.",
                                    code="L700-div-by-len",
                                )
                            )
            self.generic_visit(node)

    _DivByLen().visit(tree)

    return issues
