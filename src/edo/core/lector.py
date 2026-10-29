"""Lector de entrada flexible.

Acepta ``y'+2y=x e^x``, ``dy/dx``, ``d^2y/dx^2``, ``y^(4)``, forma diferencial
``(x+y)dx-(x-y)dy=0``, notación D ``(D^2-3D+2)y=e^x`` y funciones en español.

Convenciones de escritura:
  * ``e^2x`` y ``e^-x`` se leen como e^(2x) y e^(-x) (el exponente llega hasta el
    primer espacio u operador); ``e^(x/y)`` con paréntesis para exponentes compuestos.
  * ``sen2x`` / ``sen x`` = sen(2x) / sen(x); ``sen^2 x`` = (sen x)^2.
  * Un producto con la ``d`` de la forma diferencial se escribe ``x dx`` o ``(x+y)dx``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication, parse_expr, split_symbols, standard_transformations,
)

x = sp.Symbol("x")
ys = sp.Symbol("y")  # y como símbolo (formas diferenciales, soluciones implícitas)
y = sp.Function("y")  # y(x) como función incógnita
D = sp.Symbol("D")
_DIFX, _DIFY = sp.Symbol("DIFX"), sp.Symbol("DIFY")
_MAX_ORDEN = 12
_YD = {k: sp.Symbol(f"Yd{k}") for k in range(1, _MAX_ORDEN + 1)}


class ErrorLectura(ValueError):
    """La entrada no se pudo interpretar; el mensaje está en español."""


# --------------------------------------------------------------------------- LaTeX
def _cerrar(s: str, i: int, ab: str = "{", ce: str = "}") -> int:
    """Índice del cierre que corresponde a la apertura s[i]."""
    n = 0
    for j in range(i, len(s)):
        if s[j] == ab:
            n += 1
        elif s[j] == ce:
            n -= 1
            if n == 0:
                return j
    raise ErrorLectura("Llaves sin cerrar en la expresión LaTeX.")


def desde_latex(s: str) -> str:
    """Convierte el LaTeX que produce MathLive a la notación de texto del lector."""
    s = s.replace("\\left", "").replace("\\right", "")
    s = re.sub(r"\\mathrm\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\operatorname\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\differentialD", "d", s)
    s = s.replace("^{\\prime\\prime\\prime}", "'''").replace("^{\\prime\\prime}", "''")
    s = s.replace("^{\\prime}", "'").replace("\\prime", "'")
    # \frac y \sqrt con anidamiento
    while True:
        m = re.search(r"\\(frac|dfrac|tfrac|sqrt)", s)
        if not m:
            break
        i = m.end()
        if m.group(1) == "sqrt":
            raiz = None
            if i < len(s) and s[i] == "[":
                j = s.index("]", i)
                raiz, i = s[i + 1:j], j + 1
            if i >= len(s) or s[i] != "{":
                raise ErrorLectura("Falta el radicando de \\sqrt.")
            j = _cerrar(s, i)
            arg = desde_latex(s[i + 1:j])
            rep = f"(({arg})^(1/({desde_latex(raiz)})))" if raiz else f"sqrt({arg})"
            s = s[:m.start()] + rep + s[j + 1:]
        else:
            if i >= len(s) or s[i] != "{":
                raise ErrorLectura("Falta el numerador de \\frac.")
            j = _cerrar(s, i)
            num = s[i + 1:j]
            if j + 1 >= len(s) or s[j + 1] != "{":
                raise ErrorLectura("Falta el denominador de \\frac.")
            k = _cerrar(s, j + 1)
            den = s[j + 2:k]
            nc, dc = re.sub(r"\s+", "", num), re.sub(r"\s+", "", den)
            nc, dc = nc.replace("\\partial", "∂"), dc.replace("\\partial", "∂")
            md = re.fullmatch(r"([d∂])(?:\^\{?(\d+)\}?)?([A-Za-z])", nc)
            if md and re.fullmatch(r"(?:[d∂][A-Za-z](?:\^\{?\d+\}?)?)+", dc):
                n = md.group(2)
                num_txt = f"{md.group(1)}{'^' + n if n else ''}{md.group(3)}"
                dens = re.findall(r"([d∂])([A-Za-z])(?:\^\{?(\d+)\}?)?", dc)
                rep = num_txt + "/" + "".join(f"{a}{b}{'^' + c if c else ''}" for a, b, c in dens)
            else:
                rep = f"(({desde_latex(num)})/({desde_latex(den)}))"
            s = s[:m.start()] + rep + s[k + 1:]
    s = s.replace("\\cdot", "*").replace("\\times", "*").replace("\\pi", "pi")
    s = re.sub(r"\\(arcsin|arccos|arctan|sinh|cosh|tanh|sin|cos|tan|cot|sec|csc|ln|log|exp)\b", r"\1", s)
    s = re.sub(r"\\[,;:! ]", " ", s)
    s = s.replace("{", "(").replace("}", ")")
    s = re.sub(r"\\([A-Za-z]+)", r"\1", s)
    return s.strip()


# ------------------------------------------------------------ normalización
_FUNCIONES = {
    "arcsen": "asin", "arcsin": "asin", "arccos": "acos", "arctg": "atan", "arctan": "atan",
    "arcctg": "acot", "arccot": "acot", "arcsec": "asec", "arccsc": "acsc",
    "senh": "sinh", "sinh": "sinh", "cosh": "cosh", "tgh": "tanh", "tanh": "tanh",
    "cosec": "csc", "sen": "sin", "sin": "sin", "cos": "cos", "tg": "tan", "tan": "tan",
    "ctg": "cot", "cot": "cot", "sec": "sec", "csc": "csc",
    "ln": "log", "log": "log", "sqrt": "sqrt", "exp": "exp", "abs": "Abs",
}
_NOMBRES_ORD = sorted(_FUNCIONES, key=len, reverse=True)


def _prefijo_funcion(palabra: str) -> str | None:
    for n in _NOMBRES_ORD:
        if palabra.startswith(n):
            return n
    return None


def _grupo(s: str, i: int) -> int:
    return _cerrar(s, i, "(", ")")


def _atomo_exponente(s: str, i: int) -> int:
    """Fin (exclusivo) de un exponente que empieza en s[i]."""
    if i < len(s) and s[i] == "(":
        return _grupo(s, i) + 1
    j = i
    if j < len(s) and s[j] in "+-":
        j += 1
    while j < len(s) and (s[j].isalnum() or s[j] in "_."):
        j += 1
    return j


def _fin_argumento(s: str, i: int) -> int:
    """Fin (exclusivo) del argumento de una función que empieza en s[i]."""
    if i < len(s) and s[i] == "(":
        return _grupo(s, i) + 1   # sen(x)^2 = (sen x)^2: el exponente no entra en el argumento
    else:
        j = i
        if j < len(s) and s[j] in "+-":
            j += 1
        w0 = re.match(r"[A-Za-z]+", s[j:])
        if w0 and _prefijo_funcion(w0.group(0)) and s[j:].startswith(_prefijo_funcion(w0.group(0))):
            nombre = _prefijo_funcion(w0.group(0))
            k = j + len(nombre)
            if k < len(s) and s[k] == "^":
                k = _atomo_exponente(s, k + 1)
            k2 = k + re.match(r"\s*", s[k:]).end()
            return _fin_argumento(s, k2)
        primero = True
        while j < len(s) and (s[j].isalnum() or s[j] in "_."):
            if s[j].isalpha() and not primero and s[j - 1].isdigit():
                w = re.match(r"[A-Za-z]+", s[j:]).group(0)
                if _prefijo_funcion(w):
                    break
            j += 1
            primero = False
    if j < len(s) and s[j] == "^":  # sen x^2 = sen(x^2)
        j = _atomo_exponente(s, j + 1)
    return j


def _funciones(s: str) -> str:
    """Reescribe e^arg y f arg como exp(arg) y f(arg), recursivamente."""
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isalpha() and (i == 0 or not s[i - 1].isalpha()):
            palabra = re.match(r"[A-Za-z]+", s[i:]).group(0)
            # e^arg (también pegado a un factor: xe^x)
            fin_p = i + len(palabra)
            if (palabra.endswith("e") and not _prefijo_funcion(palabra)
                    and re.match(r"\s*\^", s[fin_p:])):
                out.append(palabra[:-1] + " ")
                i = fin_p - 1
                j = fin_p + re.match(r"\s*\^\s*", s[fin_p:]).end()
                k = _atomo_exponente(s, j)
                if k == j:
                    raise ErrorLectura("Falta el exponente después de e^.")
                arg = s[j:k]
                if arg[0] == "(":
                    arg = arg[1:-1]
                # e^x^2: el exponente se amplía a x^2
                if k < len(s) and s[k] == "^":
                    k2 = _atomo_exponente(s, k + 1)
                    arg = arg + s[k:k2]
                    k = k2
                out.append(f"exp({_funciones(arg)})")
                i = k
                continue
            nombre = _prefijo_funcion(palabra)
            if nombre:
                j = i + len(nombre)
                pot = ""
                if j < len(s) and s[j] == "^":
                    k = _atomo_exponente(s, j + 1)
                    pot = s[j + 1:k]
                    j = k
                m = re.match(r"\s*", s[j:])
                j2 = j + m.end()
                k = _fin_argumento(s, j2)
                if k == j2:
                    raise ErrorLectura(f"Falta el argumento de «{nombre}».")
                arg = s[j2:k]
                inner = arg[1:-1] if arg.startswith("(") and _grupo(arg, 0) == len(arg) - 1 else arg
                llamada = f"{_FUNCIONES[nombre]}({_funciones(inner)})"
                out.append(f"({llamada})**({pot})" if pot else llamada)
                i = k
                continue
            out.append(palabra)
            i += len(palabra)
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _normalizar(s: str) -> str:
    for a, b in (("−", "-"), ("×", "*"), ("·", "*"), ("÷", "/"), ("√", "sqrt"), ("′", "'"),
                 ("²", "^2"), ("³", "^3"), ("π", "pi"), ("\u00a0", " ")):
        s = s.replace(a, b)
    s = re.sub(r"\by\s*\(\s*x\s*\)", "y", s)
    # derivadas d^n y / d x^n
    def _dd(m):
        n = m.group(1) or m.group(2) or "1"
        return f" Yd{int(n)} "
    s = re.sub(r"(?<![A-Za-z])d\s*\^?\s*\{?(\d*)\}?\s*y\s*/\s*d\s*x\s*\^?\s*\{?(\d*)\}?", _dd, s)
    s = re.sub(r"y\^\{?\((\d+)\)\}?", lambda m: f" Yd{int(m.group(1))} ", s)
    s = re.sub(r"y('+)", lambda m: f" Yd{len(m.group(1))} ", s)
    # diferenciales
    s = re.sub(r"d([xy])(?![A-Za-z0-9_])", lambda m: f" DIF{m.group(1).upper()} ", s)
    s = s.replace("?", " QQ ")
    s = _funciones(s)
    return s


_TRANSF = standard_transformations + (split_symbols, implicit_multiplication, convert_xor)
QQ = sp.Symbol("QQ")  # «?»: M o N desconocido (hallar para que sea exacta)
_LOCAL = {"QQ": QQ, "x": x, "y": ys, "e": sp.E, "D": D, "DIFX": _DIFX, "DIFY": _DIFY, "pi": sp.pi,
          **{f"Yd{k}": v for k, v in _YD.items()},
          "C": sp.Symbol("C"), **{f"C{k}": sp.Symbol(f"C{k}") for k in range(1, 13)}}
# parámetros con subíndice numérico (P0, T1, v0, ...) son un solo símbolo, no un producto
import string as _string
_LOCAL.update({f"{c}{d}": sp.Symbol(f"{c}{d}") for c in _string.ascii_letters if c not in "eDY" for d in "0123456789"})


def _parsear(s: str) -> sp.Expr:
    s = s.strip()
    if not s:
        raise ErrorLectura("La expresión está vacía.")
    try:
        return parse_expr(_normalizar(s), local_dict=dict(_LOCAL), transformations=_TRANSF, evaluate=True)
    except ErrorLectura:
        raise
    except Exception as exc:  # SyntaxError, TypeError, etc.
        raise ErrorLectura(f"No pude interpretar «{s}»: {exc}") from exc


def _partir_igualdad(s: str) -> tuple[str, str]:
    if s.count("=") > 1:
        raise ErrorLectura("Hay más de un signo «=».")
    if "=" in s:
        a, b = s.split("=")
        return a, b
    return s, "0"


# ------------------------------------------------------------------ resultado
def a_funcion(e: sp.Expr) -> sp.Expr:
    """Convierte y -> y(x) y Yd_k -> Derivative(y(x), (x, k))."""
    rep = {v: sp.Derivative(y(x), (x, k)) for k, v in _YD.items()}
    return e.subs(rep).subs(ys, y(x))


@dataclass
class ED:
    original: str
    forma: str                      # "derivada" | "diferencial" | "operador"
    lhs: sp.Expr                    # en términos de y(x) y sus derivadas
    rhs: sp.Expr
    orden: int
    M: sp.Expr | None = None        # forma diferencial: M dx + N dy = 0 (con y símbolo)
    N: sp.Expr | None = None
    operador: sp.Expr | None = None  # forma D: polinomio P(D) con P(D)y = rhs
    notas: list[str] = field(default_factory=list)

    @property
    def expr(self) -> sp.Expr:
        """F(x, y, y', ...) con ED escrita como F = 0."""
        return self.lhs - self.rhs

    def to_dict(self) -> dict:
        from .latex import latex
        d = {"original": self.original, "forma": self.forma, "orden": int(self.orden),
             "latex": f"{latex(self.lhs)} = {latex(self.rhs)}", "notas": self.notas}
        if self.M is not None:
            d["diferencial_latex"] = rf"\left({latex(self.M)}\right)dx + \left({latex(self.N)}\right)dy = 0"
        if self.operador is not None:
            d["operador_latex"] = rf"\left({latex(self.operador)}\right)y = {latex(self.rhs)}"
        return d


def _orden(e: sp.Expr) -> int:
    ords = [int(d.derivative_count) for d in e.atoms(sp.Derivative)]
    return max(ords, default=0)


def leer_ed(texto: str, *, latex: bool = False) -> ED:
    """Lee una ecuación diferencial en cualquiera de las notaciones admitidas."""
    original = texto
    if latex:
        texto = desde_latex(texto)
    izq_s, der_s = _partir_igualdad(texto)
    izq, der = _parsear(izq_s), _parsear(der_s)
    expr = sp.expand(izq - der)
    libres = expr.free_symbols
    usa_yd = any(v in libres for v in _YD.values())
    usa_dif = _DIFX in libres or _DIFY in libres

    if usa_dif:
        if usa_yd or D in libres:
            raise ErrorLectura("No mezcles dx, dy con derivadas y' ni con el operador D.")
        M, N = expr.coeff(_DIFX), expr.coeff(_DIFY)
        resto = sp.expand(expr - M * _DIFX - N * _DIFY)
        if resto != 0 or {_DIFX, _DIFY} & (M.free_symbols | N.free_symbols):
            raise ErrorLectura("La forma diferencial debe ser M(x,y)dx + N(x,y)dy = 0 (lineal en dx, dy).")
        lhs = a_funcion(M + N * _YD[1])
        return ED(original, "diferencial", lhs, sp.Integer(0), 1, M=M, N=N)

    if D in libres:
        if usa_yd:
            raise ErrorLectura("No mezcles el operador D con derivadas escritas con apóstrofos.")
        P = expr.coeff(ys)
        g = sp.expand(expr - P * ys)
        if ys in g.free_symbols or D in g.free_symbols:
            raise ErrorLectura("Con el operador D la ecuación debe ser lineal: P(D) y = g(x).")
        P = sp.expand(P)
        poli = sp.Poly(P, D)
        if x in P.free_symbols:
            raise ErrorLectura("Con coeficientes variables no uso la notación D; escribe la ecuación con y', y''.")
        lhs = sum(c * (y(x) if k == 0 else sp.Derivative(y(x), (x, k))) for (k,), c in poli.terms())
        return ED(original, "operador", lhs, -g, poli.degree(), operador=P)

    ex = a_funcion(expr)
    # se vuelve a separar en lhs/rhs tal como se escribió
    return ED(original, "derivada", a_funcion(izq), a_funcion(der), _orden(ex))


def leer_expresion(texto: str, *, latex: bool = False) -> sp.Expr:
    """Expresión en x, y (y como símbolo)."""
    return _parsear(desde_latex(texto) if latex else texto)


def leer_relacion(texto: str, *, latex: bool = False) -> tuple[sp.Expr, sp.Expr]:
    """Lee ``G(x,y)=C`` o ``y=f(x)`` con y como símbolo. Devuelve (lhs, rhs)."""
    if latex:
        texto = desde_latex(texto)
    a, b = _partir_igualdad(texto)
    return _parsear(a), _parsear(b)


@dataclass
class Condicion:
    orden: int       # 0 para y(a)=b, k para y^(k)(a)=c
    x0: sp.Expr
    valor: sp.Expr

    def to_dict(self) -> dict:
        return {"orden": int(self.orden), "x0": str(self.x0), "valor": str(self.valor)}


_RE_COND = re.compile(r"^\s*y\s*(?:('+)|\^\(\s*(\d+)\s*\))?\s*\(\s*(.+?)\s*\)\s*=\s*(.+?)\s*$")


def leer_condiciones(texto: str) -> list[Condicion]:
    """``y(1)=2, y'(0)=-1``: y(a)=b es x=a, y=b; y'(a)=c es y' en x=a igual a c."""
    texto = texto.replace(";", ",")
    trozos, nivel, actual = [], 0, ""
    for ch in texto:
        if ch in "([{":
            nivel += 1
        elif ch in ")]}":
            nivel -= 1
        if ch == "," and nivel == 0:
            trozos.append(actual)
            actual = ""
        else:
            actual += ch
    trozos.append(actual)
    out = []
    for t in (t for t in trozos if t.strip()):
        m = _RE_COND.match(t)
        if not m:
            raise ErrorLectura(f"Condición no válida: «{t.strip()}». Usa y(a)=b o y'(a)=c.")
        orden = len(m.group(1)) if m.group(1) else int(m.group(2) or 0)
        out.append(Condicion(orden, _parsear(m.group(3)), _parsear(m.group(4))))
    return out
