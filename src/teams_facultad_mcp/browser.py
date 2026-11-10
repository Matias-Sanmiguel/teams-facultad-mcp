"""Own a dedicated Chromium profile; never borrow a personal browser session."""
from __future__ import annotations

import asyncio
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from playwright.async_api import async_playwright, Error as PlaywrightError

from .core import AppError, ProfileLease, Settings, source_url

TEAMS_HOME = 'https://teams.cloud.microsoft/'
AUTH_HOSTS = {'login.microsoftonline.com', 'login.live.com', 'login.microsoft.com'}


class BrowserSession:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lease = ProfileLease(settings.data_dir)
        self.context = None
        self.page = None
        self._pw = None
        self._downloads = None
        self.download_dir: Path | None = None
        self.lock = asyncio.Lock()

    async def start(self):
        if self.context is not None:
            try:
                if self.page and not self.page.is_closed():
                    return self.context
            except PlaywrightError:
                pass
            await self.close()
        self.lease.acquire()
        try:
            self._downloads = tempfile.TemporaryDirectory(prefix='teams-facultad-downloads-')
            self.download_dir = Path(self._downloads.name)
            self._pw = await async_playwright().start()
            self.context = await self._pw.chromium.launch_persistent_context(
                str(self.settings.profile), headless=self.settings.headless,
                accept_downloads=True, downloads_path=str(self.download_dir),
                viewport={'width': 1400, 'height': 1000}, locale='es-AR',
            )
            self.context.set_default_timeout(self.settings.timeout_ms)
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            return self.context
        except BaseException as exc:
            await self.close()
            if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                raise
            raise AppError('navegador_no_disponible',
                           'No se pudo abrir Chromium. Ejecutá doctor e instalá el navegador con python -m playwright install chromium; para modo visible necesitás una sesión gráfica.') from exc

    async def close(self):
        try:
            if self.context is not None:
                await self.context.close()
        finally:
            self.context, self.page = None, None
            try:
                if self._pw is not None:
                    await self._pw.stop()
            finally:
                self._pw = None
                if self._downloads:
                    self._downloads.cleanup()
                    self._downloads = None
                self.lease.release()

    async def page_state(self, page) -> str:
        if page.is_closed():
            return 'sin_iniciar'
        host = urlsplit(page.url).hostname
        if host in AUTH_HOSTS:
            return 'autenticacion_pendiente'
        pending = page.get_by_text(re.compile(r'Aprobar la solicitud|Approve sign.?in|Sign in to your account|Iniciar sesión en la cuenta|Pick an account|Elija una cuenta', re.I))
        if await pending.count() and await pending.first.is_visible():
            return 'autenticacion_pendiente'
        navigation = page.get_by_role('navigation', name=re.compile(r'^(Aplicaciones|Apps)$', re.I))
        if await navigation.count() and await navigation.first.is_visible():
            return 'conectado'
        return 'cargando'

    async def status(self) -> dict:
        if self.context is None:
            self.lease.acquire()
            self.lease.release()
        if self.page is None or self.page.is_closed():
            return {'ok': True, 'estado': 'sin_iniciar', 'mensaje': 'Usá iniciar_sesion o el comando login para abrir tu navegador dedicado.'}
        state = await self.page_state(self.page)
        return {'ok': True, 'estado': state, 'fuente': source_url(self.page.url),
                'mensaje': 'Sesión de Teams disponible.' if state == 'conectado' else 'Completá el ingreso en la ventana de Microsoft o esperá a que cargue Teams y consultá nuevamente.'}

    async def login(self) -> dict:
        if self.settings.headless:
            raise AppError('modo_sin_ventana', 'Para iniciar sesión quitá TEAMS_MCP_HEADLESS y ejecutá login en una sesión gráfica.')
        await self.start()
        if await self.page_state(self.page) != 'conectado':
            # Authentication continues in the visible browser after this call returns.
            try:
                await self.page.goto(TEAMS_HOME, wait_until='domcontentloaded', timeout=15000)
            except PlaywrightError:
                pass
        await self.page.bring_to_front()
        return await self.status()

    async def require_page(self):
        await self.start()
        if self.page.url == 'about:blank':
            await self.page.goto(TEAMS_HOME, wait_until='domcontentloaded')
        deadline = asyncio.get_running_loop().time() + self.settings.timeout_ms / 1000
        while True:
            state = await self.page_state(self.page)
            if state == 'conectado':
                return self.page
            if state == 'autenticacion_pendiente':
                raise AppError('autenticacion_pendiente', 'Completá el inicio de sesión en el navegador dedicado y volvé a consultar.')
            if asyncio.get_running_loop().time() >= deadline:
                raise AppError('interfaz_no_disponible', 'Teams no terminó de cargar. Revisá la ventana del navegador y ejecutá estado_conexion.')
            await asyncio.sleep(.25)
