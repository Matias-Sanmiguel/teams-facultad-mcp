import pytest
import time
from teams_facultad_mcp.browser import BrowserSession
from teams_facultad_mcp.core import Settings, AppError


async def test_browser_releases_profile_and_reuses_state(tmp_path):
    settings = Settings(tmp_path, headless=True)
    first = BrowserSession(settings)
    context = await first.start()
    await context.add_cookies([{'name': 'test-cookie', 'value': 'persisted', 'url': 'https://teams.cloud.microsoft/', 'expires': time.time() + 3600}])
    second = BrowserSession(settings)
    with pytest.raises(AppError, match='perfil_ocupado'):
        await second.start()
    await first.close()
    context = await second.start()
    assert any(c['name'] == 'test-cookie' for c in await context.cookies())
    download_dir = second.download_dir
    await second.close()
    assert not download_dir.exists()


async def test_initial_status_does_not_launch_browser(tmp_path):
    session = BrowserSession(Settings(tmp_path, headless=True))
    result = await session.status()
    assert result['estado'] == 'sin_iniciar'
    assert session.context is None


async def test_status_reports_another_profile_owner(tmp_path):
    owner=BrowserSession(Settings(tmp_path,headless=True))
    owner.lease.acquire()
    try:
        other=BrowserSession(Settings(tmp_path,headless=True))
        with pytest.raises(AppError,match='perfil_ocupado'):
            await other.status()
    finally:
        owner.lease.release()


async def test_auth_state_detects_login_and_mfa(page, tmp_path):
    session = BrowserSession(Settings(tmp_path, headless=True))
    await page.set_content('<h1>Aprobar la solicitud de inicio de sesión</h1>')
    assert await session.page_state(page) == 'autenticacion_pendiente'
    await page.set_content('<nav aria-label="Aplicaciones"><button>Tareas</button></nav>')
    assert await session.page_state(page) == 'conectado'


async def test_missing_browser_is_actionable(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAYWRIGHT_BROWSERS_PATH', str(tmp_path / 'missing'))
    session = BrowserSession(Settings(tmp_path / 'data', headless=True))
    with pytest.raises(AppError, match='navegador_no_disponible'):
        await session.start()
    assert session.context is None
    assert not session.lease.lock.is_locked
