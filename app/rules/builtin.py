from __future__ import annotations

import ast

from app.analysis.models import Category, Severity
from app.rules.base import RuleContext, issue


class DebugPrintRule:
    rule_id = "R100-debug-print"
    description = "Detect print() calls that look like debug output"
    default_enabled = True

    def run(self, ctx: RuleContext):
        out = []

        class V(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    out.append(
                        issue(
                            filename=ctx.filename,
                            line=getattr(node, "lineno", 1),
                            category=Category.style,
                            severity=Severity.low if not ctx.strict else Severity.medium,
                            description="Debug print() left in code.",
                            suggestion="Replace with structured logging or remove before merge.",
                            rule_id=DebugPrintRule.rule_id,
                        )
                    )
                self.generic_visit(node)

        V().visit(ctx.tree)
        return out


class DangerousCallRule:
    rule_id = "R200-dangerous-call"
    description = "Detect eval/exec/os.system usage"
    default_enabled = True

    def run(self, ctx: RuleContext):
        out = []

        class V(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call):
                # eval(...)
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                    out.append(
                        issue(
                            filename=ctx.filename,
                            line=getattr(node, "lineno", 1),
                            category=Category.security,
                            severity=Severity.critical,
                            description=f"Use of {node.func.id}() is dangerous.",
                            suggestion="Avoid dynamic code execution. Use safe parsers/dispatch tables.",
                            rule_id=DangerousCallRule.rule_id,
                        )
                    )
                # os.system(...)
                if isinstance(node.func, ast.Attribute) and node.func.attr == "system":
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        out.append(
                            issue(
                                filename=ctx.filename,
                                line=getattr(node, "lineno", 1),
                                category=Category.security,
                                severity=Severity.high,
                                description="Use of os.system() is risky (shell injection).",
                                suggestion="Prefer subprocess.run([...], check=True) without shell=True.",
                                rule_id=DangerousCallRule.rule_id,
                            )
                        )
                self.generic_visit(node)

        V().visit(ctx.tree)
        return out


class MutableDefaultArgRule:
    rule_id = "R300-mutable-default"
    description = "Detect mutable default arguments in function definitions"
    default_enabled = True

    def run(self, ctx: RuleContext):
        out = []

        def _is_mutable(n: ast.AST) -> bool:
            return isinstance(n, (ast.List, ast.Dict, ast.Set))

        class V(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef):
                for d in node.args.defaults or []:
                    if d is not None and _is_mutable(d):
                        out.append(
                            issue(
                                filename=ctx.filename,
                                line=getattr(d, "lineno", getattr(node, "lineno", 1)),
                                category=Category.bug,
                                severity=Severity.high,
                                description="Mutable default argument can leak state between calls.",
                                suggestion="Use None as default and create a new list/dict inside the function.",
                                rule_id=MutableDefaultArgRule.rule_id,
                            )
                        )
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self.visit_FunctionDef(node)  # type: ignore[arg-type]

        V().visit(ctx.tree)
        return out


class DeepNestingRule:
    rule_id = "R400-deep-nesting"
    description = "Detect deep nesting that hurts readability"
    default_enabled = True

    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth

    def run(self, ctx: RuleContext):
        out = []
        depth = 0
        max_depth = self.max_depth

        NEST_NODES = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncWith)

        class V(ast.NodeVisitor):
            def generic_visit(self, node: ast.AST):
                nonlocal depth
                is_nest = isinstance(node, NEST_NODES)
                if is_nest:
                    depth += 1
                    if depth > max_depth:
                        out.append(
                            issue(
                                filename=ctx.filename,
                                line=getattr(node, "lineno", 1),
                                category=Category.style,
                                severity=Severity.low if not ctx.strict else Severity.medium,
                                description=f"Deep nesting (depth={depth}) reduces readability.",
                                suggestion="Refactor with early returns, helper functions, or guard clauses.",
                                rule_id=DeepNestingRule.rule_id,
                            )
                        )
                super().generic_visit(node)
                if is_nest:
                    depth -= 1

        V().visit(ctx.tree)
        return out


class UnusedVariableRule:
    rule_id = "R500-unused-variable"
    description = "Detect unused local variables (basic heuristic)"
    default_enabled = True

    def run(self, ctx: RuleContext):
        out = []

        class FuncVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef):
                assigned = set()
                used = set()

                class Inner(ast.NodeVisitor):
                    def visit_Name(self, n: ast.Name):
                        if isinstance(n.ctx, ast.Store):
                            assigned.add(n.id)
                        elif isinstance(n.ctx, ast.Load):
                            used.add(n.id)

                for stmt in node.body:
                    Inner().visit(stmt)

                for name in sorted(assigned - used):
                    if name.startswith("_"):
                        continue
                    out.append(
                        issue(
                            filename=ctx.filename,
                            line=getattr(node, "lineno", 1),
                            category=Category.style,
                            severity=Severity.info,
                            description=f"Variable '{name}' assigned but never used.",
                            suggestion="Remove it or use it; prefix with '_' if intentionally unused.",
                            rule_id=UnusedVariableRule.rule_id,
                        )
                    )

        FuncVisitor().visit(ctx.tree)
        return out


BUILTIN_RULES = [
    DebugPrintRule(),
    DangerousCallRule(),
    MutableDefaultArgRule(),
    DeepNestingRule(max_depth=4),
    UnusedVariableRule(),
]
