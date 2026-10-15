# Diseño del panel: el prototipo aprobado

> **Qué es esta carpeta:** las fuentes del prototipo del panel que aprobó el equipo el 2026-10-14. Es la **referencia de diseño** para cualquier pantalla del panel: estructura, textos, colores, espaciados y comportamiento.
> **Por qué está en el repositorio:** el prototipo vive en un artifact privado de Claude, y en T12 el chat de tarea no pudo verlo: el primer diseño salió lejos de lo acordado y hubo que rehacerlo (DEC-158). Desde entonces, el diseño se lee aquí.

## 1. Los archivos

| Archivo | Pantalla | Estado |
|---|---|---|
| [dashboard-comunidad.dc.html](dashboard-comunidad.dc.html) | Dashboard · Comunidad (para el CM) | ✅ Hecho en T12 (`panel/paginas/dashboard.py`) |
| [dashboard-contenido.dc.html](dashboard-contenido.dc.html) | Dashboard · Contenido (para Marketing) | ✅ Hecho en T12 |
| [borradores.dc.html](borradores.dc.html) | Borradores: una tarjeta por logro | ✅ Hecho en T13 (`panel/paginas/borradores.py`), con los cambios de DEC-159 que dice la sección 2 |

Son páginas "Design Component": HTML con estilos en línea y un bloque `<script type="text/x-dc">` al final, con los datos y el comportamiento (`renderVals()`). **No se abren en el navegador tal cual** (necesitan el motor del editor): se leen como referencia. Los `{{…}}` son valores que salen del script. Los enlaces entre pantallas usan los nombres viejos (`Main.dc.html`, `DashMarketing.dc.html`, `Borradores.dc.html`).

Los nombres de alumnos de los ejemplos son inventados. En las pantallas del dashboard, los números son los reales de la base local del 2026-10-14; en Borradores, son de ejemplo.

## 2. La pantalla de Borradores (para T13)

**Quién la usa:** Marketing. **Para qué:** revisar rápido y seguro lo que propuso la IA, y saber dónde se publica cada texto.

| Zona | Qué tiene | Por qué |
|---|---|---|
| Barra lateral | La misma de las otras páginas: "CommunityLab · Panel de curaduría" (el título del panel va aquí, no arriba de cada página), la navegación con el número de pendientes, el recuadro de estado de los datos y la sesión | Igual en todas las páginas |
| Encabezado | Título "Borradores" y la frase "Cada logro trae dos textos: un post para LinkedIn y un caso de éxito para la web. Se revisan juntos." | Explica el modelo mental: un logro, dos destinos |
| Filtro de estado | Píldoras **Por revisar (n)** · Aprobados · Rechazados | Como los atajos de período del dashboard |
| Cola (izquierda) | Una **tarjeta por logro**, del más antiguo al más nuevo: el primer nombre del alumno, un resumen ("Consiguió su primer trabajo…"), hace cuánto, y una etiqueta "Post + caso de éxito". La FAQ semanal es otra tarjeta, con "FAQ · sin consentimiento". La elegida se marca con un borde más grueso | Reconocer en vez de recordar: hoy se elige en una lista desplegable con "#12 · POST_LINKEDIN" |
| Detalle (derecha) | "Logro de Ana" con una etiqueta del tipo de logro ("Contratación"), el canal y la fecha; dos recuadros: **Mensaje original** y **Por qué la IA lo propuso** | El contexto para decidir |
| Pestañas | **Post de LinkedIn** · **Caso de éxito**. Debajo de cada una, **"Dónde se publica"**: el LinkedIn de CommunityLab, o la web y las presentaciones a empresas | El caso de éxito no se publica en LinkedIn (el brief los pide como dos componentes) |
| Texto | Un área de texto editable, con un contador debajo: "N palabras (la guía pide 90 a 160) · N de 3.000 caracteres de LinkedIn" en el post, y "N palabras (la guía pide 150 a 250) · sin emojis ni hashtags" en el caso. Botón **Copiar texto** | Las reglas de la guía de voz, a la vista |
| Consentimiento | **Una sola casilla para los dos textos:** "Ana dio su consentimiento para publicar su nombre y su historia. **Vale para los dos textos.**" **Cambió en T13:** va **arriba de las pestañas**, porque los botones están dentro de cada pestaña y la casilla vale para las dos. Si el post ya se aprobó con consentimiento, viene marcada para el caso de éxito | 🧪 Hoy se aprueba el caso de éxito en 5 s (mediana) después del post: se revisan juntos |
| Acciones | **Cambió en T13 (DEC-159): botones por texto.** En cada pestaña, **Aprobar** ("Aprobar post" o "Aprobar caso de éxito", apagado hasta marcar la casilla, con el aviso "Para aprobar, marca la casilla de consentimiento"), **Guardar edición** y **Rechazar…**, solo para ese texto. **El botón del post dice antes qué pasará en LinkedIn:** apagado o simulado, "Aprobar post" con una nota; encendido, **"Aprobar y publicar en LinkedIn"**, que pide confirmar. Un post de más de 3.000 caracteres no se deja aprobar | Prevenir el error (D6). Aprobar el post puede publicarlo en LinkedIn y el caso de éxito no: por eso se separan |
| Después de aprobar | **Cambió en T13:** un aviso verde por texto ("Post aprobado. Falta revisar el caso de éxito."); la tarjeta sigue en la cola, con la pestaña del caso abierta. Cuando no queda nada: "Aprobados los dos textos de Ana", con el enlace "Verlos en Listos para publicar", que abre el dashboard en la pestaña Contenido | Dar retroalimentación y el siguiente paso |
| Estado en LinkedIn (M12) | ✅ T13 (`V9`, DEC-160, reemplaza a DEC-151): en el post aprobado, "Publicado en LinkedIn el …" con **Ver en LinkedIn**, "No publicado: la publicación en LinkedIn está apagada", "Simulado…", "Falló: <motivo>" o "Sin dato" | La columna "En LinkedIn" del dashboard también lo usa |

