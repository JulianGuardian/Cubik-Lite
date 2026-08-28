# Teorema Fundamental del Cálculo

El **Teorema Fundamental del Cálculo (TFC)** establece la conexión profunda e intrínseca entre las dos ramas principales del análisis matemático: el cálculo diferencial y el cálculo integral. Muestra que la integración y la derivación son procesos inversos.

---

## Teorema Fundamental del Cálculo - Parte 1 (TFC 1)

### Enunciado
Si $f$ es una función continua en el intervalo cerrado $[a, b]$, entonces la función acumulación $g$ definida por:

$$
g(x) = \int_a^x f(t) \, dt \quad \text{para } x \in [a, b]
$$

es continua en $[a, b]$, derivable en $(a, b)$, y su derivada es:

$$
g'(x) = \frac{d}{dx} \left[ \int_a^x f(t) \, dt \right] = f(x)
$$

### Generalización con la Regla de la Cadena
Si el límite superior es una función diferenciable $u(x)$:

$$
\frac{d}{dx} \left[ \int_a^{u(x)} f(t) \, dt \right] = f(u(x)) \cdot u'(x)
$$

### Ejemplo 1
Calcular $\frac{d}{dx} \int_2^{x^3} \cos(t^2) \, dt$.

**Solución:** Haciendo $u(x) = x^3$, $u'(x) = 3x^2$:
$$
\frac{d}{dx} \int_2^{x^3} \cos(t^2) \, dt = \cos\big((x^3)^2\big) \cdot \frac{d}{dx}(x^3) = 3x^2 \cos(x^6)
$$

---

## Teorema Fundamental del Cálculo - Parte 2 (TFC 2)

### Enunciado
Si $f$ es continua en $[a, b]$ y $F$ es cualquier antiderivada de $f$ en dicho intervalo (es decir, $F'(x) = f(x)$), entonces:

$$
\int_a^b f(x) \, dx = F(b) - F(a) = \Big[ F(x) \Big]_a^b
$$

### Significado
Permite evaluar integrales definidas algebraicamente utilizando antiderivadas, sin necesidad de calcular límites de sumas de Riemann.

### Ejemplo 2
Evaluar $\displaystyle \int_1^3 (3x^2 - 2x + 4) \, dx$.

**Solución:** Hallamos una antiderivada $F(x) = x^3 - x^2 + 4x$:
$$
\int_1^3 (3x^2 - 2x + 4) \, dx = \Big[ x^3 - x^2 + 4x \Big]_1^3
$$
$$
= \left( 3^3 - 3^2 + 4(3) \right) - \left( 1^3 - 1^2 + 4(1) \right) = (27 - 9 + 12) - (1 - 1 + 4) = 30 - 4 = 26
$$
