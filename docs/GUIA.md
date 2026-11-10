# Guía de instalación y uso

Un servidor MCP local para consultar Teams Educación desde tu asistente: materias,
tareas, consignas, anuncios y materiales. Cada alumno usa su propia cuenta en un
Chromium dedicado y guarda la sesión en su computadora.

Funciona mediante la interfaz web de Teams. No registra una aplicación en Entra,
no utiliza Microsoft Graph ni pide sus permisos de administrador. El acceso sigue
dependiendo de tu cuenta y de las políticas de tu institución.

## Requisitos

- Python **3.11 o posterior** y conexión a Internet para instalar dependencias.
- Un cliente MCP que pueda ejecutar servidores locales por **stdio**.
- Una sesión gráfica para iniciar sesión en Microsoft y completar MFA.
- Espacio para Chromium y las dependencias (varios cientos de MB).

Se incluyen instaladores para Windows, macOS y Linux. La verificación realizada en
esta entrega está detallada en [VERIFICACION.md](VERIFICACION.md).
El programa es gratuito; tu aplicación de IA puede tener su propio costo.

## Instalación

Descomprimí el ZIP en una carpeta que vayas a conservar. Si movés la carpeta
después, volvé a ejecutar el instalador y actualizá la configuración de tu cliente.

### Windows

