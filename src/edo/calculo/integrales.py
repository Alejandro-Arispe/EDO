"""Integrales indefinidas con pasos en español.

El plan de integración lo da ``integral_steps`` de SymPy (árbol de reglas al estilo
de un estudiante); aquí cada regla se traduce a un Paso. Si en el árbol aparece una
función especial (erf, Ei, Si, ...) o SymPy no sabe, la integral se deja indicada.
"""
from __future__ import annotations

import sympy as sp
from sympy.integrals import manualintegrate as mi

from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.paso import Paso
from ..core.verificador import es_cero
from .resultado import ResultadoCalculo

_ESPECIALES = tuple(
    getattr(mi, n) for n in (
        "DontKnowRule", "ErfRule", "EiRule", "SiRule", "CiRule", "ShiRule", "ChiRule", "LiRule",
        "PolylogRule", "FresnelSRule", "FresnelCRule", "UpperGammaRule", "EllipticERule",
        "EllipticFRule", "IRule", "DiracDeltaRule", "HeavisideRule", "PiecewiseRule",
    ) if hasattr(mi, n)
)
_NOMBRES_ESPECIALES = {
    "ErfRule": "función error erf", "EiRule": "integral exponencial Ei", "SiRule": "seno integral Si",
    "CiRule": "coseno integral Ci", "ShiRule": "Shi", "ChiRule": "Chi", "LiRule": "logaritmo integral li",
    "FresnelSRule": "integral de Fresnel", "FresnelCRule": "integral de Fresnel",
    "PolylogRule": "polilogaritmo", "UpperGammaRule": "gamma incompleta",
}
_TABLA = {  # reglas atómicas de tabla -> (título, fórmula)
    "SinRule": ("Integral de sen u", r"\int \operatorname{sen}u\,du = -\cos u"),
    "CosRule": ("Integral de cos u", r"\int \cos u\,du = \operatorname{sen}u"),
    "Sec2Rule": ("Integral de sec² u", r"\int \sec^2 u\,du = \operatorname{tg}u"),
    "Csc2Rule": ("Integral de csc² u", r"\int \csc^2 u\,du = -\operatorname{ctg}u"),
    "SecTanRule": ("Integral de sec u·tg u", r"\int \sec u\operatorname{tg}u\,du = \sec u"),
    "CscCotRule": ("Integral de csc u·ctg u", r"\int \csc u\operatorname{ctg}u\,du = -\csc u"),
    "SinhRule": ("Integral de senh u", r"\int \operatorname{senh}u\,du = \cosh u"),
    "CoshRule": ("Integral de cosh u", r"\int \cosh u\,du = \operatorname{senh}u"),
    "ArcsinRule": ("Integral de 1/√(1−u²)", r"\int \frac{du}{\sqrt{1-u^2}} = \operatorname{arcsen}u"),
}


class _NoElemental(Exception):
    def __init__(self, regla):
        self.regla = regla


def _int(f, v) -> str:
    return rf"\int {latex(f)}\,d{v}"


