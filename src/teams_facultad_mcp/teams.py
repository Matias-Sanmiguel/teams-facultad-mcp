"""Read-only adapters for Teams Education's rendered user interface."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re
import secrets
from contextlib import suppress

from playwright.async_api import TimeoutError as BrowserTimeout, Error as BrowserError
import anyio

from .browser import BrowserSession
from .core import AppError, Paginator, ReferenceStore, Settings, source_url, file_source_url
from .documents import extract_async, text_page

ASSIGNMENT_STATES = {
    'proximas': re.compile(r'^(Próximamente|Upcoming)$', re.I),
    'vencidas': re.compile(r'^(Vencida|Vencidas|Past due)$', re.I),
    'completadas': re.compile(r'^(Completado|Completadas|Completed)$', re.I),
}
EMPTY_TASKS = re.compile(r'No (hay |tienes |tenés |assignments|upcoming|past due)|all caught up|ninguna tarea|no tienes tareas|sin tareas', re.I)


def css_attr(name: str, value: str) -> str:
    return f'[{name}={json.dumps(value)}]'


class TeamsUI:
    def __init__(self, page, settings: Settings, refs: ReferenceStore):
        self.page, self.settings, self.refs = page, settings, refs

    async def _app(self, pattern: str):
        nav = self.page.get_by_role('navigation', name=re.compile(r'^(Aplicaciones|Apps)$', re.I))
        button = nav.get_by_role('button', name=re.compile(pattern, re.I))
        try:
            await button.click()
        except BrowserTimeout as exc:
            raise AppError('interfaz_no_disponible', 'No se encontró la aplicación en Teams. Revisá la sesión y la barra de aplicaciones.') from exc

    async def _frame(self, kind: str):
        deadline = asyncio.get_running_loop().time() + self.settings.timeout_ms / 1000
        while True:
            for frame in self.page.frames:
                if kind == 'tasks':
                    marker = frame.get_by_role('tab', name=re.compile(r'^(Próximamente|Upcoming|Vencida|Past due|Completado|Completed)$', re.I))
                elif kind == 'detail':
                    marker = frame.get_by_role('heading', name=re.compile(r'^(Instrucciones|Instructions)$', re.I))
                else:
                    marker = frame.get_by_role('grid').or_(frame.get_by_role('table'))
                if await marker.count() and await marker.first.is_visible():
                    return frame
            if asyncio.get_running_loop().time() >= deadline:
                raise AppError('interfaz_no_disponible', 'El panel de Teams no cargó, requiere iniciar sesión o cambió su interfaz. Revisá el navegador.')
            await asyncio.sleep(.2)

    async def _scan(self, locator, parser, *, rounds: int | None = None) -> list[dict]:
        """Bounded scan of currently rendered rows and their nearest scroll container."""
        found: dict[str, dict] = {}
        previous = None
        if await locator.count():
            await self._scroll(locator.first, reset=True)
        for _ in range(rounds or self.settings.scan_rounds):
            rows = await locator.evaluate_all(parser)
            for row in rows:
                key = row.get('key') or json.dumps(row, sort_keys=True)
                found[key] = row
            if not await locator.count():
                break
            scroll = await self._scroll(locator.last)
            fingerprint = (len(found), tuple(scroll) if scroll else None)
            if scroll is None or fingerprint == previous or scroll[0] == scroll[1]:
                break
            previous = fingerprint
            await asyncio.sleep(.15)
        return list(found.values())

    async def _scroll(self, locator, reset=False):
        result = await locator.evaluate('''(el,reset) => {
              let p=el.parentElement;
              while(p && !(p.scrollHeight>p.clientHeight+2 && /auto|scroll/.test(getComputedStyle(p).overflowY))) p=p.parentElement;
              if(!p) return null;
              const before=p.scrollTop;
              if(reset) p.scrollTop=0; else p.scrollBy(0,Math.max(1,p.clientHeight*.5));
              return [before,p.scrollTop,p.scrollHeight,p.clientHeight];
            }''', reset)
        if result and result[0] != result[1]:
            await asyncio.sleep(.15)
        return result

    async def seek(self, items, target):
        """Seek from the top and stop on the requested rendered identity."""
        try:
            await items.first.wait_for(state='visible', timeout=self.settings.timeout_ms)
        except BrowserTimeout as exc:
            raise AppError('recurso_no_disponible', 'La lista no terminó de cargar.') from exc
        await self._scroll(items.first, reset=True)
        for _ in range(self.settings.scan_rounds):
            if await target.count() and await target.first.is_visible():
                return
            if not await items.count():
                break
            scroll = await self._scroll(items.last)
            if scroll is None or scroll[0] == scroll[1]:
                break
        # One final bounded wait covers asynchronously inserted non-virtual rows.
        try:
            await target.first.wait_for(state='visible', timeout=self.settings.timeout_ms)
            return
        except BrowserTimeout as exc:
            raise AppError('recurso_no_disponible', 'No se encontró el recurso dentro del tramo recuperable de la lista; volvé a listar.') from exc

    async def _courses_home(self):
        await self._app(r'^(Equipos|Teams)$')
        back = self.page.get_by_role('button', name=re.compile(r'^(Volver a todos los equipos|All teams|Back to all teams)$', re.I))
        if await back.count() and await back.first.is_visible():
            await back.first.click()
        cards = self.page.locator('[data-testid="team-name"]')
        try:
            await cards.first.wait_for(state='visible', timeout=self.settings.timeout_ms)
        except BrowserTimeout as exc:
            raise AppError('interfaz_no_disponible', 'No se encontró la lista de equipos de clase. Abrí Equipos en la ventana para comprobar el acceso.') from exc
        return cards

    async def courses(self) -> list[dict]:
        cards = await self._courses_home()
        rows = await self._scan(cards, '''els => els.map(e=>{
          const g=e.closest('[role="group"]');
          return {name:(e.getAttribute('aria-label')||e.innerText).trim(), key:g?.getAttribute('data-tid')||''};
        })''')
        return [{'id': self.refs.add('materia', {'name': r['name'], 'dom_key': r['key']}),
                 'nombre': r['name']} for r in rows]

    async def _open_course(self, materia_id: str):
        ref = self.refs.get(materia_id, 'materia')
        cards = await self._courses_home()
        if ref['dom_key']:
            card = self.page.locator(css_attr('data-tid', ref['dom_key']))
            button = card.get_by_role('button', name=ref['name'], exact=True)
        else:
            button = self.page.get_by_role('button', name=ref['name'], exact=True)
        await self.seek(cards,button)
        if await button.count() != 1:
            raise AppError('recurso_no_disponible', 'La materia cambió o su nombre es ambiguo. Volvé a listar materias.')
        await button.click()
        general = self.page.get_by_role('treeitem', name='General', exact=True)
        await general.wait_for(state='visible')
        await general.click()
        return ref

    async def tasks(self, state: str, course_id: str | None = None, *, seek_id: str | None = None) -> list[dict]:
        if state not in ASSIGNMENT_STATES:
            raise AppError('estado_invalido', 'Usá proximas, vencidas o completadas.')
        course_name = ''
        if course_id:
            course = await self._open_course(course_id)
            course_name = course['name']
            await self.page.get_by_role('treeitem', name=re.compile(r'^(Tareas|Assignments)$',re.I)).click()
        else:
            await self._app(r'^(Tareas|Assignments)$')
        # A previous detail may still be open within the same application.
        for frame in self.page.frames:
            back = frame.get_by_role('button', name=re.compile(r'^(Atrás|Back)$'))
            if await back.count() and await back.first.is_visible():
                await back.first.click()
                break
        frame = await self._frame('tasks')
        tab = frame.get_by_role('tab', name=ASSIGNMENT_STATES[state])
        changing = await tab.get_attribute('aria-selected') == 'false'
        cards = frame.locator('[data-test="assignment-card"]')
        async def signature():
            return await cards.evaluate_all('es=>es.map(e=>e.id+":"+e.innerText).join("|")') + '::' + '|'.join(await frame.get_by_text(EMPTY_TASKS).all_text_contents())
        previous = await signature()
        await tab.click()
        deadline = asyncio.get_running_loop().time() + self.settings.timeout_ms / 1000
        busy_seen = False
        while True:
            busy = frame.get_by_role('progressbar').or_(frame.locator('[aria-busy="true"]'))
            is_busy = await busy.count() and await busy.first.is_visible()
            busy_seen = busy_seen or bool(is_busy)
            content_changed = not changing or await signature() != previous or (busy_seen and not is_busy)
            if content_changed and not is_busy and await cards.count():
                break
            empty = frame.get_by_text(EMPTY_TASKS)
            if content_changed and not is_busy and await empty.count() and await empty.first.is_visible():
                return []
            if asyncio.get_running_loop().time() >= deadline:
                raise AppError('interfaz_no_disponible', 'La lista de tareas no mostró elementos ni un estado vacío verificable.')
            await asyncio.sleep(.2)
        if seek_id:
            await self.seek(cards, frame.locator(css_attr('id',seek_id)))
            return []
        rows = await self._scan(cards, '''els=>els.map(e=>{
          const group=e.closest('[role="group"]');
          const header=group?.getAttribute('aria-labelledby');
          return {key:e.id, title:e.querySelector('[data-test^="assignment-card-title"]')?.textContent?.trim()||'',
          course:e.querySelector('[data-testid="card-classOrModuleName"]')?.textContent?.trim()||'',
          date:(header?document.getElementById(header)?.textContent:group?.getAttribute('aria-label'))||'',
          text:e.innerText};
        })''')
        return [{'id': self.refs.add('tarea', {'dom_id': r['key'], 'title': r['title'], 'course': r['course'] or course_name, 'state': state,'course_id':course_id}),
                 'titulo': r['title'], 'materia': r['course'] or course_name, 'estado_lista': state,
                 'fecha_original': f"{r['date']} · {r['text']}".strip(' ·'),
                 'fuente': source_url(frame.url)} for r in rows if r['key'] and r['title']]

    async def task(self, task_id: str) -> dict:
        ref = self.refs.get(task_id, 'tarea')
        await self.tasks(ref['state'],ref.get('course_id'),seek_id=ref['dom_id'])
        frame = await self._frame('tasks')
        card = frame.locator(css_attr('id', ref['dom_id']))
        if await card.count() != 1:
            raise AppError('recurso_no_disponible', 'No se encontró la tarea en su lista. Volvé a listar tareas.')
        await card.click()
        detail = await self._frame('detail')
        return {'id': task_id, 'materia': ref['course'], **await self.task_detail(detail)}

    async def task_detail(self, frame) -> dict:
        heading = frame.get_by_role('heading', level=1)
        title = (await heading.first.inner_text()).strip()
        body = await frame.locator('body').inner_text()
        instruction_heading = frame.get_by_role('heading', name=re.compile(r'^(Instrucciones|Instructions)$', re.I))
        instructions = ''
        if await instruction_heading.count():
            instructions = await instruction_heading.first.evaluate('''h=>{
              const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
              const out=[]; let active=false;
              for(let n=walker.nextNode();n;n=walker.nextNode()){
                if(h.contains(n)){active=true;continue;}
                if(!active) continue;
                if(n.parentElement.closest('h1,h2,h3,[role="heading"]')) break;
                if(!n.parentElement.closest('button,script,style,input,select,textarea') && n.textContent.trim()) out.push(n.textContent.trim());
              }
              return out.join('\\n');
            }''')
        due = re.search(r'(?:Vence|Due)[^\n]+', body, re.I)
        status = re.search(r'\b(No entregada|Entregada|Devuelta|Not turned in|Turned in|Returned)\b', body, re.I)
        links = await frame.get_by_role('link').evaluate_all('els=>els.map(e=>({nombre:e.innerText,url:e.href})).filter(e=>e.nombre)')
        return {'ok': True, 'titulo': title, 'instrucciones': instructions,
                'vencimiento_original': due.group(0) if due else None, 'estado': status.group(1).strip() if status else None,
                'materiales': [{'nombre': x['nombre'], 'fuente': source_url(x['url'])} for x in links],
                'fuente': source_url(frame.url)}

    async def _channel_tab(self, name: str):
        pattern = re.compile(r'^(Compartido|Shared|Archivos|Files)$' if name == 'files' else r'^(Publicaciones|Posts)$', re.I)
        tab = self.page.get_by_role('tab', name=pattern)
        if await tab.count() and await tab.first.is_visible():
            await tab.first.click()
            return
        # Narrow layouts collapse channel tabs into a button menu.
        current = self.page.get_by_role('button', name=re.compile(r'^(Publicaciones|Posts|Compartido|Shared|Archivos|Files)$', re.I))
        await current.first.click()
        option = self.page.get_by_role('menuitem', name=pattern).or_(self.page.get_by_role('menuitemradio', name=pattern))
        await option.first.click()

    async def post_rows(self) -> list[dict]:
        rows = self.page.locator('[id^="message-body-"]')
        raw = await self._scan(rows, '''els=>els.map(e=>{
          const author=e.querySelector('[data-tid="message-author-name"]');
          const time=e.querySelector('time,[id^="timestamp-"]');
          const content=e.querySelector('[id^="content-"]');
          return {key:e.id, author:author?.textContent?.trim()||e.innerText.split('\\n')[0],
          date:time?.getAttribute('datetime')||time?.getAttribute('aria-label')||time?.innerText||'',
          title:e.querySelector('h2')?.textContent||'', text:content?.innerText||e.getAttribute('aria-label')||e.innerText};
        })''')
        return [{'id': self.refs.add('anuncio', {'dom_id': x['key']}), 'autor': x['author'],
                 'fecha_original': x['date'], 'titulo': x['title'], 'texto': x['text'],
                 'fuente': source_url(self.page.url)} for x in raw]

    async def posts(self, materia_id: str) -> list[dict]:
        await self._open_course(materia_id)
        await self._channel_tab('posts')
        await self.page.locator('[id^="message-body-"]').first.wait_for(state='visible')
        return await self.post_rows()

    async def files_frame(self, materia_id: str, path: list[str], path_keys: list[str] | None = None):
        await self._open_course(materia_id)
        await self._channel_tab('files')
        frame = await self._frame('files')
        # SharePoint remembers the previous folder; explicitly return to General.
        root_heading = frame.get_by_role('heading', name='General', exact=True)
        if not await root_heading.count() or not await root_heading.first.is_visible():
            parents = frame.get_by_role('button', name=re.compile(r'^(Carpetas principales|Parent folders)$', re.I))
            if await parents.count() and await parents.first.is_visible():
                await parents.first.click()
                general = frame.get_by_role('menuitem', name='General', exact=True).or_(frame.get_by_role('link', name='General', exact=True))
                try:
                    await general.first.wait_for(state='visible',timeout=self.settings.timeout_ms)
                    await general.first.click()
                    await frame.get_by_role('heading',name='General',exact=True).wait_for(state='visible')
                except BrowserTimeout as exc:
                    raise AppError('carpeta_no_disponible', 'No se pudo volver a General. Abrí General en el navegador y reintentá.') from exc
        await self.grid_for(frame,'General')
        for index,folder in enumerate(path):
            grid = await self.grid_for(frame,path[index-1] if index else 'General')
            if path_keys:
                row = await self.resource_row(frame,folder,path_keys[index])
                button = row.get_by_role('button', name=folder, exact=True)
            else:
                button = grid.get_by_role('button', name=folder, exact=True)
                await self.seek(grid.get_by_role('row'),button)
            if await button.count() != 1:
                raise AppError('carpeta_no_disponible', 'No se encontró una carpeta o su nombre es ambiguo. Volvé a listar archivos.')
            await button.click()
            await frame.get_by_role('heading', name=folder, exact=True).wait_for(state='visible')
            await self.grid_for(frame,folder)
        return frame

    async def grid_for(self,frame,name):
        grid=frame.get_by_role('grid',name=name,exact=True)
        try:
            await grid.wait_for(state='visible',timeout=self.settings.timeout_ms)
        except BrowserTimeout as exc:
            raise AppError('interfaz_no_disponible','SharePoint no confirmó la lista de la carpeta solicitada; revisá la ventana y reintentá.') from exc
        return grid

    async def file_rows(self, frame, materia_id: str, path: list[str], path_keys: list[str] | None = None) -> list[dict]:
        grid = await self.grid_for(frame,path[-1] if path else 'General')
        deadline = asyncio.get_running_loop().time() + self.settings.timeout_ms / 1000
        parser = '''els=>els.filter(e=>!e.querySelector('[role="columnheader"]')).map(e=>{
          const buttons=[...e.querySelectorAll('button,[role="button"]')];
          const button=e.querySelector('[data-id="heroField"]') || buttons.find(b=>!/(Más acciones|More actions|Compartir|Share|Favoritos|Favorites|perfil|profile|OneDrive)/i.test(b.getAttribute('aria-label')||b.innerText));
          const imgs=[...e.querySelectorAll('img,[role="img"]')].map(x=>x.getAttribute('aria-label')||x.getAttribute('alt')||'').join(' ');
          return {key:e.getAttribute('data-item-id')||e.getAttribute('data-id')||e.getAttribute('data-selection-index')||e.id,
          name:button?.textContent?.trim()||'',folder:/carpeta|folder/i.test(imgs+' '+e.getAttribute('aria-label')),
          text:e.innerText};
        }).filter(e=>e.name)'''
        while True:
            raw = await self._scan(grid.get_by_role('row'),parser)
            if raw:
                break
            empty = frame.get_by_text(re.compile(r'^(Esta carpeta está vacía|Esta carpeta no contiene|This folder is empty|No items|No hay elementos)', re.I))
            if await empty.count() and await empty.first.is_visible():
                return []
            if asyncio.get_running_loop().time() >= deadline:
                raise AppError('interfaz_no_disponible', 'Los archivos no terminaron de cargar y no hay un estado de carpeta vacía verificable.')
            await asyncio.sleep(.2)
        result = []
        for row in raw:
            kind = 'carpeta' if row['folder'] else 'archivo'
            ref = {'materia_id': materia_id, 'path': path + [row['name']] if row['folder'] else path,
                   'path_keys': (path_keys or []) + [row['key']] if row['folder'] else (path_keys or []),
                   'name': row['name'], 'row_key': row['key']}
            result.append({'id': self.refs.add(kind, ref), 'nombre': row['name'], 'tipo': kind,
                           'detalle_original': row['text'], 'fuente': file_source_url(frame.url,row['name'])})
        return result

    async def files(self, materia_id: str, folder_id: str | None) -> list[dict]:
        self.refs.get(materia_id, 'materia')
        path = []
        path_keys = []
        if folder_id:
            folder = self.refs.get(folder_id, 'carpeta')
            if folder['materia_id'] != materia_id:
                raise AppError('referencia_invalida', 'La carpeta pertenece a otra materia.')
            path = folder['path']
            path_keys = folder.get('path_keys',[])
            if len(path_keys) != len(path):
                raise AppError('referencia_desactualizada','Volvé a listar la carpeta para recuperar su identidad.')
        frame = await self.files_frame(materia_id, path,path_keys)
        return await self.file_rows(frame, materia_id, path,path_keys)

    async def resource_row(self, frame, name: str, key: str):
        if not key:
            raise AppError('referencia_desactualizada','La interfaz no proporcionó una identidad verificable para este recurso.')
        folder_name=(await frame.get_by_role('heading').first.inner_text()).strip()
        rows = (await self.grid_for(frame,folder_name)).get_by_role('row')
        named = rows.filter(has=frame.get_by_role('button',name=name,exact=True))
        selector = ','.join(css_attr(attr,key) for attr in ['data-item-id','data-id','data-selection-index','id'])
        target = named.and_(frame.locator(selector))
        try:
            await self.seek(rows,target)
        except AppError as exc:
            if await named.count():
                raise AppError('referencia_desactualizada','Hay un recurso con ese nombre pero su identidad cambió. Volvé a listar.') from exc
            raise
        if await target.count() != 1:
            raise AppError('referencia_desactualizada','La identidad del recurso es ambigua. Volvé a listar.')
        return target

    async def download(self, file_id: str, directory: Path) -> tuple[Path | None, dict]:
        ref = self.refs.get(file_id, 'archivo')
        path_keys = ref.get('path_keys',[])
        if len(path_keys) != len(ref['path']):
            raise AppError('referencia_desactualizada','Volvé a listar el archivo y sus carpetas.')
        frame = await self.files_frame(ref['materia_id'], ref['path'],path_keys)
        grid = frame.get_by_role('grid').first
        row = await self.resource_row(frame,ref['name'],ref['row_key'])
        # The row's own menu targets the verified file without having to toggle
        # SharePoint's custom checkbox or open an editable document.
        await row.hover()
        more = row.get_by_role('button', name=re.compile(r'^(Más acciones|More actions)$', re.I))
        if not await more.count():
            check = row.get_by_role('checkbox')
            if not await check.is_checked():
                await row.get_by_role('gridcell').filter(has=check).click()
            more = frame.get_by_role('menuitem', name=re.compile(r'^(Más|More)$', re.I))
        await more.first.click()
        item = frame.get_by_role('menuitem', name=re.compile(r'^(Descargar|Download)$', re.I))
        try:
            await item.first.wait_for(state='visible',timeout=min(3000,self.settings.timeout_ms))
        except BrowserTimeout:
            pass
        if await item.count() and await item.first.is_visible():
            baseline = set(directory.rglob('*'))
            async with self.page.expect_download(timeout=self.settings.timeout_ms) as pending:
                await item.first.click()
            download = await pending.value
            extension = Path(ref['name']).suffix.lower()
            path = directory / (secrets.token_hex(16) + extension)
            task = asyncio.create_task(download.save_as(path))
            success = False
            deadline = asyncio.get_running_loop().time() + self.settings.timeout_ms / 1000
            try:
                while not task.done():
                    artifacts = [p for p in directory.rglob('*') if p not in baseline and p.is_file()]
                    if max((p.stat().st_size for p in artifacts if p.exists()),default=0) > self.settings.max_file_bytes:
                        raise AppError('archivo_grande', 'El archivo supera 25 MiB.')
                    if asyncio.get_running_loop().time() >= deadline:
                        raise AppError('descarga_agotada','La descarga excedió el tiempo permitido; reintentá o descargá manualmente.')
                    await asyncio.wait({task},timeout=.1)
                await task
                if path.stat().st_size > self.settings.max_file_bytes:
                    raise AppError('archivo_grande', 'El archivo supera 25 MiB.')
                success = True
                return path, {'nombre': ref['name'], 'fuente': file_source_url(frame.url,ref['name'])}
            finally:
                with anyio.CancelScope(shield=True):
                    if not task.done():
                        with suppress(BrowserError):
                            await download.cancel()
                        task.cancel()
                    await asyncio.gather(task,return_exceptions=True)
                    with suppress(BrowserError):
                        await download.delete()
                    if not success:
                        path.unlink(missing_ok=True)
                        # Chromium can leave a canceled .crdownload artifact until
                        # context shutdown. This directory is a private per-process
                        # cache; remove only files created by this transfer window.
                        for _ in range(20):
                            remaining = [p for p in directory.rglob('*') if p not in baseline and p.is_file()]
                            if not remaining:
                                break
                            for artifact in remaining:
                                with suppress(OSError):
                                    artifact.unlink(missing_ok=True)
                            await asyncio.sleep(.05)
        await self.page.keyboard.press('Escape')
        # A document viewer can supply a partial result when download is unavailable.
        before = set(self.page.context.pages)
        await grid.get_by_role('button', name=ref['name'], exact=True).click()
        deadline = asyncio.get_running_loop().time() + self.settings.timeout_ms / 1000
        while asyncio.get_running_loop().time() < deadline:
            candidates = [p for p in self.page.context.pages if p not in before] + [self.page]
            for page in candidates:
                for child in page.frames:
                    content = child.locator('#WACViewPanel')
                    if await content.count() and await content.first.is_visible():
                        text = (await content.first.inner_text())[:2_000_000]
                        if page is not self.page:
                            await page.close()
                        return None, {'nombre': ref['name'], 'fuente': source_url(child.url), 'texto': text,
                                      'extraccion_completa': False,
                                      'aviso': 'Descarga no disponible. Solo se recuperó el texto visible del visor; pueden faltar páginas.'}
            await asyncio.sleep(.25)
        raise AppError('descarga_no_disponible', 'No se encontró una descarga ni texto legible del visor. Abrí el archivo manualmente.')


class TeamsService:
    def __init__(self, settings: Settings):
        self.session = BrowserSession(settings)
        self.settings = settings
        self.refs = ReferenceStore()
        self.pages = Paginator()
        self.documents: dict[str, dict] = {}

    async def close(self):
        await self.session.close()

    async def call(self, name: str, **args):
        async with self.session.lock:
            if name == 'estado_conexion':
                return await self.session.status()
            if name == 'iniciar_sesion':
                return await self.session.login()
            cursor = args.pop('cursor', None)
            limit = args.pop('limite', 50)
            scope = json.dumps([name, args], sort_keys=True)
            if name != 'leer_documento' and cursor:
                return self.pages.next(cursor, scope, limit)
            if name not in {'leer_tarea', 'leer_documento'}:
                self.pages.validate_limit(limit)
            page = await self.session.require_page()
            ui = TeamsUI(page, self.settings, self.refs)
            if name == 'listar_materias':
                return self.pages.first(await ui.courses(), scope, limit, complete=False)
            if name == 'listar_tareas':
                courses = await ui.tasks(args.get('estado', 'proximas'),args.get('materia_id'))
                return self.pages.first(courses, scope, limit, complete=False)
            if name == 'leer_tarea':
                return await ui.task(args['tarea_id'])
            if name == 'leer_anuncios':
                return self.pages.first(await ui.posts(args['materia_id']), scope, limit, complete=False)
            if name == 'listar_archivos':
                return self.pages.first(await ui.files(args['materia_id'], args.get('carpeta_id')), scope, limit, complete=False)
            if name == 'leer_documento':
                key = args['archivo_id']
                self.refs.get(key, 'archivo')
                if key not in self.documents:
                    path, meta = await ui.download(key, self.session.download_dir)
                    try:
                        self.documents[key] = {**meta, **(await extract_async(path, self.settings.max_file_bytes) if path else {})}
                    finally:
                        if path:
                            path.unlink(missing_ok=True)
                    if len(self.documents) > 8:
                        self.documents.pop(next(iter(self.documents)))
                document = self.documents[key]
                scope = f'documento:{key}'
                # Document cursors reuse the same authenticated paginator, in chunks.
                if cursor:
                    result = self.pages.next(cursor, scope, 1)
                else:
                    chunk = args.get('limite_caracteres', 10000)
                    text_page(document['texto'], limit=chunk)
                    chunks = [document['texto'][i:i+chunk] for i in range(0, len(document['texto']), chunk)]
                    result = self.pages.first(chunks, scope, 1, complete=document['extraccion_completa'])
                text = ''.join(result.pop('items'))
                return {**result, 'texto': text, 'nombre': document['nombre'],
                        'fuente': document['fuente'], 'aviso': document.get('aviso'),
                        'extraccion_completa': document['extraccion_completa']}
            raise AppError('herramienta_invalida', 'Herramienta desconocida.')
