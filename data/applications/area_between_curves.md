# Área entre Curvas

El cálculo del área comprendida entre dos curvas en el plano cartesiano generaliza el concepto de área bajo una curva, determinando la magnitud de la región delimitada por las funciones en un intervalo dado.

---

## 1. Integración Respecto al Eje $x$ (Rectángulos Verticales)

Si $f(x)$ y $g(x)$ son funciones continuas en $[a, b]$ y se verifica que $f(x) \ge g(x)$ para todo $x \in [a, b]$, el área $A$ de la región acotada entre ambas curvas es:

$$
A = \int_a^b \Big( f(x) - g(x) \Big) \, dx = \int_a^b \Big( y_{\text{superior}} - y_{\text{inferior}} \Big) \, dx
$$

### Determinación de Curvas Superior e Inferior
1. **Puntos de Intersección:** Resolver la ecuación $f(x) = g(x)$ para encontrar los límites de integración $a$ y $b$.
2. **Punto de Prueba:** Evaluar un valor $x_0 \in (a, b)$ en ambas funciones; aquella con mayor valor numérico corresponderá a la curva superior $f(x)$.

---

## 2. Integración Respecto al Eje $y$ (Rectángulos Horizontales)

Cuando las fronteras se describen más fácilmente en función de $y$, es decir $x = f(y)$ y $x = g(y)$ con $f(y) \ge g(y)$ en $[c, d]$:

$$
A = \int_c^d \Big( f(y) - g(y) \Big) \, dy = \int_c^d \Big( x_{\text{derecha}} - x_{\text{izquierda}} \Big) \, dy
$$

---

## Ejemplo Resuelto

Calcular el área de la región acotada entre las parábolas $y = 2x - x^2$ e $y = x^2$.

**Paso 1: Determinar los puntos de intersección:**
$$
2x - x^2 = x^2 \implies 2x^2 - 2x = 0 \implies 2x(x - 1) = 0 \implies x = 0, \quad x = 1
$$
Los límites de integración son $a = 0$ y $b = 1$.

**Paso 2: Identificar la curva superior:**
Probando con $x = 0.5$:
- $y_1 = 2(0.5) - (0.5)^2 = 1 - 0.25 = 0.75$
- $y_2 = (0.5)^2 = 0.25$
Como $y_1 > y_2$, la curva superior es $f(x) = 2x - x^2$ y la inferior es $g(x) = x^2$.

**Paso 3: Plantear y resolver la integral:**
$$
A = \int_0^1 \Big( (2x - x^2) - x^2 \Big) \, dx = \int_0^1 (2x - 2x^2) \, dx
$$
$$
A = \left[ x^2 - \frac{2}{3}x^3 \right]_0^1 = \left( 1 - \frac{2}{3} \right) - 0 = \frac{1}{3} \approx 0.333 \text{ unidades cuadradas}
$$
