"""Derivador por reglas (suma, múltiplo constante, producto, cociente, cadena, tabla).

No usa ``sp.diff`` para producir el resultado: cada regla emite su paso y arma la
derivada. ``sp.diff`` solo aparece en la tabla de derivadas básicas y para verificar.
"""
from __future__ import annotations

import sympy as sp
from sympy.core.function import AppliedUndef

from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.paso import Paso
from ..core.verificador import es_cero
from .resultado import ErrorCalculo, ResultadoCalculo

_T = sp.Dummy("t")
_TABLA_FUNCIONES = {
    sp.sin: "sen", sp.cos: "cos", sp.tan: "tg", sp.cot: "ctg", sp.sec: "sec", sp.csc: "csc",
    sp.asin: "arcsen", sp.acos: "arccos", sp.atan: "arctg", sp.acot: "arcctg",
    sp.sinh: "senh", sp.cosh: "cosh", sp.tanh: "tgh", sp.coth: "ctgh",
    sp.exp: "e^u", sp.log: "ln",
}


def _p(e: sp.Expr) -> str:
    """LaTeX con paréntesis si hace falta para usarlo como factor."""
    s = latex(e)
    if isinstance(e, sp.Add) or (isinstance(e, sp.Mul) and e.could_extract_minus_sign()):
        return rf"\left({s}\right)"
    return s


class _Derivador:
    def __init__(self, var: sp.Symbol):
        self.v = var
        self.pasos: list[Paso] = []

    # ---------------------------------------------------------------- helpers
    def dep(self, e: sp.Expr) -> bool:
        return e.has(self.v)

    def dx(self, e: sp.Expr) -> str:
        return rf"\frac{{d}}{{d{self.v}}}\left[{latex(e)}\right]"

    def paso(self, titulo, regla, e, despues, expl=""):
        self.pasos.append(Paso(titulo, regla, self.dx(e), despues, expl))

    # ------------------------------------------------------------------ reglas
    def d(self, e: sp.Expr) -> sp.Expr:
        v = self.v
        if not self.dep(e):
            self.paso("Derivada de una constante", "(c)' = 0", e, "0",
                      f"${latex(e)}$ no depende de ${v}$.")
            return sp.Integer(0)
        if e == v:
            self.paso("Derivada de la variable", f"({v})' = 1", e, "1")
            return sp.Integer(1)
        if isinstance(e, AppliedUndef):
            r = sp.Derivative(e, v)
            self.paso("Derivada de la función incógnita", "y es función de x", e, latex(r),
                      f"${e.func.__name__}$ depende de ${v}$, su derivada queda indicada.")
            return r
        if isinstance(e, sp.Derivative) and isinstance(e.expr, AppliedUndef):
            r = sp.Derivative(e.expr, *e.variable_count, (v, 1))
            self.paso("Derivada de una derivada de y", "se sube un orden", e, latex(r))
            return r
        if isinstance(e, sp.Add):
            return self._suma(e)
        if isinstance(e, sp.Mul):
            return self._mul(e)
        if isinstance(e, sp.Pow):
            return self._pow(e)
        if isinstance(e, sp.Integral):
            return self._integral(e)
        if isinstance(e, sp.Function) and type(e) in _TABLA_FUNCIONES:
            return self._funcion(e)
        raise ErrorCalculo(f"No tengo una regla de derivación para «{latex(e)}».")

    def _suma(self, e: sp.Add) -> sp.Expr:
        terminos = e.args
        self.paso("Regla de la suma", "(u + v)' = u' + v'", e,
                  " + ".join(self.dx(t) for t in terminos),
                  "La derivada de una suma es la suma de las derivadas.")
        return sp.Add(*[self.d(t) for t in terminos])

    def _mul(self, e: sp.Mul) -> sp.Expr:
        num, den = sp.fraction(e)
        if self.dep(den):
            if self.dep(num):
                return self._cociente(num, den)
            # c / g(x) = c * g^(-1)
            c, resto = num, sp.Pow(den, -1)
            self.paso("Regla del múltiplo constante", "(c·f)' = c·f'", e,
                      rf"{_p(c)}\,{self.dx(resto)}",
                      f"${latex(c)}$ es constante; se escribe el cociente como potencia de exponente $-1$.")
            return c * self.d(resto)
        factores = sp.Mul.make_args(e)
        ctes = [f for f in factores if not self.dep(f)]
        deps = [f for f in factores if self.dep(f)]
        if ctes:
            c = sp.Mul(*ctes)
            resto = sp.Mul(*deps)
            self.paso("Regla del múltiplo constante", "(c·f)' = c·f'", e,
                      rf"{_p(c)}\,{self.dx(resto)}",
                      f"${latex(c)}$ es constante y sale de la derivada.")
            return c * self.d(resto)
        return self._producto(e, deps)

    def _producto(self, e, factores) -> sp.Expr:
        if len(factores) == 2:
            u, w = factores
            self.paso("Regla del producto", "(u·v)' = u'·v + u·v'", e,
                      rf"{self.dx(u)}\,{_p(w)} + {_p(u)}\,{self.dx(w)}",
                      f"Con $u={latex(u)}$ y $v={latex(w)}$.")
            return self.d(u) * w + u * self.d(w)
        partes = []
        for i in range(len(factores)):
            partes.append(r"\,".join(self.dx(f) if j == i else _p(f) for j, f in enumerate(factores)))
        self.paso("Regla del producto (varios factores)", "(u₁·u₂···uₙ)' = Σ u₁···uᵢ'···uₙ", e,
                  " + ".join(partes), "Se deriva un factor a la vez y se dejan los demás.")
        total = sp.Integer(0)
        for i in range(len(factores)):
            dfi = self.d(factores[i])
            total += dfi * sp.Mul(*[f for j, f in enumerate(factores) if j != i])
        return total

    def _cociente(self, u: sp.Expr, w: sp.Expr) -> sp.Expr:
        e = u / w
        self.paso("Regla del cociente", r"(u/v)' = (u'·v − u·v')/v²", e,
                  rf"\frac{{{self.dx(u)}\,{_p(w)} - {_p(u)}\,{self.dx(w)}}}{{\left({latex(w)}\right)^{{2}}}}",
                  f"Con $u={latex(u)}$ y $v={latex(w)}$.")
        du, dw = self.d(u), self.d(w)
        return (du * w - u * dw) / w ** 2

    def _pow(self, e: sp.Pow) -> sp.Expr:
        b, ex = e.args
        v = self.v
        if not self.dep(ex):
            if b == v:
                r = ex * v ** (ex - 1)
                self.paso("Regla de la potencia", r"(xⁿ)' = n·xⁿ⁻¹", e, latex(r),
                          f"Con $n={latex(ex)}$.")
                return r
            self.paso("Regla de la potencia y de la cadena", r"(uⁿ)' = n·uⁿ⁻¹·u'", e,
                      rf"{_p(ex)}\,{_p(b ** (ex - 1))}\,{self.dx(b)}",
                      f"Con $u={latex(b)}$ y $n={latex(ex)}$.")
            return ex * b ** (ex - 1) * self.d(b)
        if not self.dep(b):  # a^u
            self.paso("Derivada de aᵘ con la regla de la cadena", r"(aᵘ)' = aᵘ·ln a·u'", e,
                      rf"{latex(e)}\,\ln {_p(b)}\,{self.dx(ex)}", f"Con $a={latex(b)}$ y $u={latex(ex)}$.")
            return e * sp.log(b) * self.d(ex)
        # u^v con u y v variables: derivación logarítmica
        self.paso("Derivada de uᵛ (derivación logarítmica)", r"(uᵛ)' = uᵛ·(v'·ln u + v·u'/u)", e,
                  rf"{latex(e)}\left({self.dx(ex)}\,\ln {_p(b)} + {_p(ex)}\,\frac{{{self.dx(b)}}}{{{latex(b)}}}\right)",
                  f"Con $u={latex(b)}$ y $v={latex(ex)}$.")
        dv, du = self.d(ex), self.d(b)
        return e * (dv * sp.log(b) + ex * du / b)

    def _funcion(self, e: sp.Function) -> sp.Expr:
        u = e.args[0]
        nombre = _TABLA_FUNCIONES[type(e)]
        tabla = sp.diff(type(e)(_T), _T).subs(_T, u)
        if u == self.v:
            self.paso(f"Derivada de {nombre}" if nombre != "e^u" else "Derivada de eˣ",
                      "tabla de derivadas", e, latex(tabla))
            return tabla
        self.paso("Regla de la cadena", r"[f(u)]' = f'(u)·u'", e,
                  rf"{_p(tabla)}\,{self.dx(u)}",
                  f"Función externa {nombre if nombre != 'e^u' else 'exponencial'}, interna $u={latex(u)}$.")
        return tabla * self.d(u)

    def _integral(self, e: sp.Integral) -> sp.Expr:
        if len(e.limits) != 1 or len(e.limits[0]) != 3:
            raise ErrorCalculo("Solo derivo integrales definidas con límites (t, a, b).")
        t, a, b = e.limits[0]
        f = e.function
        if f.has(self.v):
            raise ErrorCalculo("El integrando depende de la variable de derivación (regla de Leibniz): fuera del temario.")
        sup = f.subs(t, b)
        inf = f.subs(t, a)
        self.paso("Teorema fundamental del cálculo", r"\frac{d}{dx}\int_a^{u(x)} f(t)\,dt = f(u(x))\,u'(x)", e,
                  rf"{latex(sup)}\,{self.dx(b)}" + (rf" - {_p(inf)}\,{self.dx(a)}" if self.dep(a) else ""),
                  "La derivada de una integral con límite superior variable es el integrando evaluado en ese límite, por la derivada del límite.")
        r = sup * self.d(b)
        if self.dep(a):
            r -= inf * self.d(a)
        return r


