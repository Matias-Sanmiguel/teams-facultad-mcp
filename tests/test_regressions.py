import asyncio
import html
import pytest
from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from teams_facultad_mcp.core import Settings,ReferenceStore,AppError
from teams_facultad_mcp.teams import TeamsUI
from teams_facultad_mcp.documents import extract_document


def card(ident,title):
    return f'<div role="listitem" data-test="assignment-card" id="{ident}"><span data-test="assignment-card-title">{title}</span><span data-testid="card-classOrModuleName">Materia A</span></div>'


async def test_tab_switch_waits_for_new_content(page,tmp_path):
    inner=f'''<button role="tab" aria-selected="true">Upcoming</button>
      <button role="tab" aria-selected="false" onclick="this.setAttribute('aria-selected','true');setTimeout(()=>document.querySelector('[role=list]').innerHTML='{card('past','PAST TASK')}',500)">Past due</button><div role="list">{card('future','FUTURE TASK')}</div>'''
    # Put script outside an HTML attribute so nested quotes do not alter the fixture.
    inner=f'<button role="tab" aria-selected="true">Upcoming</button><button id="past" role="tab" aria-selected="false">Past due</button><div role="list">{card("future","FUTURE TASK")}</div><script>document.getElementById("past").onclick=function(){{this.setAttribute("aria-selected","true");setTimeout(()=>document.querySelector("[role=list]").innerHTML={__import__("json").dumps(card("past-task","PAST TASK"))},500);}};</script>'
    await page.set_content(f'<nav aria-label="Apps"><button>Assignments</button></nav><iframe srcdoc="{html.escape(inner,quote=True)}"></iframe>')
    ui=TeamsUI(page,Settings(tmp_path,headless=True,timeout_ms=2000),ReferenceStore())
    result=await ui.tasks('vencidas')
    assert [x['titulo'] for x in result]==['PAST TASK']


async def test_old_empty_banner_does_not_hide_new_tab_tasks(page,tmp_path):
    import json
    inner=f'<button role="tab" aria-selected="true">Upcoming</button><button id="past" role="tab" aria-selected="false">Past due</button><div id="content"><h2>No assignments yet</h2></div><script>document.getElementById("past").onclick=function(){{this.setAttribute("aria-selected","true");setTimeout(()=>document.getElementById("content").innerHTML={json.dumps(card("past-task","PAST TASK"))},500);}};</script>'
    await page.set_content(f'<nav aria-label="Apps"><button>Assignments</button></nav><iframe srcdoc="{html.escape(inner,quote=True)}"></iframe>')
    ui=TeamsUI(page,Settings(tmp_path,headless=True,timeout_ms=2000),ReferenceStore())
    assert len(await ui.tasks('vencidas'))==1


async def test_file_loading_controls_do_not_become_empty_success(page,tmp_path):
    await page.set_content('<div role="grid" aria-label="General"><div role="row"><button aria-label="Más acciones"></button></div></div>')
    ui=TeamsUI(page,Settings(tmp_path,headless=True,timeout_ms=500),ReferenceStore())
    with pytest.raises(AppError,match='interfaz_no_disponible'):
        await ui.file_rows(page,'course',[])


async def test_folder_heading_change_waits_for_matching_grid(page,tmp_path):
    await page.set_content('''<h2>Materials</h2><div role="grid" aria-label="General"><div role="row"><button>OldRoot.docx</button></div></div>
      <script>setTimeout(()=>{const g=document.querySelector('[role=grid]');g.setAttribute('aria-label','Materials');g.innerHTML='<div role="row" data-id="new"><button>NewFolder.docx</button></div>';},500);</script>''')
    ui=TeamsUI(page,Settings(tmp_path,headless=True,timeout_ms=2000),ReferenceStore())
    assert [x['nombre'] for x in await ui.file_rows(page,'course',['Materials'])]==['NewFolder.docx']


def test_pdf_aggregate_expansion_limit(tmp_path):
    file=tmp_path/'many-pages.pdf'
    writer=PdfWriter()
    for _ in range(3):
        page=writer.add_blank_page(100,100)
        content=DecodedStreamObject()
        content.set_data(b'%'+b'x'*630+b'\nBT (test) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(content)
    writer.write(file)
    with pytest.raises(AppError,match='contenido_grande'):
        extract_document(file,max_expanded_bytes=1000)


def test_text_budget_boundary_never_reports_complete(tmp_path,monkeypatch):
    from teams_facultad_mcp import documents
    monkeypatch.setattr(documents,'MAX_TEXT',10)
    doc=Document();doc.add_paragraph('12345678');doc.add_paragraph('UNREAD')
    file=tmp_path/'boundary.docx';doc.save(file)
    assert extract_document(file)['extraccion_completa'] is False


async def test_seek_restores_virtualized_target(page,tmp_path):
    await page.set_content('''<div id="scroll" style="height:100px;overflow:auto"><div style="height:1000px"><div id="rows"></div></div></div>
      <script>const s=document.getElementById('scroll');function render(){const i=Math.floor(s.scrollTop/100);document.getElementById('rows').innerHTML=`<button data-key="${i}">Item ${i}</button>`;}s.onscroll=render;render();s.scrollTop=800;</script>''')
    await page.wait_for_timeout(50)
    ui=TeamsUI(page,Settings(tmp_path,headless=True,timeout_ms=1000,scan_rounds=20),ReferenceStore())
    target=page.locator('[data-key="0"]')
    await ui.seek(page.locator('#rows button'),target)
    assert await target.count()==1


async def test_identical_course_names_are_scoped_by_selected_team(page,tmp_path):
    import json
    content_a=f'<button role="tab" aria-selected="true">Upcoming</button><div role="list">{card("task-a","Task A")}</div>'
    content_b=f'<button role="tab" aria-selected="true">Upcoming</button><div role="list">{card("task-b","Task B")}</div>'
    await page.set_content(f'''<nav aria-label="Apps"><button>Teams</button><button>Assignments</button></nav>
      <div role="group" data-tid="A-team-card"><button data-testid="team-name" onclick="window.active='A'">Materia A</button></div>
      <div role="group" data-tid="B-team-card"><button data-testid="team-name" onclick="window.active='B'">Materia A</button></div>
      <div role="treeitem">General</div><div role="treeitem" id="assignments">Assignments</div><iframe></iframe>
      <script>document.getElementById('assignments').onclick=()=>document.querySelector('iframe').srcdoc=window.active==='A'?{json.dumps(content_a)}:{json.dumps(content_b)};</script>''')
    ui=TeamsUI(page,Settings(tmp_path,headless=True,timeout_ms=1500),ReferenceStore())
    selected=ui.refs.add('materia',{'name':'Materia A','dom_key':'B-team-card'})
    assert [x['titulo'] for x in await ui.tasks('proximas',selected)]==['Task B']
