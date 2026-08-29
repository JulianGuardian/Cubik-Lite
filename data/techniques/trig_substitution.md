# Sustitución Trigonométrica

La **sustitución trigonométrica** es una técnica especializada diseñada para eliminar expresiones con raíces cuadradas que involucran sumas o diferencias de cuadrados: $\sqrt{a^2 - x^2}$, $\sqrt{a^2 + x^2}$ y $\sqrt{x^2 - a^2}$ (con $a > 0$). Se fundamenta en las identidades trigonométricas pitagóricas fundamentales.

---

## Los Tres Casos Clásicos

| Expresión en el Integrando | Sustitución Propuesta | Diferencial $dx$ | Identidad Pitagórica | Simplificación del Radical |
| :--- | :--- | :--- | :--- | :--- |
| $\sqrt{a^2 - x^2}$ | $x = a\sin(\theta)$ | $dx = a\cos(\theta)\,d\theta$ | $1 - \sin^2(\theta) = \cos^2(\theta)$ | $\sqrt{a^2 - x^2} = a\cos(\theta)$ |
| $\sqrt{a^2 + x^2}$ | $x = a\tan(\theta)$ | $dx = a\sec^2(\theta)\,d\theta$ | $1 + \tan^2(\theta) = \sec^2(\theta)$ | $\sqrt{a^2 + x^2} = a\sec(\theta)$ |
| $\sqrt{x^2 - a^2}$ | $x = a\sec(\theta)$ | $dx = a\sec(\theta)\tan(\theta)\,d\theta$ | $\sec^2(\theta) - 1 = \tan^2(\theta)$ | $\sqrt{x^2 - a^2} = a\tan(\theta)$ |

> **Nota:** Se asume el rango principal de cada función trigonométrica inversa para garantizar que las raíces cuadradas sean siempre positivas.

---

## Regreso a la Variable Original

Tras calcular la antiderivada en términos de $\theta$, se construye un **triángulo rectángulo de referencia** donde:
- Se ubica el ángulo $\theta$.
- Se asignan los catetos y la hipotenusa según la relación de sustitución inicial.
- Se leen directamente las razones trigonométricas requeridas en términos de $x$.

---

## Ejemplo Resuelto

Evaluar $\displaystyle \int \frac{1}{x^2 \sqrt{4 - x^2}} \, dx$.

**Solución:**
- Caso $\sqrt{a^2 - x^2}$ con $a = 2$. Hacemos $x = 2\sin(\theta) \implies dx = 2\cos(\theta)\,d\theta$.
- El radical se reduce a $\sqrt{4 - 4\sin^2(\theta)} = 2\cos(\theta)$.
- Sustituyendo en la integral:
  $$
  \int \frac{2\cos(\theta) \, d\theta}{(2\sin(\theta))^2 \cdot 2\cos(\theta)} = \int \frac{1}{4\sin^2(\theta)} \, d\theta = \frac{1}{4} \int \csc^2(\theta) \, d\theta = -\frac{1}{4}\cot(\theta) + C
  $$
- Con el triángulo rectángulo donde $\sin(\theta) = \frac{x}{2}$:
  - Cateto opuesto $= x$, Hipotenusa $= 2$, Cateto adyacente $= \sqrt{4 - x^2}$.
  - Por tanto, $\cot(\theta) = \frac{\text{adyacente}}{\text{opuesto}} = \frac{\sqrt{4 - x^2}}{x}$.
- Conclusión:
  $$
  \int \frac{1}{x^2 \sqrt{4 - x^2}} \, dx = -\frac{\sqrt{4 - x^2}}{4x} + C
  $$
