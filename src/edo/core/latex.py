"""LaTeX con la notación del docente: sen, tg, ctg, arcsen, arctg, y', y''."""
from __future__ import annotations

import sympy as sp
from sympy.printing.latex import LatexPrinter

_NOMBRES = {
    "sin": "sen", "tan": "tg", "cot": "ctg", "asin": "arcsen", "acos": "arccos",
    "atan": "arctg", "acot": "arcctg", "asec": "arcsec", "acsc": "arccsc",
    "sinh": "senh", "tanh": "tgh", "coth": "ctgh",
}


class _Impresor(LatexPrinter):
    def _print_Function(self, expr, exp=None):
        nombre = expr.func.__name__
        if nombre in _NOMBRES:
            op = _NOMBRES[nombre]
            arg = self._print(expr.args[0])
            if not (expr.args[0].is_Symbol or expr.args[0].is_Number):
                arg = rf"\left({arg}\right)"
            base = rf"\operatorname{{{op}}}\,{arg}"
            return base if exp is None else rf"\operatorname{{{op}}}^{{{exp}}}\,{arg}"
        return super()._print_Function(expr, exp)

    def _print_Derivative(self, expr):
        f = expr.expr
        if isinstance(f, sp.core.function.AppliedUndef) and len(expr.variables) > 0:
            vs = set(expr.variables)
            if len(vs) == 1 and f.args == tuple(vs):
                n = len(expr.variables)
                nombre = f.func.__name__
                return nombre + ("'" * n if n <= 3 else rf"^{{({n})}}")
        return super()._print_Derivative(expr)

    def _as_ordered_terms(self, expr, order=None):
        """En una ED, derivadas de mayor orden primero: y'' - 3y' + 2y."""
        terminos = super()._as_ordered_terms(expr, order)

        def clave(t):
            ords = [d.derivative_count for d in t.atoms(sp.Derivative)]
            if ords:
                return -max(ords)
            return -0.5 if t.has(sp.core.function.AppliedUndef) else 1
        return sorted(terminos, key=clave)

    def _print_AppliedUndef(self, expr, exp=None):
        # y(x) se escribe y
        return self._print(sp.Symbol(expr.func.__name__)) if len(expr.args) == 1 else super()._print_Function(expr)


_imp = _Impresor({"mul_symbol": " ", "ln_notation": True, "inv_trig_style": "full"})


def latex(expr) -> str:
    """LaTeX de una expresión SymPy (o cadena ya en LaTeX)."""
    if isinstance(expr, str):
        return expr
    return _imp.doprint(expr)


def latex_eq(izq, der) -> str:
    return f"{latex(izq)} = {latex(der)}"


def latex_ed(expr_lhs, expr_rhs=0) -> str:
    return latex_eq(expr_lhs, expr_rhs)