class _Traductor:
    def __init__(self):
        self.pasos: list[Paso] = []

    def paso(self, titulo, regla, regla_obj, expl="", valor=None, antes=None):
        v = regla_obj.variable
        val = regla_obj.eval() if valor is None else valor
        self.pasos.append(Paso(titulo, regla, antes or _int(regla_obj.integrand, v), latex(val), expl))
        return val

    def tr(self, r) -> sp.Expr:
        nombre = type(r).__name__
        if isinstance(r, _ESPECIALES):
            raise _NoElemental(r)
        v = r.variable
        f = r.integrand
        if nombre == "ConstantRule":
            return self.paso("Integral de una constante", r"\int c\,dx = c\,x", r)
        if nombre == "ConstantTimesRule":
            self.pasos.append(Paso("Sacar la constante", r"\int c\,f\,dx = c\int f\,dx", _int(f, v),
                                   rf"{latex(r.constant)}\,{_int(r.other, v)}",
                                   f"${latex(r.constant)}$ es constante y sale de la integral."))
            self.tr(r.substep)
            return r.eval()
        if nombre == "PowerRule":
            return self.paso("Regla de la potencia", r"\int x^n\,dx = \frac{x^{n+1}}{n+1},\ n\neq -1", r,
                             f"Con $n={latex(r.exp)}$.")
        if nombre == "AddRule":
            self.pasos.append(Paso("Integral de una suma", r"\int (f+g)\,dx = \int f\,dx + \int g\,dx",
                                   _int(f, v), " + ".join(_int(s.integrand, v) for s in r.substeps),
                                   "Se integra término a término."))
            for s in r.substeps:
                self.tr(s)
            return r.eval()
        if nombre == "URule":
            u, uf = r.u_var, r.u_func
            du = sp.diff(uf, v)
            self.pasos.append(Paso(
                "Sustitución (cambio de variable)", r"u = g(x),\ du = g'(x)\,dx", _int(f, v),
                _int(r.substep.integrand, u),
                f"Sea $u={latex(uf)}$; entonces $du={latex(du)}\\,d{v}$."))
            self.tr(r.substep)
            val = r.eval()
            self.pasos.append(Paso("Volver a la variable original", "", f"u = {latex(uf)}", latex(val),
                                   f"Se reemplaza $u={latex(uf)}$ en el resultado."))
            return val
        if nombre == "PartsRule":
            return self._partes(r, ciclica=False)
        if nombre == "CyclicPartsRule":
            return self._ciclica(r)
        if nombre == "RewriteRule":
            self.pasos.append(Paso("Reescribir el integrando", "álgebra / identidades", _int(f, v),
                                   _int(r.rewritten, v), "Se transforma el integrando a una forma integrable."))
            self.tr(r.substep)
            return r.eval()
        if nombre == "CompleteSquareRule":
            self.pasos.append(Paso("Completar el cuadrado", "a x² + b x + c = a(x + b/2a)² + …", _int(f, v),
                                   _int(r.rewritten, v)))
            self.tr(r.substep)
            return r.eval()
        if nombre == "AlternativeRule":
            return self.tr(r.alternatives[0])
        if nombre == "ExpRule":
            if r.base == sp.E:
                return self.paso("Integral de eˣ", r"\int e^u\,du = e^u", r)
            return self.paso("Integral de aˣ", r"\int a^x\,dx = \frac{a^x}{\ln a}", r)
        if nombre == "ReciprocalRule":
            return self.paso("Integral de 1/u", r"\int \frac{du}{u} = \ln|u|", r,
                             "Se escribe $\\ln u$ cuando $u>0$; en general lleva valor absoluto.")
        if nombre == "ArctanRule":
            return self.paso("Integral que da arco tangente", r"\int \frac{du}{u^2+a^2} = \frac1a\operatorname{arctg}\frac ua", r)
        if nombre == "TrigSubstitutionRule":
            self.pasos.append(Paso(
                "Sustitución trigonométrica", "", _int(f, v), _int(r.rewritten, r.theta),
                f"Se hace ${v}={latex(r.func)}$ (válido si {latex(r.restriction)})."))
            self.tr(r.substep)
            val = r.eval()
            self.pasos.append(Paso("Volver a la variable original", "", "", latex(val)))
            return val
        if nombre in _TABLA:
            titulo, formula = _TABLA[nombre]
            return self.paso(titulo, formula, r)
        if nombre == "TrigRule" or isinstance(r, mi.AtomicRule):
            titulo = "Integral de tabla"
            return self.paso(titulo, "fórmula de tabla", r)
        if nombre == "DerivativeRule":
            return self.paso("Integral de una derivada", r"\int F'(x)\,dx = F(x)", r)
        if nombre == "NestedPowRule":
            return self.paso("Potencia de potencia", "", r)
        # SqrtQuadratic*, etc.: fórmula de tabla compuesta
        return self.paso("Fórmula de integral", "fórmula de tabla (ver el siguiente resultado)", r,
                         f"Se aplica una fórmula estándar para este tipo de integrando ({nombre}).")

    def _partes(self, r, ciclica) -> sp.Expr:
        v = r.variable
        u, dv = r.u, r.dv
        du = sp.diff(u, v)
        vv = r.v_step.eval()
        f = r.integrand
        self.pasos.append(Paso(
            "Integración por partes", r"\int u\,dv = u\,v - \int v\,du", _int(f, v),
                rf"{latex(u)}\cdot {latex(vv)} - \int {latex(vv)}\,\left({latex(du)}\right)d{v}",
                f"Sea $u={latex(u)}$ y $dv={latex(dv)}\\,d{v}$; entonces $du={latex(du)}\\,d{v}$ y $v={latex(vv)}$."))
        if not ciclica and r.second_step is not None:
            self.tr(r.second_step)
            return r.eval()
        return vv

    def _ciclica(self, r) -> sp.Expr:
        v = r.variable
        actual = r.integrand
        for pr in r.parts_rules:
            u, dv = pr.u, pr.dv
            du = sp.diff(u, v)
            vv = pr.v_step.eval()
            self.pasos.append(Paso(
                "Integración por partes", r"\int u\,dv = u\,v - \int v\,du", _int(actual, v),
                rf"{latex(u)}\cdot {latex(vv)} - \int {latex(vv)}\,\left({latex(du)}\right)d{v}",
                f"Sea $u={latex(u)}$ y $dv={latex(dv)}\\,d{v}$; entonces $du={latex(du)}\\,d{v}$ y $v={latex(vv)}$."))
            actual = sp.expand(vv * du)
        val = r.eval()
        self.pasos.append(Paso(
            "Despejar la integral (partes cíclicas)", "I = (…) + k·I ⟹ I = (…)/(1−k)", _int(r.integrand, v), latex(val),
            f"Después de aplicar partes la integral original reaparece con coeficiente ${latex(r.coefficient)}$; se despeja $I$."))
        return val


