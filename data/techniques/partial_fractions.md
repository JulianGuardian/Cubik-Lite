# Fracciones Parciales

El método de **descomposición en fracciones parciales** se utiliza para integrar funciones racionales de la forma:

$$
f(x) = \frac{P(x)}{Q(x)}
$$

donde $P(x)$ y $Q(x)$ son polinomios con coeficientes reales.

---

## Requisitos Previos

1. **Fracción Propia:** El grado del numerador debe ser estrictamente menor que el del denominador: $\text{gr}(P) < \text{gr}(Q)$. Si $\text{gr}(P) \ge \text{gr}(Q)$, primero se debe realizar **división polinómica larga**:
   $$
   \frac{P(x)}{Q(x)} = C(x) + \frac{R(x)}{Q(x)} \quad \text{donde } \text{gr}(R) < \text{gr}(Q)
   $$
2. **Factorización:** Factorizar completamente el denominador $Q(x)$ en factores lineales y factores cuadráticos irreducibles sobre los reales.

---

## Casos de Descomposición

1. **Factores lineales distintos $(ax + b)$:**
   $$
   \frac{A}{ax + b}
   $$
2. **Factores lineales repetidos $(ax + b)^k$:**
   $$
   \frac{A_1}{ax + b} + \frac{A_2}{(ax + b)^2} + \dots + \frac{A_k}{(ax + b)^k}
   $$
3. **Factores cuadráticos irreducibles distintos $(ax^2 + bx + c)$ con $b^2 - 4ac < 0$:**
   $$
   \frac{Ax + B}{ax^2 + bx + c}
   $$
4. **Factores cuadráticos repetidos $(ax^2 + bx + c)^k$:**
   $$
   \sum_{j=1}^k \frac{A_j x + B_j}{(ax^2 + bx + c)^j}
   $$

---

## Ejemplo Resuelto

Evaluar $\displaystyle \int \frac{5x - 3}{x^2 - 2x - 3} \, dx$.

**Paso 1: Factorizar el denominador:**
$$
x^2 - 2x - 3 = (x - 3)(x + 1)
$$

**Paso 2: Plantear la descomposición en fracciones parciales:**
$$
\frac{5x - 3}{(x - 3)(x + 1)} = \frac{A}{x - 3} + \frac{B}{x + 1}
$$

Multiplicando por el denominador común:
$$
5x - 3 = A(x + 1) + B(x - 3)
$$

**Paso 3: Determinar los coeficientes:**
- Si $x = 3 \implies 5(3) - 3 = A(4) + 0 \implies 12 = 4A \implies A = 3$
- Si $x = -1 \implies 5(-1) - 3 = 0 + B(-4) \implies -8 = -4B \implies B = 2$

**Paso 4: Integrar cada término:**
$$
\int \frac{5x - 3}{x^2 - 2x - 3} \, dx = \int \left( \frac{3}{x - 3} + \frac{2}{x + 1} \right) dx = 3\ln\vert x - 3\vert + 2\ln\vert x + 1\vert + C
$$
