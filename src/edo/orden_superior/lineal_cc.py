"""Ecuaciones lineales de coeficientes constantes F(D)y = Q(x).

Método abreviado (operador D): y = y_h + y_p con
  * y_h: raíces de la ecuación característica F(D) = 0,
  * y_p = Q(x)/F(D): Caso I (e^ax), Caso II (sen/cos), Caso III (e^ax·V(x)), polinomios
    (división de 1/F(D)), resonancia y sumas de términos.
Coeficientes indeterminados con la modificación x^s (s = multiplicidad de la raíz asociada).

El texto llama y_c a la solución particular; aquí se escribe y_p (docs/DISCREPANCIAS.md, A15).
"""
from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from ..conceptos.desde_raices import NOTA_A8, base_solucion
from ..core import discrepancias
from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, D, x, y
from ..core.paso import Paso, Resultado, Verificacion
from ..core.verificador import es_cero, verificar_explicita
from ..primer_orden.base import NoAplica

NOTA_A15 = "[A15] El texto llama y_c a la solución particular; aquí se la escribe y_p (y_h es la homogénea)."


def L(e) -> str:
    """LaTeX con números decimales a 4 cifras (raíces numéricas)."""
    if hasattr(e, "replace") and getattr(e, "has", None) and e.has(sp.Float):
        e = e.replace(lambda a: isinstance(a, sp.Float), lambda a: sp.Float(f"{float(a):.4g}"))
    return latex(e)


# ----------------------------------------------------------------- lectura
@dataclass
class EDLineal:
    ed: ED
    n: int
    P: sp.Expr          # F(D)
    Q: sp.Expr          # término independiente
    factor: sp.Expr = sp.Integer(1)  # factor común h(x) que se dividió, si lo hubo

    @property
    def homogenea(self) -> bool:
        return sp.simplify(self.Q) == 0


def leer_lineal(ed: ED) -> EDLineal:
    if ed.orden < 1:
        raise NoAplica("No es una ecuación diferencial.")
    F = ed.expr
    ders = {k: (y(x) if k == 0 else sp.Derivative(y(x), (x, k))) for k in range(ed.orden + 1)}
    coefs = []
    for k, d in ders.items():
        a = sp.diff(F, d)
        if a.has(y) or a.has(sp.Derivative):
            raise NoAplica("La ecuación no es lineal en y y sus derivadas.")
        coefs.append(a)
    resto = F.subs({d: 0 for d in reversed(list(ders.values()))})
    if sp.simplify(F - (sum(a * d for a, d in zip(coefs, ders.values())) + resto)) != 0:
        raise NoAplica("La ecuación no es lineal en y y sus derivadas.")
    if coefs[-1] == 0:
        raise NoAplica("El coeficiente de la derivada mayor es cero.")
    factor = sp.Integer(1)
    if any(a.has(x) for a in coefs):
        # un factor común h(x) (p. ej. y'' cos(x/2) + y cos(x/2)/4 = 1) se pasa dividiendo
        h = coefs[-1]
        razones = [sp.simplify(a / h) for a in coefs]
        if any(r.has(x) for r in razones):
            raise NoAplica("Los coeficientes no son constantes (ni son constantes salvo un factor común).")
        coefs, resto, factor = razones, sp.simplify(resto / h), h
    coefs = [sp.nsimplify(a) if a.is_Float is False else a for a in coefs]
    P = sum(a * D ** k for k, a in enumerate(coefs))
    return EDLineal(ed, ed.orden, sp.expand(P), sp.expand(-resto), factor)


def aplica_abreviado(ed: ED) -> str | None:
    if ed.orden < 2:
        return None
    try:
        L_ = leer_lineal(ed)
        if not L_.homogenea:
            _grupos(L_.Q)
    except NoAplica:
        return None
    return "coeficientes constantes y Q(x) = suma de c·xᵏ·e^(ax)·sen/cos(bx+φ)"


