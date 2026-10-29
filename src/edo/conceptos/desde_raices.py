"""Armar la ED lineal homogénea de coeficientes constantes a partir de las raíces de la
ecuación característica, y escribir y_h.

Raíz real r de multiplicidad m:  e^(rx), x e^(rx), ..., x^(m-1) e^(rx)   (A8: el texto puso x^m)
Par a ± bi de multiplicidad m:   e^(ax) x^j cos(bx),  e^(ax) x^j sen(bx),  j = 0..m-1
"""
from __future__ import annotations

import re

import sympy as sp

from ..core import discrepancias  # noqa: F401  (nota A8 se añade aquí)
from ..core.latex import latex
from ..core.lector import ED, ErrorLectura, D, leer_expresion, x, y
from ..core.paso import Paso, Resultado
from ..core.verificador import verificar_explicita

Raiz = tuple[sp.Expr, int]

NOTA_A8 = ("[A8] Para una raíz de multiplicidad m las soluciones son e^(rx), x e^(rx), …, x^(m-1) e^(rx). "
           "El texto escribe x^m; lo correcto es x^(m-1) (la potencia más alta es m-1).")


def _a_numero(txt: str) -> sp.Expr:
    t = re.sub(r"(?<![A-Za-z])i(?![A-Za-z])", "I", txt.strip())
    t = re.sub(r"(\d)\s*I", r"\1*I", t)
    try:
        return sp.nsimplify(leer_expresion(t).subs(sp.Symbol("I"), sp.I))
    except ErrorLectura:
        raise
    except Exception as exc:
        raise ErrorLectura(f"No pude leer la raíz «{txt}»: {exc}") from exc


_MULT = {"doble": 2, "triple": 3, "cuádruple": 4, "cuadruple": 4}


def leer_raices(texto: str) -> list[Raiz]:
    """``5+2i, 5+2i, 5-2i, 5-2i, 0, 0``, ``5+2i (2), 5-2i (2), 0 (2)`` o ``D1=D2=5+2i; D3=D4=5-2i``.

    Devuelve [(raíz, multiplicidad)] sin repetidos, en orden de aparición.
    """
    acum: dict[sp.Expr, int] = {}
    orden: list[sp.Expr] = []
    for trozo in re.split(r"[;,]", texto):
        trozo = trozo.strip()
        if not trozo:
            continue
        m = 1
        if "=" in trozo:
            *ds, trozo = [p.strip() for p in trozo.split("=")]
            m = max(len(ds), 1)
        mm = re.search(r"\(\s*(?:x|×)?\s*(\d+)\s*\)\s*$", trozo)
        if mm:
            m *= int(mm.group(1))
            trozo = trozo[:mm.start()]
        else:
            for palabra, k in _MULT.items():
                if re.search(rf"\b{palabra}\b", trozo):
                    m *= k
                    trozo = re.sub(rf"\b{palabra}\b", "", trozo)
        r = _a_numero(trozo)
        if r not in acum:
            orden.append(r)
            acum[r] = 0
        acum[r] += m
    if not orden:
        raise ErrorLectura("No hay raíces.")
    return [(r, acum[r]) for r in orden]


def _validar(raices: list[Raiz]) -> list[Raiz]:
    """Une cada par conjugado (representante con parte imaginaria positiva) conservando el orden."""
    dic = dict(raices)
    out: list[Raiz] = []
    vistos = set()
    for r, m in raices:
        if r in vistos:
            continue
        if r.is_real:
            out.append((r, m))
            vistos.add(r)
            continue
        c = sp.conjugate(r)
        if dic.get(c) != m:
            raise ErrorLectura(
                f"La raíz compleja {latex(r)} (multiplicidad {m}) necesita su conjugada {latex(c)} con la misma "
                "multiplicidad para que la ecuación tenga coeficientes reales.")
        rep = r if sp.im(r) > 0 else c
        out.append((rep, m))
        vistos |= {r, c}
    return out


def polinomio_caracteristico(raices: list[Raiz]) -> sp.Expr:
    fs = []
    for r, m in raices:
        fs.append((D - r) ** m if r.is_real else ((D - sp.re(r)) ** 2 + sp.im(r) ** 2) ** m)
    return sp.expand(sp.Mul(*fs))


