# Evaluación de Obscura como motor del MCP

Fecha: 10 de noviembre de 2026. Resultado: **no adoptado**. Chromium sigue siendo
el motor del conector.

## Qué se probó

Se ejecutó el binario oficial Linux x86_64 de
[Obscura v0.2.6](https://github.com/h4ckf0r0day/obscura/releases/tag/v0.2.6).
SHA256 del archivo descargado:
`eed986e478c5ec5439f531f2d7fb6b0e36a356f1df7a6c44a8e8fd4f2486bd76`.
Se verificó contra el digest publicado en la API de releases de GitHub antes de
extraerlo y ejecutarlo.

La prueba usó Playwright Python del entorno del proyecto, conexión CDP a un
servidor Obscura enlazado a 127.0.0.1, perfiles nuevos y datos sintéticos.
Las mismas seis funciones de prueba existentes se ejecutaron en ambos motores.
No se copiaron cookies, tokens ni el perfil real de Microsoft a Obscura.

## Comparación de operaciones del conector

| Prueba existente | Obscura 0.2.6 | Chromium |
|---|---|---|
| Materias con referencias distintas y roles | Pasó | Pasó |
| Tareas dentro de un iframe | Tiempo agotado (35 s) | Pasó |
| Filas de archivos y carpetas | Pasó | Pasó |
| Lectura de anuncios | Pasó | Pasó |
| Cambio de estado de tareas dentro de un iframe | Tiempo agotado (35 s) | Pasó |
| Descarga por menú y lectura de DOCX | Tiempo agotado (35 s) | Pasó |

Resultado de esta selección: **3/6 con Obscura; 6/6 con Chromium**.
Son pruebas sintéticas de integración, no consultas de materias reales.

Funciones utilizadas: `test_spanish_courses_have_stable_distinct_refs`,
`test_assignments_in_iframe_by_status` (próximas),
`test_file_rows_preserve_folder_and_duplicate_names`,
`test_posts_read_author_date_and_body_without_replying`,
`test_tab_switch_waits_for_new_content` y
`test_download_through_sharepoint_menu_reads_document`.

## Reproducciones mínimas independientes

Para separar los problemas del motor de la lógica de Teams se hicieron dos
comprobaciones adicionales, también comparadas con Chromium.

### Exposición de iframes a Playwright

Con `<iframe srcdoc="<button>Dentro</button>"></iframe>`:

- Obscura: `page.frames` tenía inicialmente **1** elemento y luego **2**. Leer
  el `contentDocument` desde el DOM padre devolvió `Dentro`, pero consultar el
  botón mediante el locator del frame de Playwright agotó el plazo de 4 segundos.
- Chromium: `page.frames` tenía **2** elementos y el locator del frame encontró
  el botón.

El HTML del iframe y su frame finalmente existen en Obscura; el bloqueo concreto
es la consulta del locator dentro de ese frame. Por lo tanto, la diferencia
inicial en el número de frames no demuestra por sí sola ausencia de soporte.
La reproducción identifica una incompatibilidad del acceso mediante Playwright
que necesita el conector, sin atribuirla a una causa interna única del motor.

### Descarga nativa

Con un enlace `download="sample.txt"` a `data:text/plain,synthetic`:

- Obscura: `page.expect_download` agotó 2500 ms sin recibir el evento `download`.
- Chromium: recibió el evento, guardó el archivo y leyó exactamente `synthetic`.

Este caso no usa iframes ni SharePoint. Demuestra un segundo bloqueo independiente
para el mecanismo de descargas que usa el conector actual.

## Carga pública de Teams, sin autenticar

Se abrió `https://teams.cloud.microsoft/` con perfiles nuevos en ambos motores:

- Chromium llegó a `login.microsoftonline.com` y mostró el formulario de ingreso
  de Microsoft.
- Obscura por CDP permaneció en `teams.cloud.microsoft`, con título Microsoft
  Teams y una vista sin contenido útil después de la espera de la prueba.
- En una ejecución independiente por CLI, Obscura devolvió `Oops, unknown error!`
  y registró, entre otros errores JavaScript, `importScripts is not defined`.

La carga de una URL por sí sola no se consideró prueba de funcionamiento de
Teams. No se completó un ingreso ni MFA en Obscura, y no se afirma haber probado
una sesión autenticada con ese motor.

## Decisión

La versión probada no puede reemplazar al Chromium del MCP sin perder tareas y
lectura de documentos. Se conserva Chromium. La evaluación no sustituyó el motor ni utilizó el perfil
autenticado de la instalación existente.

Una evaluación futura debe repetir los casos de iframes y descarga, alcanzar el
login real, completar MFA de forma interactiva y verificar persistencia de sesión,
tareas y documentos antes de adoptar otro motor. Los resultados de este informe
se limitan a Obscura 0.2.6 en Linux; no generalizan a versiones futuras ni a todos
los usos del proyecto Obscura.