# ---------------------------------------------------------------- raíces
def raices_caracteristicas(P: sp.Expr):
    """([(raíz, mult)], exactas) de F(D) = 0. Exactas si cada factor irreducible es de grado ≤ 2."""
    poli = sp.Poly(P, D)
    _, factores = sp.factor_list(poli)
    if all(f.degree() <= 2 for f, _ in factores):
        out: dict[sp.Expr, int] = {}
        for f, m in factores:
            for r in sp.roots(f, D):
                out[sp.nsimplify(r) if r.is_number else r] = out.get(r, 0) + m
        return [(r, m) for r, m in out.items()], True
    aprox = poli.nroots(n=25, maxsteps=500)
    grupos: list[list] = []
    for r in aprox:
        for g in grupos:
            if abs(complex(r) - complex(g[0])) < 1e-6:
                g[1] += 1
                break
        else:
            grupos.append([r, 1])
    out2 = []
    for r, m in grupos:
        r = sp.sympify(r)
        out2.append((sp.re(r) if abs(complex(r).imag) < 1e-12 else r, m))
    return _simetrizar(out2), False


def _simetrizar(raices):
    """Fuerza que cada raíz compleja tenga su conjugada exacta (los polinomios reales las tienen)."""
    out, vistos = [], []
    for r, m in raices:
        if r.is_real:
            out.append((sp.re(r), m))
            continue
        if any(abs(complex(r - v)) < 1e-9 or abs(complex(sp.conjugate(r) - v)) < 1e-9 for v in vistos):
            continue
        rep = r if complex(r).imag > 0 else sp.conjugate(r)
        vistos.append(rep)
        out += [(rep, m), (sp.conjugate(rep), m)]
    return out


def _mult(raices, lam) -> int:
    for r, m in raices:
        if abs(complex(r - lam)) < 1e-9:
            return m
    return 0


# ------------------------------------------------------- solución homogénea
def solucion_homogenea(L_: EDLineal, res: Resultado):
    """Añade los pasos de y_h. Devuelve (y_h, constantes, raíces)."""
    n = L_.n
    res.pasos.append(Paso("Escribir el operador lineal D = d/dx", "y⁽ᵏ⁾ = Dᵏ y", L_.ed.lhs.__str__() if False else latex(L_.ed.lhs) + " = " + latex(L_.ed.rhs),
                          rf"\left({latex(L_.P)}\right)y = {latex(L_.Q)}" if not L_.homogenea else rf"\left({latex(L_.P)}\right)y = 0",
                          "Se escribe la ecuación con $F(D)\\,y = Q(x)$. La solución es $y = y_h + y_p$."))
    if L_.factor != 1:
        res.pasos.append(Paso("Dividir entre el factor común de los coeficientes", "a_k(x) = h(x)·c_k", "",
                              rf"\text{{dividir entre }} {latex(L_.factor)}\ \Rightarrow\ \left({latex(L_.P)}\right)y = {latex(L_.Q)}",
                              "Todos los coeficientes tienen el mismo factor $h(x)$: al dividir quedan constantes y el término independiente es $Q(x)/h(x)$."))
    raices, exactas = raices_caracteristicas(L_.P)
    p_fact = sp.factor(L_.P) if exactas else None
    res.pasos.append(Paso("Resolver la ecuación característica para y_h (F(D) = 0)", "F(D) = 0",
                          latex(L_.P) + " = 0" + (rf"\ ;\quad {latex(p_fact)} = 0" if p_fact is not None and p_fact != L_.P else ""),
                          r"\ ;\quad ".join(_txt_raiz(r, m) for r, m in raices),
                          ("Raíces exactas." if exactas else
                           "El polinomio no se factoriza en factores de grado ≤ 2 con coeficientes racionales: "
                           "las raíces se calculan numéricamente (4 cifras en pantalla).")))
    if not exactas:
        res.advertencias.append(
            "Las raíces de la ecuación característica no son exactas y se calcularon numéricamente. "
            "Si el enunciado debía tener raíces «bonitas», puede haber un error de transcripción en los coeficientes.")
    sol, cs = base_solucion(raices)
    nota = NOTA_A8 if any(m > 1 for _, m in raices) else None
    res.pasos.append(Paso("Escribir la solución homogénea y_h", "e^(rx), x^j e^(rx), e^(ax) cos bx, e^(ax) sen bx", "",
                          "y_h = " + L(sol), "Raíz real $r$: $e^{rx}$; par $a\\pm bi$: $e^{ax}\\cos bx$, $e^{ax}\\operatorname{sen}bx$; "
                          "multiplicidad $m$: factores $1, x, \\dots, x^{m-1}$.", discrepancia=nota))
    return sol, cs, raices


