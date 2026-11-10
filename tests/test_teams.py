import pytest
from teams_facultad_mcp.teams import TeamsUI
from teams_facultad_mcp.core import Settings, ReferenceStore, AppError


async def ui_for(page, tmp_path, body):
    await page.set_content(body)
    return TeamsUI(page, Settings(tmp_path, headless=True, timeout_ms=1500, scan_rounds=3), ReferenceStore())


async def test_spanish_courses_have_stable_distinct_refs(page, tmp_path):
    ui = await ui_for(page, tmp_path, '''<nav aria-label="Aplicaciones"><button>Equipos</button></nav>
      <div role="group" data-tid="team-A-team-card" aria-label="Materia A Equipo 1 de 2"><button data-testid="team-name">Materia A</button><button>Tareas</button></div>
      <div role="group" data-tid="team-B-team-card" aria-label="Materia A Equipo 2 de 2"><button data-testid="team-name">Materia A</button><button>Tareas</button></div>''')
    result = await ui.courses()
    assert len(result) == 2
    assert result[0]['id'] != result[1]['id']
    assert all(x['nombre'] == 'Materia A' for x in result)


@pytest.mark.parametrize('status,label', [('proximas','Próximamente'),('vencidas','Vencida'),('completadas','Completado')])
async def test_assignments_in_iframe_by_status(page, tmp_path, status, label):
    ui = await ui_for(page, tmp_path, f'''<nav aria-label="Aplicaciones"><button>Tareas</button></nav>
      <iframe srcdoc='<main><div role="tablist"><button role="tab">{label}</button></div>
      <div role="list" data-test="assignment-list"><div role="group" aria-label="20 nov viernes">
      <div role="listitem" id="assignment-1" data-test="assignment-card"><span data-test="assignment-card-title-all-up-view">TPO</span><div data-testid="card-classOrModuleName">Materia A</div><span>Vence el 23:00</span></div>
      </div></div></main>'></iframe>''')
    result = await ui.tasks(status)
    assert result[0]['titulo'] == 'TPO'
    assert result[0]['materia'] == 'Materia A'
    assert '20 nov' in result[0]['fecha_original']
    assert result[0]['estado_lista'] == status


async def test_english_empty_assignments_are_not_loading(page, tmp_path):
    ui = await ui_for(page, tmp_path, '''<nav aria-label="Apps"><button>Assignments</button></nav>
      <iframe srcdoc='<main><button role="tab">Upcoming</button><h2>No assignments yet</h2></main>'></iframe>''')
    assert await ui.tasks('proximas') == []


async def test_loading_frame_is_error_not_empty_success(page, tmp_path):
    ui = await ui_for(page, tmp_path, '''<nav aria-label="Apps"><button>Assignments</button></nav><iframe srcdoc='<p>Loading...</p>'></iframe>''')
    with pytest.raises(AppError, match='interfaz_no_disponible'):
        await ui.tasks('proximas')


async def test_task_detail_excludes_submit_and_attach_controls(page, tmp_path):
    ui = await ui_for(page, tmp_path, '''<main><h1>Trabajo práctico</h1><span>Vence el 20 de noviembre de 2026 23:00</span>
      <span>No entregada</span><h2>Instrucciones</h2><p>Entrega el capitán del equipo</p><button>Entregar</button><h2>Mi trabajo</h2><button>Adjuntar</button></main>''')
    result = await ui.task_detail(page)
    assert result['titulo'] == 'Trabajo práctico'
    assert 'capitán' in result['instrucciones']
    assert 'Entregar' not in result['instrucciones']
    assert '2026' in result['vencimiento_original']
    assert result['estado'] == 'No entregada'


async def test_file_rows_preserve_folder_and_duplicate_names(page, tmp_path):
    ui = await ui_for(page, tmp_path, '''<div role="grid" aria-label="General"><div role="row"><span role="columnheader">Nombre</span></div>
      <div role="row" data-id="folder-1"><span role="gridcell"><img aria-label="Amarillo carpeta"></span><span role="gridcell"><button>Materiales</button></span></div>
      <div role="row" data-id="file-1"><span role="gridcell"><img aria-label=".docx"></span><span role="gridcell" data-automationid="field-LinkFilename"><span role="button" data-id="heroField">Apunte.docx</span><button aria-label="Más acciones"></button><button aria-label="Agregar acceso directo a OneDrive"></button></span><span role="gridcell">10 nov</span></div></div>''')
    result = await ui.file_rows(page, 'materia_a', [])
    assert [x['tipo'] for x in result] == ['carpeta','archivo']
    assert result[1]['nombre'] == 'Apunte.docx'
    assert ui.refs.get(result[0]['id'], 'carpeta')['path'] == ['Materiales']


async def test_posts_read_author_date_and_body_without_replying(page, tmp_path):
    ui = await ui_for(page, tmp_path, '''<div id="reply-chain-summary-1"><div id="message-body-1"><span data-tid="message-author-name">Docente</span><time datetime="2026-11-09T18:00:00-03:00">Ayer 18:00</time><h2>Entrega</h2><div id="content-1">El TPO vence el viernes</div><button>Responder</button></div></div>''')
    result = await ui.post_rows()
    assert result[0]['autor'] == 'Docente'
    assert 'viernes' in result[0]['texto']
    assert result[0]['fecha_original']


async def test_invalid_task_reference_never_navigates(page, tmp_path):
    ui = await ui_for(page, tmp_path, '<h1>Hola</h1>')
    with pytest.raises(AppError, match='referencia_invalida'):
        await ui.task('https://evil.example')
    assert page.url == 'about:blank'


async def test_file_rows_wait_for_async_rows(page, tmp_path):
    ui = await ui_for(page, tmp_path, '''<div role="grid" aria-label="General"><div role="row"><span role="columnheader"><button>Nombre</button></span></div></div><script>
      setTimeout(()=>document.querySelector('[role=grid]').innerHTML='<div role="row"><span role="gridcell"><img aria-label=".pdf"></span><span role="gridcell"><button>Apunte.pdf</button></span></div>',250);
      </script>''')
    result = await ui.file_rows(page, 'course', [])
    assert len(result) == 1 and result[0]['nombre'] == 'Apunte.pdf'


async def test_unloaded_files_are_not_empty_success(page, tmp_path):
    ui = await ui_for(page, tmp_path, '<div role="grid" aria-label="General"></div>')
    with pytest.raises(AppError, match='interfaz_no_disponible'):
        await ui.file_rows(page, 'course', [])
