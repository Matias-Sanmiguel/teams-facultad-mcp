import asyncio
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading
import pytest
from playwright.async_api import async_playwright
from teams_facultad_mcp.core import Settings,ReferenceStore,AppError
from teams_facultad_mcp.teams import TeamsUI


@pytest.fixture
def slow_server():
    state={'bytes':0}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type','application/octet-stream')
            self.send_header('Content-Disposition','attachment; filename="slow.docx"')
            self.send_header('Content-Length','500000')
            self.end_headers()
            import time
            try:
                for _ in range(100):
                    self.wfile.write(b'x'*5000);self.wfile.flush();state['bytes']+=5000
                    time.sleep(.03)
            except (BrokenPipeError,ConnectionResetError): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}/slow.docx',state
    server.shutdown();server.server_close();thread.join()


async def prepare_stream(page,tmp_path,url,max_bytes=1000,timeout=2000):
    from test_download import download_ui
    ui,file=await download_ui(page,tmp_path,max_bytes=max_bytes)
    from dataclasses import replace
    ui.settings=replace(ui.settings,timeout_ms=timeout)
    await page.frames[1].get_by_role('menuitem',name='Descargar',include_hidden=True).evaluate('(e,url)=>e.href=url',url)
    return ui,file


async def test_transfer_is_cancelled_before_finishing_over_limit(page,tmp_path,slow_server):
    url,state=slow_server
    ui,file=await prepare_stream(page,tmp_path,url)
    with pytest.raises(AppError,match='archivo_grande'):
        await ui.download(file,tmp_path)
    assert state['bytes']<500000
    assert not [p for p in tmp_path.iterdir() if p.name!='original.docx']


async def test_cancellation_joins_transfer_and_leaves_no_artifact(page,tmp_path,slow_server):
    url,state=slow_server
    ui,file=await prepare_stream(page,tmp_path,url,max_bytes=1000000,timeout=5000)
    task=asyncio.create_task(ui.download(file,tmp_path))
    for _ in range(200):
        if state['bytes']>=10000:break
        await asyncio.sleep(.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    await asyncio.sleep(.2)
    assert not [p for p in tmp_path.iterdir() if p.name!='original.docx']
    assert state['bytes']<500000


async def test_transfer_deadline_cancels_slow_file(page,tmp_path,slow_server):
    url,state=slow_server
    ui,file=await prepare_stream(page,tmp_path,url,max_bytes=1000000,timeout=500)
    with pytest.raises(AppError,match='descarga_agotada'):
        await ui.download(file,tmp_path)
    assert state['bytes']<500000


async def test_cancellation_at_download_event_cleans_started_transfer(page, tmp_path, slow_server):
    url, state = slow_server
    ui, file = await prepare_stream(page, tmp_path, url, max_bytes=1000000, timeout=5000)
    # Cancel at the handoff from the browser event to the Python owner, before
    # save_as starts. Waiting for bytes can miss this race on faster machines.
    page.once('download', lambda download: task.cancel())
    task = asyncio.create_task(ui.download(file, tmp_path))
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(.2)
    assert not [p for p in tmp_path.iterdir() if p.name != 'original.docx']
    assert state['bytes'] < 500000