def _txt_raiz(r, m) -> str:
    base = f"D = {L(r)}" if r.is_real else f"D = {L(r)}"
    return base + (rf"\ \text{{(mult. {m})}}" if m > 1 else "")


# --------------------------------------------------- términos de Q(x)
@dataclass
class Grupo:
    a: sp.Expr                 # exponente real de e^(ax)
    trig: str | None           # "sin" | "cos" | None
    b: sp.Expr                 # frecuencia (0 si no hay trig)
    fase: sp.Expr              # φ en sen(bx+φ)
    poli: sp.Expr              # P(x), polinomio real
    original: sp.Expr

    @property
    def grado(self) -> int:
        return int(sp.degree(self.poli, x)) if self.poli.has(x) else 0


def _lineal_en_x(arg: sp.Expr):
    arg = sp.expand(arg)
    a = sp.diff(arg, x)
    if a.has(x):
        return None
    return a, sp.simplify(arg - a * x)


def _grupos(Q: sp.Expr) -> list[Grupo]:
    """Descompone Q(x) en grupos c·P(x)·e^(ax)·trig(bx+φ). Lanza NoAplica si no tiene esa forma."""
    Q = sp.expand(Q)
    acum: dict[tuple, list] = {}
    for term in sp.Add.make_args(Q):
        coef, k, a, trig, b, fase = sp.Integer(1), 0, sp.Integer(0), None, sp.Integer(0), sp.Integer(0)
        for f in sp.Mul.make_args(term):
            if not f.has(x):
                coef *= f
            elif f == x:
                k += 1
            elif isinstance(f, sp.Pow) and f.base == x and f.exp.is_Integer and f.exp > 0:
                k += int(f.exp)
            elif isinstance(f, sp.exp):
                r = _lineal_en_x(f.args[0])
                if r is None or not r[0].is_real or r[0].has(sp.I):
                    raise NoAplica("Q(x) tiene una exponencial que no es e^(ax+c) con a real.")
                a += r[0]
                coef *= sp.exp(r[1])
            elif isinstance(f, (sp.sin, sp.cos)) and trig is None:
                r = _lineal_en_x(f.args[0])
                if r is None or r[0] == 0:
                    raise NoAplica("Q(x) tiene sen/cos de un argumento no lineal en x.")
                trig, b, fase = ("sin" if isinstance(f, sp.sin) else "cos"), r[0], r[1]
                if b < 0:
                    b, fase = -b, -fase
                    if trig == "sin":
                        coef *= -1
            else:
                raise NoAplica(f"Q(x) contiene «{latex(f)}», que no es de la forma xᵏ, e^(ax), sen(bx+φ) o cos(bx+φ). "
                               "Prueba variación de parámetros.")
        key = (a, trig, b, fase)
        acum.setdefault(key, [0, term])
        acum[key][0] += coef * x ** k
    grupos = []
    for (a, trig, b, fase), (poli, ej) in acum.items():
        poli = sp.expand(poli)
        if poli != 0:
            grupos.append(Grupo(a, trig, b, fase, poli, ej))
    # orden estable: constantes/polinomios, exponenciales, trigonométricas
    return grupos


