# Propiedades de la Integral Definida

Las integrales definidas satisfacen diversas propiedades algebraicas y analíticas fundamentales que facilitan su manipulación y cálculo sin requerir la evaluación directa de sumas de Riemann.

---

## 1. Reglas de Límites de Integración

- **Inversión de límites de integración:** Intercambiar los límites cambia el signo del resultado:
  $$
  \int_b^a f(x) \, dx = -\int_a^b f(x) \, dx
  $$

- **Límites de integración idénticos:** La integral sobre un intervalo de longitud cero es nula:
  $$
  \int_a^a f(x) \, dx = 0
  $$

---

## 2. Propiedades de Linealidad

Sean $f$ y $g$ funciones integrables en $[a, b]$ y sean $c, k \in \mathbb{R}$ constantes:

- **Integral de una función constante:**
  $$
  \int_a^b c \, dx = c(b - a)
  $$

- **Multiplicación por una constante escalar:**
  $$
  \int_a^b k \cdot f(x) \, dx = k \int_a^b f(x) \, dx
  $$

- **Aditividad de funciones (suma y resta):**
  $$
  \int_a^b \big( f(x) \pm g(x) \big) \, dx = \int_a^b f(x) \, dx \pm \int_a^b g(x) \, dx
  $$

---

## 3. Aditividad de Intervalos

Para cualesquiera tres números $a, b, c$ pertenecientes a un intervalo donde $f$ sea integrable:

$$
\int_a^b f(x) \, dx = \int_a^c f(x) \, dx + \int_c^b f(x) \, dx
$$

Esta propiedad es especialmente útil para integrar funciones definidas a trozos o funciones con valor absoluto.

---

## 4. Propiedades de Comparación y Monotonía

- **No negatividad:** Si $f(x) \ge 0$ para todo $x \in [a, b]$, entonces $\displaystyle \int_a^b f(x) \, dx \ge 0$.
- **Dominancia:** Si $f(x) \ge g(x)$ para todo $x \in [a, b]$, entonces:
  $$
  \int_a^b f(x) \, dx \ge \int_a^b g(x) \, dx
  $$
- **Acotación (Teorema de la Media):** Si $m \le f(x) \le M$ para todo $x \in [a, b]$, entonces:
  $$
  m(b - a) \le \int_a^b f(x) \, dx \le M(b - a)
  $$

---

## 5. Propiedades de Simetría

Para una función integrable en un intervalo simétrico $[-a, a]$:

- Si $f$ es **par** ($f(-x) = f(x)$): $\displaystyle \int_{-a}^a f(x) \, dx = 2\int_0^a f(x) \, dx$
- Si $f$ es **impar** ($f(-x) = -f(x)$): $\displaystyle \int_{-a}^a f(x) \, dx = 0$