Instalá Python desde [python.org](https://www.python.org/downloads/) si no lo tenés.
Abrí una terminal en la carpeta descomprimida y ejecutá:

```powershell
py -3 scripts/install.py
```

También se incluye `install.ps1`. Usar directamente el comando de Python evita
tener que cambiar la política de ejecución de scripts de PowerShell.

### macOS o Linux

```sh
sh install.sh
```

El instalador crea `.venv`, instala dependencias fijadas y verificadas con hashes,
descarga Chromium y genera **`mcp-config.json`**. No cambia la configuración de
ninguna aplicación ni instala paquetes Python globales.

En Linux pueden faltar bibliotecas del sistema que necesita Chromium. Si Playwright
lo informa, revisá su mensaje y la [guía oficial](https://playwright.dev/python/docs/browsers#install-system-dependencies).
El instalador no intenta obtener permisos de administrador del equipo por su cuenta.
Los permisos locales de tu computadora son distintos del consentimiento de la facultad.

## Iniciar sesión

Antes de conectar el MCP, ejecutá en una terminal:

Windows (PowerShell):

```powershell
& .\.venv\Scripts\python.exe -m teams_facultad_mcp login
```

macOS/Linux:

```sh
.venv/bin/python -m teams_facultad_mcp login
```

Se abre un navegador nuevo. Ingresá tu cuenta de la facu y completá la verificación
de Microsoft. Cuando Teams termine de cargar, el comando confirma el ingreso y
cierra la ventana para liberar el perfil al MCP. Podés extender la espera con
`login --timeout 900` (segundos). No compartas la carpeta del perfil.

Las sesiones persistentes se conservan entre ejecuciones. Microsoft puede exigir
un nuevo ingreso; las cookies de sesión que el navegador considera temporales
pueden caducar al cerrarlo. El programa informa cuándo necesita intervención.

## Conectar tu asistente

Copiá la entrada de **`mcp-config.json`** a la configuración de servidores locales
de tu cliente MCP. El archivo ya contiene la ruta absoluta al Python correcto:

```json
{
  "mcpServers": {
    "teams-facultad": {
      "command": "RUTA_ABSOLUTA_A_ESTA_CARPETA/.venv/bin/python",
      "args": ["-m", "teams_facultad_mcp", "serve"],
      "env": {"TEAMS_MCP_HEADLESS": "1"}
    }
  }
}
```

En Windows la ruta termina en `.venv\\Scripts\\python.exe`. Algunos clientes usan
otro formato para registrar servidores; conservá el mismo `command`, `args` y
`env` del archivo generado. Una aplicación que solo acepte una URL remota no puede
usar directamente este servidor local. Reiniciá o recargá los servidores de tu
cliente cuando termines de configurarlo.

Para regenerar la configuración usá `python -m teams_facultad_mcp config` con el
Python de `.venv`. En Linux conserva las variables de pantalla necesarias: algunos
clientes no las transmiten automáticamente al subproceso. No copies la configuración
de otro alumno: la ruta y las variables se generan en cada computadora.

La configuración generada usa `TEAMS_MCP_HEADLESS=1` para consultar sin ventana.
Una consulta como `listar_materias` abre el navegador oculto y recupera la sesión
guardada, aunque `estado_conexion` inicialmente indique `sin_iniciar`.

Si Microsoft pide volver a ingresar, cerrá el cliente MCP para liberar el perfil,
ejecutá `login` desde una terminal gráfica sin esa variable activada y reabrí el
cliente. No ejecutes `login` al mismo tiempo que otro proceso usa el perfil.

Para abrir el navegador durante un diagnóstico, poné `TEAMS_MCP_HEADLESS=0` en
`env` y recargá el servidor. En ese modo también se puede usar `iniciar_sesion`
desde el chat: completá el ingreso y consultá `estado_conexion`.

## Herramientas

| Herramienta | Uso |
|---|---|
| `estado_conexion` | Estado del navegador y del ingreso |
| `iniciar_sesion` | Abrir el navegador para autenticarte |
| `listar_materias` | Equipos visibles y sus identificadores |
| `listar_tareas` | `proximas`, `vencidas` o `completadas`; filtro opcional por materia |
| `leer_tarea` | Consigna, fecha completa, estado y referencias visibles |
| `leer_anuncios` | Publicaciones y respuestas visibles del canal General |
| `listar_archivos` | Archivos o carpetas del canal General |
| `leer_documento` | Texto de DOCX, PPTX y PDF, en fragmentos |

Ejemplos de pedidos:

- “Listá mis tareas próximas y leé las consignas de las que vencen primero”.
- “Mostrame los anuncios de Ingeniería de Software”.
- “Buscá el cronograma en Documentos del Curso y resumilo”.

Usá los IDs devueltos por las herramientas; no son URLs. Vencen al reiniciar el
servidor. Para entrar en una carpeta, usá su ID en `listar_archivos`. Si hay un
`cursor`, repetí la misma consulta con ese cursor para obtener la siguiente página.
`leer_documento` devuelve hasta 10.000 caracteres por fragmento.

## Alcance y límites

- Consultas de una cuenta por instalación; las operaciones se ejecutan de a una.
- No envía mensajes, entrega trabajos, adjunta archivos ni edita documentos.
  Abrir anuncios puede marcarlos como leídos y Teams puede actualizar tu presencia.
- Las listas virtualizadas pueden ser parciales. `completo: false` y `aviso`
  indican que el resultado no permite asegurar que no existan más elementos.
- Fechas conservadas tal como aparecen en Teams; `leer_tarea` permite consultar
  el vencimiento completo sin inferir un año a partir de una fecha abreviada.
- Documentos de hasta **25 MiB**; máximo de 2 millones de caracteres extraídos.
  No incluye OCR, imágenes, diagramas, audio, videos ni PDF protegidos por contraseña.
- La lectura se ejecuta en un proceso separado con un máximo de 30 segundos.
  Los PDF tienen un límite de 1000 páginas y de 100 MiB de contenido decodificado
  acumulado; los DOCX/PPTX también tienen un límite de expansión de 100 MiB.
- Si no hay descarga disponible, puede devolver solo el texto visible del visor,
  marcado explícitamente como parcial. Los archivos temporales se eliminan al cerrar.
- Una actualización de la interfaz de Teams puede requerir actualizar el programa.
- No funciona cuando tu computadora está apagada. No se aloja un servicio remoto.

## Sesiones y datos locales

El perfil queda fuera del proyecto, en el directorio de datos de tu usuario:

- Windows: `%LOCALAPPDATA%\\teams-facultad-mcp`.
- macOS: `~/Library/Application Support/teams-facultad-mcp`.
- Linux: `~/.local/share/teams-facultad-mcp`.

El comando `doctor` muestra la ruta efectiva. Se puede cambiar con la variable
`TEAMS_MCP_DATA_DIR`; para configuraciones normales no hace falta. No se leen
perfiles ni credenciales de tu Chrome/Firefox habitual. Para cambiar de cuenta,
cerrá sesión desde la interfaz de Microsoft en el navegador dedicado.

Cada cliente MCP puede enviar a su proveedor de IA los resultados que consulta,
según su configuración. El servidor no envía tus documentos a un servicio propio.

## Diagnóstico

Ejecutá con el Python de `.venv`:

```sh
python -m teams_facultad_mcp doctor
```

| Mensaje | Qué hacer |
|---|---|
| `perfil_ocupado` | Cerrá otro cliente MCP o el comando `login` que usa el perfil |
| `autenticacion_pendiente` | Completá el ingreso/MFA en el navegador y reintentá |
| `navegador_no_disponible` | Revisá `doctor`, la instalación de Chromium y la pantalla gráfica |
| `interfaz_no_disponible` / `tiempo_agotado` | Revisá la ventana de Teams; puede estar cargando, requerir ingreso o haber cambiado |
| `referencia_invalida` / `cursor_invalido` | Volvé a listar el recurso sin reutilizar IDs de un proceso anterior |
| `referencia_desactualizada` | El archivo o una carpeta cambió de identidad; volvé a listar antes de abrirlo |
| `descarga_no_disponible` | Abrí el archivo manualmente para comprobar sus permisos |
| `descarga_agotada` / `procesamiento_agotado` | El archivo excedió el tiempo o los recursos permitidos; probá descargarlo manualmente |
| `sin_texto` | El documento puede estar vacío o escaneado; no hay OCR |

`TEAMS_MCP_HEADLESS=1` permite consultas sin ventana y es el valor predeterminado
de la configuración generada. El ingreso interactivo se completa con el comando
`login` en modo visible, antes de abrir el cliente MCP.

## Desarrollo y distribución

```sh
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
.venv/bin/python -m pytest -q
.venv/bin/python -m build
.venv/bin/python scripts/package.py
```

Las pruebas de navegador usan páginas sintéticas y no necesitan una cuenta real.
Se incluyen pruebas MCP por stdio para protocolos actuales y anteriores, y un
workflow de CI para los tres sistemas. La existencia del workflow no significa
que ya se haya ejecutado en Windows/macOS.

Compartí el ZIP generado en `dist`, que se arma con una lista explícita de archivos.
No compartas `.venv`, tu `mcp-config.json` ni tu perfil de navegador.

Licencia MIT. Es un proyecto independiente, sin afiliación con Microsoft o la facultad.