El prototipo de Borradores es anterior al tema oscuro: tiene los colores del tema claro escritos a mano. **No copiar esos colores**: usar los de T12 (sección 3).

## 3. Reutilizar lo de T12 (obligatorio)

Para que todo el panel se vea igual, Borradores usa las piezas que T12 dejó en `panel/paginas/dashboard.py`. Conviene **moverlas a un módulo común** (por ejemplo, `panel/estilo.py`) y que las dos páginas lo importen, sin cambiar cómo se ve el dashboard:

| Pieza de T12 | Qué es |
|---|---|
| `ESTILOS`, `BORDE`, `FONDO_TARJETA`, `FONDO_FRANJA`, `SUAVE`, `SERIE`, `ESPERA`, `ALERTA` | Los colores y estilos. **No dependen del tema** (DEC-156): fondos semitransparentes y el color del texto heredado, así funcionan en claro y en oscuro sin recargar |
| `_bloque`, `_seccion`, `_titulo`, `_nota`, `_tarjeta`, `_encabezado_lista` | Los bloques de HTML del diseño. **Solo** llevan números y textos fijos, siempre por `_e` (`html.escape`) |
| `ICONO_RELOJ`, `ICONO_ALERTA`, `ICONO_DOCUMENTO` y el botón con borde e ícono de "Abrir en Discord" | Los íconos y el estilo de botón |
| `DESTINOS`, `TIPOS_PLURAL`, `_hace`, `_dia`, `_corto` | Los textos de destino de cada tipo, las fechas relativas y los recortes |

**Seguridad (DEC-158 y AGENTS.md):** los textos de alumnos y de la IA (el mensaje original, el borrador, el motivo, los nombres) **nunca** van en HTML ni en markdown: van con `st.text`, `st.text_area` o `ui.mostrar_texto`.

## 4. Cómo comprobar el diseño

Antes de dar una pantalla por terminada: **capturas a 1440 px en claro y en oscuro**, comparadas con el archivo de esta carpeta, y cambiando el tema **sin recargar** desde el menú ⋮ → Settings. Así lo hizo T12 (informe §4.4: una copia aparte del panel en la red de Docker y Chromium sin pantalla).