def _Q_grupo(g: Grupo) -> sp.Expr:
    base = g.poli * sp.exp(g.a * x)
    if g.trig is None:
        return base
    f = sp.sin if g.trig == "sin" else sp.cos
    return base * f(g.b * x + g.fase)


# ----------------------------------------------- operador inverso 1/F(D)
def _inv_poli(Fs: sp.Expr, P: sp.Expr):
    """1/Fs(D) aplicado al polinomio P(x). Devuelve (R, s, serie): s = orden del cero en D=0."""
    Fs = sp.expand(Fs)
    pol = sp.Poly(Fs, D)
    coefs = pol.all_coeffs()[::-1]  # a_0, a_1, ...
    s = next(i for i, c in enumerate(coefs) if sp.simplify(c) != 0)
    G = sum(c * D ** (i - s) for i, c in enumerate(coefs) if i >= s)
    k = int(sp.degree(P, x)) if P.has(x) else 0
    serie = sp.series(1 / G, D, 0, k + 1).removeO() if k >= 0 else 1 / G
    R = sp.Integer(0)
    for j in range(k + 1):
        cj = sp.simplify(serie.coeff(D, j))
        R += cj * sp.diff(P, x, j)
    for _ in range(s):
        R = sp.integrate(R, x)
    return sp.expand(R), s, sp.expand(serie)


def _particular_grupo(Pol: sp.Expr, g: Grupo):
    """y_p del grupo g con F(D) = Pol. Devuelve (y, info) con info para los pasos."""
    lam = g.a + sp.I * g.b
    Fs = sp.expand(Pol.subs(D, D + lam))
    R, s, serie = _inv_poli(Fs, g.poli)
    info = {"lam": lam, "Fs": Fs, "s": s, "serie": serie}
    if g.trig is None:
        return sp.exp(g.a * x) * sp.simplify(R), info
    xr = sp.Symbol("xr", real=True)
    R1, R2 = sp.expand_complex(R.subs(x, xr)).as_real_imag() if False else (None, None)
    Rr = sp.expand(R.subs(x, xr))
    R1, R2 = sp.re(Rr), sp.im(Rr)
    R1, R2 = sp.simplify(R1.subs(xr, x)), sp.simplify(R2.subs(xr, x))
    th = g.b * x + g.fase
    if g.trig == "sin":
        y_ = R1 * sp.sin(th) + R2 * sp.cos(th)
    else:
        y_ = R1 * sp.cos(th) - R2 * sp.sin(th)
    return sp.exp(g.a * x) * y_, info


def _caso(g: Grupo) -> str:
    if g.trig is None and g.grado == 0 and g.a == 0:
        return "Constante (Caso I con a = 0)"
    if g.trig is None and g.grado == 0:
        return "Caso I: e^(ax)"
    if g.trig is None and g.a == 0:
        return "Polinomio: división de 1/F(D)"
    if g.trig is None:
        return "Caso III: e^(ax)·V(x) con V polinomio"
    if g.a == 0 and g.grado == 0:
        return "Caso II: " + ("sen" if g.trig == "sin" else "cos") + "(bx + φ)"
    if g.grado == 0:
        return "Caso III: e^(ax)·" + ("sen" if g.trig == "sin" else "cos") + "(bx + φ)"
    return "Polinomio por " + ("sen" if g.trig == "sin" else "cos") + (" y exponencial" if g.a != 0 else "")


