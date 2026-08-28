# Método de Sustitución (u-sub)

El **método de sustitución** (también conocido como sustitución $u$ o cambio de variable) es el equivalente en integración a la **regla de la cadena** en derivación. Permite simplificar una integral compleja transformándola en una integral elemental respecto a una nueva variable $u$.

---

## Teorema y Fórmula General

Si $u = g(x)$ es una función diferenciable cuyo recorrido está contenido en un intervalo donde $f$ es continua, entonces:

$$
\int f(g(x)) \cdot g'(x) \, dx = \int f(u) \, du
$$

El diferencial $du$ está dado por $du = g'(x) \, dx$, lo que permite sustituir tanto la expresión interna como el diferencial $dx$.

---

## Procedimiento Paso a Paso

1. **Elegir $u$:** Identificar una función interna $u = g(x)$ cuya derivada $g'(x)$ aparezca (al menos salvo por una constante multiplicativa) en el integrando.
2. **Calcular el diferencial:** Obtener $du = g'(x) \, dx$ y despejar $dx$ o el bloque correspondiente: $dx = \frac{du}{g'(x)}$.
3. **Reescribir la integral:** Sustituir todas las apariciones de $x$ por expresiones en términos de $u$. La integral resultante debe depender **únicamente** de $u$.
4. **Integrar:** Resolver la integral resultante respecto a la variable $u$.
5. **Revertir la sustitución:** Reemplazar $u$ por su expresión original $g(x)$ para expresar la respuesta en términos de la variable original $x$.

---

## Ejemplos Resueltos

### Ejemplo 1
Evaluar $\displaystyle \int 2x \sqrt{x^2 + 5} \, dx$.

**Solución:**
- Elegimos la función interna del radical: $u = x^2 + 5$.
- Diferenciamos: $du = 2x \, dx \implies 2x \, dx = du$.
- Sustituimos en la integral:
  $$
  \int \sqrt{u} \, du = \int u^{1/2} \, du = \frac{u^{3/2}}{3/2} + C = \frac{2}{3}u^{3/2} + C
  $$
- Revertimos a la variable $x$:
  $$
  \frac{2}{3}(x^2 + 5)^{3/2} + C = \frac{2}{3}\sqrt{(x^2 + 5)^3} + C
  $$

### Ejemplo 2
Evaluar $\displaystyle \int \frac{\ln(x)}{x} \, dx$.

**Solución:**
- Elegimos $u = \ln(x)$.
- Su diferencial es $du = \frac{1}{x} \, dx$.
- Reescribimos e integramos:
  $$
  \int u \, du = \frac{u^2}{2} + C = \frac{1}{2}(\ln(x))^2 + C
  $$
