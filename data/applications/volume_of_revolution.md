# Volumen de Revolución

Un **sólido de revolución** es un cuerpo tridimensional generado al girar una región plana bidimensional alrededor de un eje coplanar fijo denominado eje de rotación o eje de revolución.

---

## 1. Método de Discos y Arandelas (Cortes Perpendiculares al Eje)

Este método se aplica cuando la rebanada o elemento diferencial de volumen es perpendicular al eje de giro.

- **Método de Discos (Sólido sin hueco):**
  Al rotar alrededor del eje $x$ la región acotada por $y = R(x)$ en $[a, b]$:
  $$
  V = \pi \int_a^b [R(x)]^2 \, dx
  $$

- **Método de Arandelas (Sólido con hueco):**
  Al rotar entre un radio exterior $R(x)$ y un radio interior $r(x)$:
  $$
  V = \pi \int_a^b \Big( [R(x)]^2 - [r(x)]^2 \Big) \, dx
  $$

---

## 2. Método de Cascarones Cilíndricos (Cortes Paralelos al Eje)

Este método se emplea cuando el rectángulo diferencial es paralelo al eje de giro, evitando despejar variables complejas:

- **Rotación alrededor del eje $y$ (o recta vertical $x = k$):**
  $$
  V = 2\pi \int_a^b (\text{radio})(\text{altura}) \, dx = 2\pi \int_a^b x \cdot f(x) \, dx
  $$

- **Rotación alrededor del eje $x$ (o recta horizontal $y = k$):**
  $$
  V = 2\pi \int_c^d y \cdot g(y) \, dy
  $$

---

## ¿Cuándo Usar Cada Método?

| Criterio | Método de Discos / Arandelas | Método de Cascarones Cilíndricos |
| :--- | :--- | :--- |
| **Orientación del rectángulo** | Perpendicular ($\perp$) al eje de giro | Paralelo ($\parallel$) al eje de giro |
| **Eje de rotación horizontal ($y = 0$)** | Integrar respecto a $x$ ($dx$) | Integrar respecto a $y$ ($dy$) |
| **Eje de rotación vertical ($x = 0$)** | Integrar respecto a $y$ ($dy$) | Integrar respecto a $x$ ($dx$) |

---

## Ejemplo Resuelto (Método de Discos)

Calcular el volumen del sólido generado al girar la región acotada por $y = \sqrt{x}$, el eje $x$ y la recta $x = 4$, alrededor del eje $x$.

**Solución:**
- El radio del disco en cualquier punto $x$ es $R(x) = \sqrt{x}$.
- Los límites de integración sobre el eje $x$ son $a = 0$ y $b = 4$.
- Aplicando la fórmula de discos:
  $$
  V = \pi \int_0^4 (\sqrt{x})^2 \, dx = \pi \int_0^4 x \, dx = \pi \left[ \frac{x^2}{2} \right]_0^4
  $$
- Evaluando los límites:
  $$
  V = \pi \left( \frac{4^2}{2} - 0 \right) = \pi \left( \frac{16}{2} \right) = 8\pi \approx 25.132 \text{ unidades cúbicas}
  $$