def integrar(expr: sp.Expr, var: sp.Symbol) -> ResultadoCalculo:
    """Integral indefinida de expr respecto de var, con pasos. valor=None si no es elemental."""
    expr = sp.sympify(expr)
    enun = _int(expr, var)
    try:
        arbol = mi.integral_steps(expr, var)
    except Exception as exc:
        return _no_elemental(expr, var, enun, f"SymPy no pudo planear la integral ({type(exc).__name__}).")
    tr = _Traductor()
    try:
        valor = tr.tr(arbol)
    except _NoElemental as ne:
        esp = _NOMBRES_ESPECIALES.get(type(ne.regla).__name__)
        motivo = (f"Esta integral se expresa con una función especial ({esp}), no elemental."
                  if esp else "No encontré una antiderivada elemental con las reglas del curso.")
        return _no_elemental(expr, var, enun, motivo)
    except Exception as exc:
        return _no_elemental(expr, var, enun, f"No pude traducir el procedimiento ({type(exc).__name__}).")
    finally:
        mi._parts_u_cache.clear()
    valor = _quitar_piecewise(valor)
    simple = simplificar(valor)
    pasos = tr.pasos
    if simple != valor:
        pasos.append(Paso("Simplificar", "álgebra", latex(valor), latex(simple)))
    pasos.append(Paso("Resultado", "", enun, latex(simple) + " + C",
                      "Se suma la constante de integración $C$."))
    verif = es_cero(sp.diff(simple, var) - expr)
    return ResultadoCalculo(expr, simple, pasos, [], verif, True, enun, latex(simple) + " + C")


def _quitar_piecewise(e: sp.Expr) -> sp.Expr:
    if isinstance(e, sp.Piecewise):
        if len(e.args) == 2 and e.args[1][1] == True and isinstance(e.args[0][1], sp.Eq):  # noqa: E712
            return e.args[1][0]
        return e.args[0][0]
    return e


def _no_elemental(expr, var, enun, motivo) -> ResultadoCalculo:
    paso = Paso("Integral no elemental", "", enun, enun, motivo + " Se deja indicada.")
    return ResultadoCalculo(expr, None, [paso], [motivo + " La integral queda indicada."], None, False,
                            enun, enun)
