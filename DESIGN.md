---
name: Teams Facultad MCP
description: Identidad editorial de un MCP local para compañeros de facultad.
colors:
  ink: "#173C3A"
  terracotta: "#C45132"
  paper: "#F4F0E7"
typography:
  display:
    fontFamily: "Libre Baskerville"
    fontSize: "89px"
    fontWeight: 400
  body:
    fontFamily: "DM Sans"
    fontSize: "28px"
    fontWeight: 500
  title:
    fontFamily: "DM Sans"
    fontSize: "33px"
    fontWeight: 500
rounded:
  mark: "24px"
spacing:
  banner-inset: "68px"
  mark-inset: "24px"
components:
  brand-banner:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    width: "1440px"
    height: "520px"
  brand-mark:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.mark}"
    width: "180px"
    height: "180px"
  social-preview:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    width: "1200px"
    height: "630px"
---

# Design System: Teams Facultad MCP

## Overview

**Creative North Star: "El boletín universitario"**

El boletín universitario organiza una identidad cercana para compañeros de facultad: papel cálido, tinta verde oscura y un pequeño acento terracota. Una serif editorial convive con una sans clara; la espina y las pestañas del símbolo conectan las tres piezas de marca.

El sistema describe los assets estáticos del repositorio. El README conserva los títulos, enlaces, tablas, citas y bloques de código de Markdown nativo de GitHub; estos tokens no sustituyen su tipografía ni sus colores, incluido el modo oscuro. No hay una interfaz de aplicación de marca ni controles interactivos propios.

**Key Characteristics:**
- Papel cálido y tinta de alto contraste.
- Titular serif y wordmark sans en trazados autónomos.
- Espina continua con pestañas como firma geométrica.
- Assets planos; instrucciones esenciales en Markdown vivo.

## Colors

Una paleta de papel cálido y tinta verde, con un acento terracota concentrado en el símbolo.

### Primary

- **Tinta verde:** titulares, wordmark, textos y estructura principal del símbolo sobre papel.

### Secondary

- **Terracota:** una pestaña del símbolo y el acento del badge de licencia del README.

### Neutral

- **Papel cálido:** fondo de las tres piezas de marca. No redefine el fondo de GitHub.

**The Tinta sobre papel Rule.** Los assets usan papel como fondo y tinta como contenido principal; terracota señala una única pestaña del símbolo.

## Typography

**Display Font:** Libre Baskerville.
**Body Font:** DM Sans.

**Character:** una serif de publicación académica aporta voz al titular; la sans sostiene el nombre y la explicación breve. Las familias se usaron para construir los trazados, por lo que los SVG publicados no descargan ni cargan fuentes. Las licencias SIL OFL 1.1 están en `assets/branding/`.

### Hierarchy

- **Display:** titular de dos líneas del banner; tamaño y peso de referencia en `typography.display`.
- **Title:** wordmark «Teams Facultad MCP» del banner; referencia en `typography.title`.
- **Body:** explicación breve del banner; referencia en `typography.body`.

Los tamaños de frontmatter corresponden al lienzo original del banner. No constituyen una escala CSS adaptable ni especifican la tipografía del README. La vista social es una composición independiente a partir de las mismas familias; no se deduce una escala universal de sus trazados. No se registra interlineado CSS porque el texto está posicionado como geometría vectorial.

**The Dos soportes Rule.** La tipografía de marca pertenece a las imágenes; la columna de lectura conserva el estilo nativo de GitHub.

## Layout

El banner tiene un lienzo horizontal: titular a la izquierda y símbolo a la derecha, con una regla horizontal de tinta (2px) en `y=326`. El margen lateral es `spacing.banner-inset`. Debajo de la regla quedan el wordmark, la explicación y la frase breve «Local. Personal. Abierto.».

El README inserta el banner al ancho disponible (`width="100%"`), conservando su proporción. No hay puntos de quiebre propios: en móvil se reduce toda la imagen. La letra secundaria resulta pequeña a ese tamaño; el título y el párrafo vivo del README repiten la información necesaria. Se verificó la lectura en capturas locales de 1280px y 390px; esas capturas de revisión no se distribuyen.

El símbolo cuadrado mantiene un margen interior `spacing.mark-inset`. La vista social usa su propio lienzo de paisaje; no es un recorte del banner. La columna, las tablas, los enlaces y los bloques de código dependen del renderizado nativo de GitHub.

## Elevation & Depth

Las piezas de marca son planas: sin sombras, degradados, texturas ni efectos de iluminación. El contraste entre el papel, la tinta y la pestaña terracota separa las formas. No se extraen tokens de elevación de los bordes o fondos que GitHub aplica al Markdown.

## Shapes

Una F geométrica enlaza la espina vertical y las pestañas de materias. Sus trazos son rectos y compactos; la pestaña terracota queda separada de la espina. El contenedor cuadrado del símbolo tiene las esquinas redondeadas de `rounded.mark`; los lienzos del banner y de la vista social son rectangulares.

Las versiones del símbolo conservan la espina y sus pestañas como una misma construcción geométrica.

## Components

### Banner de marca

Cabecera editorial estática (`assets/branding/banner.svg`). Une titular, símbolo, regla y texto de apoyo. Sus dimensiones naturales están en `components.brand-banner`. Incluye título y descripción accesibles en el SVG; el README además define texto alternativo. No tiene estados ni animación.

### Símbolo

Identificador compacto (`assets/branding/mark.svg`). El fondo de papel redondeado contiene la construcción de espina y pestañas en tinta y terracota. Sus dimensiones naturales están en `components.brand-mark`. Comparte exactamente la geometría interior con las otras piezas, donde se aplica una escala uniforme.

### Vista social

Composición para compartir (`assets/branding/social-preview.svg`). Reutiliza las formas y la voz tipográfica, con disposición propia para su lienzo. Sus dimensiones naturales están en `components.social-preview`.

Los PNG correspondientes son conversiones de los mismos vectores. No existen botones, campos, tarjetas, navegación ni estados interactivos propios que documentar. Los badges y enlaces del README mantienen el comportamiento del servicio que los renderiza y de GitHub.

## Do's and Don'ts

### Do:

- **Do** conservar los SVG autónomos con texto convertido a trazados.
- **Do** escalar el banner completo, manteniendo su proporción y sin recortarlo.
- **Do** repetir el sentido del banner en el título y el texto vivo del README.
- **Do** conservar los avisos SIL OFL de las dos familias al redistribuir los assets.

### Don't:

- **Don't** presentar estos tokens como estilos que controlan el Markdown de GitHub.
- **Don't** usar el texto pequeño del banner como único lugar para una instrucción esencial.
- **Don't** presentar esta identidad independiente como una marca oficial de Microsoft o de una universidad.