def _pasos_grupo(res: Resultado, L_: EDLineal, g: Grupo, yp, info, raices):
    Q = _Q_grupo(g)
    caso = _caso(g)
    lam, s, Fs = info["lam"], info["s"], info["Fs"]
    antes = rf"y_p = \frac{{{L(Q)}}}{{F(D)}}"
    expl = []
    if g.trig is None and g.grado == 0:
        Fa = sp.simplify(L_.P.subs(D, g.a))
        expl.append(f"$a={L(g.a)}$ y $F({L(g.a)})={L(Fa)}$.")
        if Fa != 0:
            desp = rf"y_p = \frac{{{L(g.poli)}\,e^{{{L(g.a * x)}}}}}{{F({L(g.a)})}} = {L(yp)}"
        else:
            desp = rf"y_p = {L(yp)}"
    elif g.trig is not None and g.grado == 0 and g.a == 0:
        b2 = g.b ** 2
        pol = sp.expand(L_.P)
        resto = sp.Poly(pol, D)
        if s == 0:
            # D² -> -b²: F(D) -> α + βD
            red = sp.expand(sp.rem(sp.Poly(pol, D), sp.Poly(D ** 2 + b2, D)).as_expr())
            alpha, beta = red.coeff(D, 0), red.coeff(D, 1)
            expl.append(f"$D^2\\to -{L(b2)}$: $F(D)\\to {L(alpha)} + ({L(beta)})D$, no es cero: se racionaliza multiplicando por el conjugado.")
        else:
            expl.append(f"$F(-b^2)=0$ con $b={L(g.b)}$: hay resonancia (la raíz $\\pm {L(g.b)}i$ es de multiplicidad {s}); "
                        f"la solución se multiplica por $x^{s}$.")
        desp = rf"y_p = {L(yp)}"
    else:
        expl.append(f"Se desplaza el operador: $F(D)\\to F(D+{L(lam)})$." if lam != 0 else "")
        if s > 0:
            expl.append(f"Resonancia: $F(D+{L(lam)})$ tiene el factor $D^{s}$; se integra {s} vez/veces después de aplicar la serie.")
        if g.grado > 0 or lam != 0:
            serie_txt = L(sp.expand(sp.series(1 / (sp.expand(Fs) / D ** s).expand(), D, 0, g.grado + 1).removeO())) if s >= 0 else ""
            expl.append(f"$1/F(D{'+' + L(lam) if lam != 0 else ''}) = D^{{-{s}}}\\left({serie_txt}+\\cdots\\right)$.")
        desp = rf"y_p = {L(yp)}"
    res.pasos.append(Paso(f"Término ${L(g.original)}$: {caso}", "método abreviado: y_p = Q(x)/F(D)", antes, desp,
                          " ".join(e for e in expl if e)))


def particular_abreviado(L_: EDLineal, res: Resultado, raices) -> sp.Expr:
    grupos = _grupos(L_.Q)
    total = sp.Integer(0)
    res.pasos.append(Paso("Determinar la solución particular y_p (Q(x)/F(D))", "y_p = Q(x)/F(D)",
                          rf"y_p = \frac{{{L(L_.Q)}}}{{{latex(L_.P)}}}", "",
                          f"Q(x) se separa en {len(grupos)} término(s) y se aplica 1/F(D) a cada uno; las soluciones se suman."))
    for g in grupos:
        yp, info = _particular_grupo(L_.P, g)
        _pasos_grupo(res, L_, g, yp, info, raices)
        total += yp
    return sp.simplify(total) if not total.has(sp.Float) else total


# --------------------------------------------------------------- resolver
def _finalizar(res: Resultado, L_: EDLineal, general: sp.Expr, cs, condiciones, yp=None):
    from ..conceptos.constantes import determinar_constantes
    res.valor = general
    res.solucion = "y = " + L(general)
    res.constantes = [c.name for c in cs]
    res.particular = yp
    if yp is not None:
        nota = discrepancias.nota("particular", L_.ed)
        for p in res.pasos:
            if "Solución particular y_p" in p.titulo:
                p.discrepancia = (NOTA_A15 + (" " + nota if nota else ""))
    if condiciones:
        det = determinar_constantes(L_.ed, sp.Symbol("y"), general, condiciones)
        res.pasos += [s for s in det.pasos[1:] if s.titulo != "Comprobación"]
        res.advertencias += det.advertencias
        if det.valor is not None:
            res.valor, res.solucion, res.constantes = det.valor, "y = " + L(det.valor), []
            res.verificacion = det.verificacion
            return res
    v = verificar_explicita(L_.ed, general)
    res.verificacion = v
    if not v.ok:
        res.advertencias.append("La verificación por sustitución no confirmó la solución: no la tomes como correcta.")
    return res


