# Área bajo una Curva

El cálculo del área delimitada por la gráfica de una función representa la motivación geométrica primordial para la formulación de la integral definida a través del límite de las **sumas de Riemann**.

---

## Fundamento Teórico y Definición

Sea $f(x)$ una función continua y no negativa ($f(x) \ge 0$) en el intervalo cerrado $[a, b]$. El área $A$ de la región acotada superiormente por la curva $y = f(x)$, inferiormente por el eje $x$, y lateralmente por las rectas verticales $x = a$ y $x = b$, está dada exactamente por:

$$
A = \int_a^b f(x) \, dx = \lim_{n \to \infty} \sum_{i=1}^n f(x_i^*) \, \Delta x
$$

donde $\Delta x = \frac{b - a}{n}$ y $x_i^*$ es un punto muestra en el $i$-ésimo subintervalo.

---

## Área Neta con Signo vs. Área Total Geométrica

- **Integral definida (Área neta con signo):** La integral asigna valores positivos a las regiones situadas por encima del eje $x$ y valores negativos a las que se encuentran por debajo:
  $$
  \int_a^b f(x) \, dx = A_{\text{superior}} - A_{\text{inferior}}
  $$

- **Área geométrica total:** Para calcular el área física total real encerrada, se debe integrar el valor absoluto de la función:
  $$
  A_{\text{total}} = \int_a^b \vert f(x)\vert \, dx
  $$
  Esto requiere subdividir el intervalo en los puntos donde $f(x) = 0$ e integrar cada sección por separado con el signo adecuado.

---

## Ejemplo Resuelto

Calcular el área de la región comprendida entre la curva $f(x) = 4 - x^2$ y el eje $x$ en el intervalo $[-2, 2]$.

**Solución:**
- Dado que $f(x) = 4 - x^2 \ge 0$ para todo $x \in [-2, 2]$ (los puntos de corte con el eje $x$ son $x = \pm 2$), el área geométrica coincide con la integral definida directa:
  $$
  A = \int_{-2}^2 (4 - x^2) \, dx
  $$
- Como $f(x)$ es una función par, podemos aplicar la propiedad de simetría:
  $$
  A = 2 \int_0^2 (4 - x^2) \, dx = 2 \left[ 4x - \frac{x^3}{3} \right]_0^2
  $$
- Evaluando en los límites:
  $$
  A = 2 \left( 4(2) - \frac{2^3}{3} \right) = 2 \left( 8 - \frac{8}{3} \right) = 2 \left( \frac{16}{3} \right) = \frac{32}{3} \approx 10.67 \text{ unidades cuadradas}
  $$
