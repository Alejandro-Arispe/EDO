# Discrepancias con el texto del docente

La matemática correcta manda. Cada punto es una prueba en `tests/golden/`. A3 y A5 fueron confirmados con la hoja original y son definitivos. El paso afectado muestra la nota "Discrepancia con el texto del docente".

## Anexo A: errores del texto

| Id | Caso | Respuesta correcta | Qué hizo el texto |
|----|------|--------------------|-------------------|
| A1 | y'=3-2x, y(1)=2 | y=3x-x² | Usó x=2, y=1 y dio C=-1 |
| A2 | (y+3)dx+(4-x)dy=0, y(7)=0 | y=x-7 | Usó x=0, y=7 |
| A3 | Verificar x∫₀ˣ (sen t/t)dt = y ln y | Derivando: x y'(1+ln y) = x sen x + y ln y. La función **no satisface** la ED escrita en el texto (xy' + x ln y = x sen x + y ln y): la verificación de esa ED debe dar "no es solución" y mostrar x y'(1+ln y) = x sen x + y ln y | Perdió y' en ln y |
| A4 | (2xy+3)dy-y²dx=0 | x/y²+1/y³=C | Escribió 3/(4y⁴) |
| A5 | (1+e^(x/y))dx+e^(x/y)(1-x/y)dy=0, y(1)=1 | x+y e^(x/y)=1+e | Escribió ln(x/y) en vez de ln y |
| A6 | y''+4y=3x³ | y=(3/4)x³-(9/8)x+C1 cos2x+C2 sen2x | Escribió 4/3 |
| A7 | Dependencia lineal | Independientes si la suma=0 solo con todas las C=0. x, 2x, x² son dependientes. W=0 no basta para concluir dependencia salvo que sean soluciones de la misma ED lineal. | — |
| A8 | Raíz de multiplicidad m | e^(Dx), x e^(Dx), …, x^(m-1) e^(Dx) | Puso x^m |
| A9 | y''''+y''=sen2x | y=C1+C2x+C3 cosx+C4 senx+sen(2x)/12 | Omitió C3 y C4 |
| A10 | y''-2y'+y=x³+4x | y=C1 eˣ+C2 x eˣ+x³+6x²+22x+32 | Resolvió con -y |
| A11 | y''-4y'+4y=x e^(3x) | yp=(x-2)e^(3x), sin multiplicar por x² porque 3 no es raíz. Y y''-4y'+4y=x e^(2x) → yp=(x³/6)e^(2x). Regla: multiplicar por x^s con s=multiplicidad de la raíz asociada (no "grado de Q ≤ orden"). | Regla errónea |
| A12 | (ax+b)ⁿ y⁽ⁿ⁾ = aⁿ D(D-1)…(D-n+1) con ax+b=eᵗ. (2x+1)²y''-3(2x+1)y'+2y=4(2x+1)³ | 4D²-10D+2; y=C1(2x+1)^((5+√17)/4)+C2(2x+1)^((5-√17)/4)+(2x+1)³/2 | Usó aⁿDⁿ y dio raíces 1/2 y 1 |
| A13 | Clairaut y=xy'+f(y') | General y=cx+f(c); la singular sale de x+f'(p)=0 | Escribió y=c+f(c) |
| A14 | y=2xy'+y'²+1 | x=-2p/3+c/p², y=2c/p-p²/3+1, y además la singular y=1 (p=0), que se pierde al dividir | — |
| A15 | Nombres | y_h (homogénea) y y_p (particular) | El docente llama y_c a la particular |

## Anexo B: casos límite que no deben romperse

| Id | Caso | Comportamiento esperado |
|----|------|-------------------------|
| B1 | Raíces 5±2i dobles y 0 doble | y=e^(5x)[(C1+C2x)cos2x+(C3+C4x)sen2x]+C5+C6x |
| B2 | (D²+5)y=cos(√5 x) | Resonancia, yp=x sen(√5 x)/(2√5) |
| B3 | y⁽⁹⁾-y⁽⁷⁾+273y⁽⁵⁾-820y'''+576y'=0 | Raíces no exactas (≈ ±1.06, ±1.36, ±2.80±2.97i): resolver numéricamente y avisar de posible error de transcripción |
| B4 | 2y''+2y'+y=4√x | Integrales de variación de parámetros probablemente no elementales: dejarlas indicadas con aviso |
| B5 | Ecuación que no encaja en ningún método | Mensaje claro, sin inventar pasos |