def derivar(expr: sp.Expr, var: sp.Symbol, orden: int = 1) -> ResultadoCalculo:
    """Deriva ``expr`` respecto de ``var`` con pasos. Lanza ErrorCalculo si no hay regla."""
    expr = sp.sympify(expr)
    pasos: list[Paso] = []
    actual = expr
    for k in range(1, orden + 1):
        dr = _Derivador(var)
        armado = dr.d(actual)
        simple = simplificar(armado)
        suf = "" if orden == 1 else f" (derivada {k})"
        if orden > 1:
            pasos.append(Paso(f"Derivada de orden {k}", "", "", "", f"Se deriva el resultado anterior."))
        pasos.extend(dr.pasos)
        if simple != armado:
            pasos.append(Paso("Simplificar" + suf, "álgebra", latex(armado), latex(simple)))
        pasos.append(Paso("Resultado" + suf, "", rf"\frac{{d}}{{d{var}}}\left[{latex(actual)}\right]", latex(simple)))
        actual = simple
    cotejo = sp.diff(expr, var, orden)
    verif = es_cero(actual - cotejo)
    res = ResultadoCalculo(expr, actual, pasos, [], verif, True,
                           rf"\frac{{d{'^' + str(orden) if orden > 1 else ''}}}{{d{var}{'^' + str(orden) if orden > 1 else ''}}}\left[{latex(expr)}\right]",
                           latex(actual))
    return res
