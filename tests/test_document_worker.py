import pytest
from docx import Document
from teams_facultad_mcp.documents import extract_async
from teams_facultad_mcp.core import AppError


async def test_document_worker_extracts_without_browser(tmp_path):
    file=tmp_path/'test.docx'
    doc=Document();doc.add_paragraph('Contenido del documento');doc.save(file)
    assert 'Contenido del documento' in (await extract_async(file))['texto']


async def test_document_worker_timeout_is_bounded(tmp_path):
    file=tmp_path/'test.docx'
    doc=Document();doc.add_paragraph('Contenido');doc.save(file)
    with pytest.raises(AppError,match='procesamiento_agotado'):
        await extract_async(file,timeout=.001)
