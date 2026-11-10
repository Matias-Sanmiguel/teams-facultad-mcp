import base64
import html
from docx import Document
import pytest
from teams_facultad_mcp.core import Settings, ReferenceStore, AppError
from teams_facultad_mcp.teams import TeamsUI, TeamsService
from teams_facultad_mcp.documents import extract_document


async def download_ui(page, tmp_path, *, max_bytes=25*1024*1024):
    doc = Document()
    doc.add_paragraph('Consigna para descargar y estudiar')
    original = tmp_path / 'original.docx'
    doc.save(original)
    data = base64.b64encode(original.read_bytes()).decode()
    inner = f'''<h2>General</h2><div role="grid" aria-label="General"><div role="row" data-id="file-1">
      <span role="gridcell"><input type="checkbox" aria-label="Seleccionar fila"></span>
      <span role="gridcell"><span role="button" data-id="heroField">Apunte.docx</span>
      <button aria-label="Más acciones" onclick="document.getElementById('menu').hidden=false"></button></span></div></div>
      <div id="menu" hidden><a role="menuitem" download="Apunte.docx" href="data:application/octet-stream;base64,{data}">Descargar</a></div>'''
    await page.set_content(f'''<nav aria-label="Aplicaciones"><button>Equipos</button></nav>
      <div role="group" data-tid="team-A-team-card"><button data-testid="team-name">Materia</button></div>
      <div role="treeitem">General</div><button role="tab">Compartido</button>
      <iframe srcdoc="{html.escape(inner, quote=True)}"></iframe>''')
    refs = ReferenceStore()
    course = refs.add('materia',{'name':'Materia','dom_key':'team-A-team-card'})
    file = refs.add('archivo',{'materia_id':course,'path':[],'name':'Apunte.docx','row_key':'file-1'})
    settings = Settings(tmp_path,headless=True,timeout_ms=1500,max_file_bytes=max_bytes)
    return TeamsUI(page,settings,refs), file


async def test_download_through_sharepoint_menu_reads_document(page,tmp_path):
    ui, file = await download_ui(page,tmp_path)
    path, meta = await ui.download(file,tmp_path)
    assert path.name != 'Apunte.docx'
    assert meta['nombre'] == 'Apunte.docx'
    assert 'descargar y estudiar' in extract_document(path)['texto']


async def test_oversized_download_is_removed(page,tmp_path):
    ui, file = await download_ui(page,tmp_path,max_bytes=100)
    with pytest.raises(AppError,match='archivo_grande'):
        await ui.download(file,tmp_path)
    assert list(tmp_path.glob('*.docx')) == [tmp_path/'original.docx']


async def test_stale_file_id_does_not_download_replacement(page,tmp_path):
    ui,file=await download_ui(page,tmp_path)
    ref=ui.refs.get(file,'archivo');ref['row_key']='deleted-file-123'
    stale=ui.refs.add('archivo',ref)
    await page.frames[1].get_by_role('row').evaluate('(e)=>e.setAttribute("data-id","replacement-file-999")')
    with pytest.raises(AppError,match='referencia_desactualizada'):
        await ui.download(stale,tmp_path)


async def test_custom_checkbox_overlay_does_not_block_row_menu(page,tmp_path):
    ui,file=await download_ui(page,tmp_path)
    await page.frames[1].get_by_role('checkbox').evaluate('''e=>{
      const wrap=document.createElement('div');wrap.style='position:relative;width:24px;height:24px';e.replaceWith(wrap);wrap.append(e);
      e.style='margin:0;width:24px;height:24px';const overlay=document.createElement('span');overlay.style='position:absolute;inset:0';wrap.append(overlay);
    }''')
    path,meta=await ui.download(file,tmp_path)
    assert path.is_file()


async def test_download_waits_for_folder_rows_after_heading(page,tmp_path):
    from dataclasses import replace
    ui,file=await download_ui(page,tmp_path)
    ui.settings=replace(ui.settings,timeout_ms=4000)
    await page.frames[1].evaluate('''()=>{const g=document.querySelector('[role=grid]');const rows=g.innerHTML;g.innerHTML='<div role="row"><div role="columnheader"><button>Nombre</button></div></div>';setTimeout(()=>g.innerHTML=rows,2000);}''')
    path,meta=await ui.download(file,tmp_path)
    assert path.is_file()


async def test_folder_navigation_waits_for_rows_after_root_heading(page,tmp_path):
    from dataclasses import replace
    ui,file=await download_ui(page,tmp_path)
    ui.settings=replace(ui.settings,timeout_ms=4000)
    await page.frames[1].evaluate('''()=>{document.querySelector('[role=grid]').innerHTML='<div role="row"><div role="columnheader"><button>Nombre</button></div></div>';setTimeout(()=>{
      const b=document.createElement('button');b.textContent='Materials';b.onclick=()=>{document.querySelector('h2').textContent='Materials';document.querySelector('[role=grid]').setAttribute('aria-label','Materials');};
      document.querySelector('[role=grid]').append(b);},2000);}''')
    course=ui.refs.get(file,'archivo')['materia_id']
    frame=await ui.files_frame(course,['Materials'])
    assert await frame.get_by_role('heading',name='Materials',exact=True).is_visible()


async def test_document_cursor_returns_only_one_fragment(page,tmp_path):
    await page.route('https://teams.cloud.microsoft/',lambda route:route.fulfill(content_type='text/html',body='<nav aria-label="Aplicaciones"><button>Tareas</button></nav>'))
    await page.goto('https://teams.cloud.microsoft/')
    service=TeamsService(Settings(tmp_path,headless=True,timeout_ms=1500))
    service.session.page=page
    service.session.context=page.context
    file=service.refs.add('archivo',{'name':'Test.docx'})
    service.documents[file]={'nombre':'Test.docx','fuente':'https://example.edu/a.docx','texto':'A'*12000,'extraccion_completa':True}
    result=await service.call('leer_documento',archivo_id=file,limite_caracteres=10000)
    assert len(result['texto'])==10000
    assert 'items' not in result
    last=await service.call('leer_documento',archivo_id=file,cursor=result['cursor'])
    assert len(last['texto'])==2000 and last['cursor'] is None
    assert last['completo'] is True