def resolver_abreviado(ed: ED, condiciones=None) -> Resultado:
    L_ = leer_lineal(ed)
    res = Resultado("método abreviado (operador D)")
    yh, cs, raices = solucion_homogenea(L_, res)
    if L_.homogenea:
        res.pasos.append(Paso("Escribir la solución", "y = y_h", "", "y = " + L(yh)))
        return _finalizar(res, L_, yh, cs, condiciones)
    yp = particular_abreviado(L_, res, raices)
    res.pasos.append(Paso("Solución particular y_p (el texto la llama y_c)", "suma de las soluciones de cada término", "",
                          "y_p = " + L(yp)))
    general = yh + yp
    res.pasos.append(Paso("Solución final: y = y_h + y_p", "y = y_h + y_p", "", "y = " + L(general)))
    return _finalizar(res, L_, general, cs, condiciones, yp)


# ------------------------------------------------- coeficientes indeterminados
def _familias(grupos: list[Grupo], raices):
    """[(a, b, grado)] fusionando grupos con la misma exponencial y frecuencia."""
    fam: dict[tuple, int] = {}
    for g in grupos:
        key = (g.a, g.b if g.trig else sp.Integer(0))
        fam[key] = max(fam.get(key, 0), g.grado)
    return [(a, b, k) for (a, b), k in fam.items()]