def base_solucion(raices: list[Raiz], agrupadas: bool = False) -> tuple[sp.Expr, list[sp.Symbol]]:
    """y_h con constantes numeradas en el orden de las raíces (como en el texto)."""
    k = 1
    partes = []
    cs: list[sp.Symbol] = []

    def nueva():
        nonlocal k
        c = sp.Symbol(f"C{k}")
        k += 1
        cs.append(c)
        return c
    for r, m in (raices if agrupadas else _validar(raices)):
        if r.is_real:
            poli = sum(nueva() * x ** j for j in range(m))
            partes.append(sp.exp(r * x) * poli if r != 0 else poli)
        else:
            a, b = sp.re(r), sp.im(r)
            pc = sum(nueva() * x ** j for j in range(m))
            ps = sum(nueva() * x ** j for j in range(m))
            base = pc * sp.cos(b * x) + ps * sp.sin(b * x)
            partes.append(sp.exp(a * x) * base if a != 0 else base)
    return sp.Add(*partes), cs


def _ed_desde_poli(P: sp.Expr) -> ED:
    poli = sp.Poly(P, D)
    lhs = sum(c * (y(x) if k == 0 else sp.Derivative(y(x), (x, k))) for (k,), c in poli.terms())
    return ED("raíces", "operador", lhs, sp.Integer(0), poli.degree(), operador=P)


def desde_raices(raices: list[Raiz]) -> Resultado:
    res = Resultado("ED desde las raíces de la ecuación característica")
    raices = _validar(raices)
    n = sum((2 if not r.is_real else 1) * m for r, m in raices)
    listado = ",\\ ".join(
        (f"D = {latex(r)}\\ \\text{{(mult. {m})}}" if r.is_real else f"D = {latex(r)},\\ {latex(sp.conjugate(r))}\\ \\text{{(mult. {m})}}")
        for r, m in raices)
    res.pasos.append(Paso("Raíces de la ecuación característica", "raíces y multiplicidades", "", listado,
                          f"Se cuentan {n} raíces: la ecuación diferencial es de orden {n}."))
    factores = []
    for r, m in raices:
        if r.is_real:
            f = rf"\left(D {'-' if r > 0 else '+'} {latex(abs(r))}\right)" if r != 0 else "D"
        else:
            a, b = sp.re(r), sp.im(r)
            f = rf"\left[(D {'-' if a > 0 else '+'} {latex(abs(a))})^2 + {latex(b ** 2)}\right]" if a != 0 else rf"\left(D^2 + {latex(b ** 2)}\right)"
        factores.append(f + (f"^{{{m}}}" if m > 1 else ""))
    res.pasos.append(Paso("Factores del polinomio característico", "cada raíz r da el factor (D − r)",
                          "", "".join(factores) + " = 0",
                          "Cada raíz real $r$ da el factor $(D-r)$; cada par $a\\pm bi$ da $(D-a)^2+b^2$."))
    P = polinomio_caracteristico(raices)
    res.pasos.append(Paso("Ecuación característica", "multiplicar los factores", "", latex(P) + " = 0"))
    ed = _ed_desde_poli(P)
    res.pasos.append(Paso("Ecuación diferencial (método abreviado)", "D ↔ derivada",
                          "(" + latex(P) + ")\\,y = 0", latex(ed.lhs) + " = 0"))
    sol, cs = base_solucion(raices, agrupadas=True)
    nota = NOTA_A8 if any(m > 1 for _, m in raices) else None
    res.pasos.append(Paso("Función solución y_h", "solución de la homogénea", "", "y_h = " + latex(sol),
                          "Raíz real $r$: $e^{rx}$; par $a\\pm bi$: $e^{ax}\\cos bx$ y $e^{ax}\\operatorname{sen} bx$; "
                          "si la raíz tiene multiplicidad $m$ se multiplican por $1, x, \\dots, x^{m-1}$.",
                          discrepancia=nota))
    v = verificar_explicita(ed, sol)
    res.verificacion = v
    res.solucion = "y = " + latex(sol)
    res.valor = sol
    res.constantes = [c.name for c in cs]
    res.pasos.append(Paso("Comprobación", "sustitución en la ED", "", "",
                          f"La función cumple la ecuación diferencial ({v.como})." if v.ok else "La comprobación falló."))
    return res
