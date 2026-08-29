# Reglas Básicas de Integración

La integración indefinida es la operación inversa de la derivación. Dada una función continua $f(x)$, su integral indefinida representa la familia de todas sus antiderivadas y se denota mediante el símbolo:

$$
\int f(x) \, dx = F(x) + C
$$

donde $F'(x) = f(x)$ y $C$ es la **constante de integración arbitraria**.

---

## 1. Reglas de Linealidad

El operador de integración es un operador lineal, lo que permite descomponer integrales complejas:

- **Regla del factor constante:** Una constante que multiplica al integrando puede salir fuera de la integral:
  $$
  \int c \cdot f(x) \, dx = c \int f(x) \, dx \quad (c \in \mathbb{R})
  $$

- **Regla de la suma y diferencia:** La integral de una suma o resta de funciones es la suma o resta de sus integrales:
  $$
  \int \big( f(x) \pm g(x) \big) \, dx = \int f(x) \, dx \pm \int g(x) \, dx
  $$

---

## 2. Regla de Potencias

Para cualquier número real $n \neq -1$:

$$
\int x^n \, dx = \frac{x^{n+1}}{n+1} + C \quad (n \neq -1)
$$

Cuando el exponente es $n = -1$, la integral corresponde al logaritmo natural:

$$
\int \frac{1}{x} \, dx = \ln|x| + C
$$

---

## 3. Reglas Exponenciales

- Para la base natural $e$:
  $$
  \int e^x \, dx = e^x + C
  $$
- Para una base general $a > 0$ con $a \neq 1$:
  $$
  \int a^x \, dx = \frac{a^x}{\ln(a)} + C
  $$

---

## 4. Integrales Trigonométricas Elementales

Derivadas a partir de las funciones trigonométricas estándar:

- $\displaystyle \int \sin(x) \, dx = -\cos(x) + C$
- $\displaystyle \int \cos(x) \, dx = \sin(x) + C$
- $\displaystyle \int \sec^2(x) \, dx = \tan(x) + C$
- $\displaystyle \int \csc^2(x) \, dx = -\cot(x) + C$

---

## Ejemplos Resueltos

### Ejemplo 1
Evaluar $\displaystyle \int (5x^3 - 4e^x + \sec^2(x)) \, dx$.

**Solución:** Aplicando las propiedades de linealidad y las reglas básicas:
$$
\int (5x^3 - 4e^x + \sec^2(x)) \, dx = 5\int x^3 \, dx - 4\int e^x \, dx + \int \sec^2(x) \, dx
$$
$$
= 5\left(\frac{x^4}{4}\right) - 4e^x + \tan(x) + C = \frac{5}{4}x^4 - 4e^x + \tan(x) + C
$$

### Ejemplo 2
Evaluar $\displaystyle \int \frac{3x^2 + 2\sqrt{x}}{x} \, dx$.

**Solución:** Simplificando algebraicamente antes de integrar:
$$
\int \left( 3x + 2x^{-1/2} \right) dx = 3\left(\frac{x^2}{2}\right) + 2\left(\frac{x^{1/2}}{1/2}\right) + C = \frac{3}{2}x^2 + 4\sqrt{x} + C
$$