def resolver_coef_indeterminados(ed: ED, condiciones=None) -> Resultado:
    L_ = leer_lineal(ed)
    if L_.homogenea:
        raise NoAplica("La ecuación es homogénea: no hay solución particular que proponer.")
    grupos = _grupos(L_.Q)
    res = Resultado("coeficientes indeterminados")
    yh, cs, raices = solucion_homogenea(L_, res)
    familias = _familias(grupos, raices)
    # solución propuesta
    incog: list[sp.Symbol] = []
    yp = sp.Integer(0)
    partes_txt = []
    modif = []
    letras = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for a, b, k in familias:
        lam = a + sp.I * b
        s = _mult(raices, lam)
        def poli():
            cs_ = [sp.Symbol(next(letras)) for _ in range(k + 1)]
            incog.extend(cs_)
            return sum(c * x ** j for j, c in enumerate(cs_[::-1])), cs_
        if b == 0:
            P_, _ = poli()
            prop0 = P_ * sp.exp(a * x)
            prop = x ** s * prop0
        else:
            Pc, _ = poli()
            Ps, _ = poli()
            prop0 = (Pc * sp.cos(b * x) + Ps * sp.sin(b * x)) * sp.exp(a * x)
            prop = x ** s * prop0
        partes_txt.append(L(prop0))
        if s > 0:
            modif.append(f"La raíz ${L(lam)}$ asociada a este término tiene multiplicidad {s} en la ecuación característica: "
                         f"se multiplica por $x^{s}$ (A11: no depende del grado de $Q$ sino de la multiplicidad).")
        yp += prop
    res.pasos.append(Paso("Segundo paso. Proponer la solución particular y_p según Q(x)", "y_p = forma de Q(x)",
                          "Q(x) = " + L(L_.Q), "y_p = " + " + ".join(partes_txt),
                          "Q(x) es polinomio, exponencial, seno o coseno (o productos): se propone la misma forma con coeficientes por determinar."))
    if modif:
        res.pasos.append(Paso("Modificar el método", "y_p = xˢ · (forma propuesta)", "", "y_p = " + L(yp), " ".join(modif)))
    derivs = [yp] + [sp.diff(yp, x, k) for k in range(1, L_.n + 1)]
    res.pasos.append(Paso("Determinar las derivadas de la función propuesta", "derivación",
                          "", r"\ ;\quad ".join((f"y_p{chr(39) * k} = " if k <= 3 else f"y_p^{{({k})}} = ") + L(sp.simplify(d)) for k, d in enumerate(derivs) if k > 0)))
    # sustituir
    residuo = sp.expand(sum(sp.Poly(L_.P, D).coeff_monomial(D ** k) * derivs[k] for k in range(L_.n + 1)) - _Q_canon(grupos))
    res.pasos.append(Paso("Reemplazar y, y′, … en la ecuación diferencial y simplificar", "sustitución",
                          rf"\left({latex(L_.P)}\right)y_p = {L(L_.Q)}", L(sp.collect(residuo, x)) + " = 0"))
    # sistema: se sustituyen exp/cos/sin por símbolos independientes
    reemplazos, simbolos = {}, []
    for e in sorted(residuo.atoms(sp.exp, sp.sin, sp.cos), key=str):
        s_ = sp.Dummy("f")
        reemplazos[e] = s_
        simbolos.append(s_)
    poly = sp.Poly(sp.expand(residuo.xreplace(reemplazos)), x, *simbolos)
    ecs = [c for c in poly.coeffs()]
    sol = sp.solve(ecs, incog, dict=True)
    if not sol:
        raise NoAplica("El sistema para los coeficientes no tiene solución (revisa la forma propuesta).")
    sol = sol[0]
    sol = {k: sol.get(k, sp.Integer(0)) for k in incog}
    sistema = r"\begin{cases} " + r" \\ ".join(L(sp.simplify(e)) + " = 0" for e in ecs) + r" \end{cases}"
    res.pasos.append(Paso("Formar el sistema de ecuaciones para los coeficientes", "igualar coeficientes", "", sistema,
                          "Se igualan a cero los coeficientes de cada potencia de $x$ y de cada función independiente."))
    res.pasos.append(Paso("Resolver el sistema", "sistema lineal", "", r"\ ;\quad ".join(f"{latex(k)} = {L(v)}" for k, v in sol.items())))
    ypf = simplificar(sp.expand(yp.subs(sol)))
    res.pasos.append(Paso("Solución particular y_p (el texto la llama y_c)", "reemplazar los valores", "",
                          "y_p = " + L(ypf)))
    general = yh + ypf
    res.pasos.append(Paso("Tercer paso. Escribir la solución de la ecuación diferencial", "y = y_h + y_p", "", "y = " + L(general)))
    return _finalizar(res, L_, general, cs, condiciones, ypf)


def _Q_canon(grupos: list[Grupo]) -> sp.Expr:
    """Q(x) con sen(bx+φ), cos(bx+φ) abiertos en sen(bx), cos(bx) para igualar coeficientes."""
    total = sp.Integer(0)
    for g in grupos:
        base = g.poli * sp.exp(g.a * x)
        if g.trig is None:
            total += base
            continue
        sb, cb = sp.sin(g.b * x), sp.cos(g.b * x)
        cf, sf = sp.cos(g.fase), sp.sin(g.fase)
        if g.trig == "sin":
            total += base * (sb * cf + cb * sf)
        else:
            total += base * (cb * cf - sb * sf)
    return total


def aplica_coef_indeterminados(ed: ED) -> str | None:
    if ed.orden < 1:
        return None
    try:
        L_ = leer_lineal(ed)
        if L_.homogenea:
            return None
        _grupos(L_.Q)
    except NoAplica:
        return None
    return "coeficientes constantes y Q(x) polinomial, exponencial o trigonométrica"


def resolver_homogenea_cc(ed: ED, condiciones=None) -> Resultado:
    L_ = leer_lineal(ed)
    if not L_.homogenea:
        raise NoAplica("La ecuación no es homogénea.")
    return resolver_abreviado(ed, condiciones)
