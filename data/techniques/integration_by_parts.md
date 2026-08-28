# Integración por Partes

El método de **integración por partes** es la contraparte de la **regla del producto** para derivadas. Se utiliza principalmente cuando el integrando consiste en el producto de dos funciones de distinta naturaleza (por ejemplo, algebraicas con exponenciales o trigonométricas con logarítmicas).

---

## Deducción y Fórmula General

A partir de la regla del producto $\frac{d}{dx}[u(x)v(x)] = u'(x)v(x) + u(x)v'(x)$, integrando ambos miembros y reorganizando términos, se obtiene la fórmula fundamental:

$$
\int u \, dv = u v - \int v \, du
$$

---

## Criterio de Selección: Regla LIATE

Para elegir convenientemente la función $u$ (priorizando aquellas que se simplifican al derivarse), se emplea la regla mnemotécnica **LIATE**:

1. **L** - **Logarítmicas:** $\ln(x),\, \log_a(x)$
2. **I** - **Inversas trigonométricas:** $\arcsin(x),\, \arctan(x)$
3. **A** - **Algebraicas:** $x^n,\, 3x^2 + 1,\, \sqrt{x}$
4. **T** - **Trigonométricas:** $\sin(x),\, \cos(x),\, \sec(x)$
5. **E** - **Exponenciales:** $e^x,\, 2^x$

> **Regla práctica:** La función que aparezca primero en la lista LIATE se asigna como $u$. El resto del integrando junto con $dx$ conforma $dv$.

---

## Procedimiento Paso a Paso

1. Asignar $u$ siguiendo el orden de LIATE y definir $dv$ con el resto del integrando.
2. Calcular $du$ mediante diferenciación ($du = u' \, dx$).
3. Calcular $v$ mediante integración ($v = \int dv$).
4. Aplicar la fórmula: $\int u \, dv = u v - \int v \, du$.
5. Resolver la integral residual $\int v \, du$.

---

## Ejemplos Resueltos

### Ejemplo 1
Evaluar $\displaystyle \int x e^x \, dx$.

**Solución:**
- $u = x$ (Algebraica antes de Exponencial) $\implies du = dx$
- $dv = e^x \, dx \implies v = \int e^x \, dx = e^x$
- Aplicando la fórmula:
  $$
  \int x e^x \, dx = x e^x - \int e^x \, dx = x e^x - e^x + C = e^x(x - 1) + C
  $$

### Ejemplo 2
Evaluar $\displaystyle \int \ln(x) \, dx$.

**Solución:**
- $u = \ln(x)$ (Logarítmica) $\implies du = \frac{1}{x} \, dx$
- $dv = dx \implies v = x$
- Aplicando la fórmula:
  $$
  \int \ln(x) \, dx = x\ln(x) - \int x \left(\frac{1}{x}\right) dx = x\ln(x) - \int 1 \, dx = x\ln(x) - x + C
  $$
