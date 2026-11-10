# Verificación de la versión 0.1.0

## Comprobado localmente

En Linux, con Python 3.12, Chromium dedicado y una cuenta real de Teams Educación:

- Ingreso interactivo y reapertura de la sesión desde procesos nuevos.
- Descubrimiento y llamadas a las ocho herramientas por stdio.
- Listado de materias, tareas por estado y lectura de consignas y vencimientos.
- Lectura de publicaciones y respuestas visibles del canal General.
- Navegación de carpetas y listado de materiales en SharePoint.
- Descarga de un DOCX, extracción de texto y paginación del resultado.
- Instalación desde un ZIP limpio, incluso sin pip/ensurepip preinstalado.
- Registro en la configuración local de Codex y prueba de la orden registrada
  con un cliente MCP: sesión disponible y consulta de materias correcta.

Los contenidos de la cuenta y el perfil del navegador se mantuvieron fuera del
repositorio. No se publican capturas, nombres de materias, tareas ni documentos.

## Pruebas automáticas

Ejecutá `python -m pytest -q` en el entorno del proyecto. La suite cubre:

- Perfiles exclusivos, autenticación, persistencia y limpieza.
- Referencias opacas, cursores, paginación e identidad de recursos reemplazados.
- Interfaces en español/inglés, iframes, cargas tardías y listas virtualizadas.
- Descargas limitadas por bytes y tiempo, cancelación y archivos temporales.
- DOCX, PPTX y PDF; límites de expansión, texto, páginas y tiempo de extracción.
- Empaquetado por lista explícita y exclusión de perfiles, configuraciones y symlinks.
- MCP por stdio con protocolos actuales y anteriores.

La matriz pública de [GitHub Actions](https://github.com/Matias-Sanmiguel/teams-facultad-mcp/actions/workflows/tests.yml)
ejecuta las pruebas en Linux, Windows y macOS. Consultá allí el resultado de cada
commit; disponer de un workflow no demuestra por sí mismo que haya pasado.

## Límites de esta evidencia

Las pruebas con una cuenta institucional y el instalador completo se realizaron
en Linux. La matriz de CI usa datos sintéticos: no prueba el ingreso institucional
ni una instalación interactiva en Windows/macOS.

Otras instituciones pueden tener políticas o variantes de interfaz distintas.
No se promete evitar una restricción institucional. La descarga real validada fue
un DOCX; PPTX/PDF se prueban con archivos sintéticos. No hay OCR ni garantía de
fidelidad para imágenes o diagramas.

En Windows no se aplican los límites Unix de memoria/CPU; permanecen los límites
de tiempo, archivo, expansión y texto. Las pruebas no son una auditoría exhaustiva
contra cualquier documento hostil ni de toda la cadena de dependencias.

Las herramientas pueden requerir una recarga del cliente o un nuevo chat luego
de registrarlas. El resultado de un cliente stdio de prueba no demuestra que un
chat ya abierto haya recargado automáticamente las herramientas.
