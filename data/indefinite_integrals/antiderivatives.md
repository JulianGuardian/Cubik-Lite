# Tabla de Antiderivadas Comunes

Una **antiderivada** o primitiva de una función $f(x)$ es cualquier función $F(x)$ tal que $F'(x) = f(x)$ en un intervalo dado. Si $F(x)$ es una antiderivada de $f(x)$, la antiderivada más general es $F(x) + C$, donde $C \in \mathbb{R}$ es la constante de integración.

A continuación se presenta la tabla fundamental de antiderivadas estándar que todo estudiante de cálculo debe dominar.

---

## Tabla Fundamental de Integrales

| # | Función Integrando $f(x)$ | Integral Indefinida $\int f(x) \, dx$ | Restricciones / Dominio |
| :-: | :--- | :--- | :--- |
| **1** | $k$ (constante) | $kx + C$ | $k \in \mathbb{R}$ |
| **2** | $x^n$ | $\displaystyle \frac{x^{n+1}}{n+1} + C$ | $n \neq -1$ |
| **3** | $\displaystyle \frac{1}{x}$ | $\ln\vert x\vert + C$ | $x \neq 0$ |
| **4** | $e^x$ | $e^x + C$ | $\forall x \in \mathbb{R}$ |
| **5** | $a^x$ | $\displaystyle \frac{a^x}{\ln(a)} + C$ | $a > 0,\, a \neq 1$ |
| **6** | $\sin(x)$ | $-\cos(x) + C$ | $\forall x \in \mathbb{R}$ |
| **7** | $\cos(x)$ | $\sin(x) + C$ | $\forall x \in \mathbb{R}$ |
| **8** | $\sec^2(x)$ | $\tan(x) + C$ | $x \neq \frac{\pi}{2} + k\pi$ |
| **9** | $\csc^2(x)$ | $-\cot(x) + C$ | $x \neq k\pi$ |
| **10** | $\sec(x)\tan(x)$ | $\sec(x) + C$ | $x \neq \frac{\pi}{2} + k\pi$ |
| **11** | $\csc(x)\cot(x)$ | $-\csc(x) + C$ | $x \neq k\pi$ |
| **12** | $\tan(x)$ | $\ln\vert\sec(x)\vert + C = -\ln\vert\cos(x)\vert + C$ | $x \neq \frac{\pi}{2} + k\pi$ |
| **13** | $\cot(x)$ | $\ln\vert\sin(x)\vert + C$ | $x \neq k\pi$ |
| **14** | $\sec(x)$ | $\ln\vert\sec(x) + \tan(x)\vert + C$ | $x \neq \frac{\pi}{2} + k\pi$ |
| **15** | $\csc(x)$ | $\ln\vert\csc(x) - \cot(x)\vert + C$ | $x \neq k\pi$ |
| **16** | $\displaystyle \frac{1}{\sqrt{1 - x^2}}$ | $\arcsin(x) + C$ | $\vert x\vert < 1$ |
| **17** | $\displaystyle \frac{1}{1 + x^2}$ | $\arctan(x) + C$ | $\forall x \in \mathbb{R}$ |
| **18** | $\displaystyle \frac{1}{\vert x\vert\sqrt{x^2 - 1}}$ | $\text{arcsec}(x) + C$ | $\vert x\vert > 1$ |
| **19** | $\sinh(x)$ | $\cosh(x) + C$ | $\forall x \in \mathbb{R}$ |
| **20** | $\cosh(x)$ | $\sinh(x) + C$ | $\forall x \in \mathbb{R}$ |

---

## Verificación por Diferenciación

Para corroborar la validez de cualquier antiderivada calculada, se aplica el proceso de derivación:

$$
\frac{d}{dx} \left( \int f(x) \, dx \right) = \frac{d}{dx} \big( F(x) + C \big) = F'(x) + 0 = f(x)
$$

Si al derivar el resultado obtenido no se recupera exactamente la función integrando original $f(x)$, la antiderivada calculada contiene un error.
