from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse

from .auth import verify_token
from .config import settings
from .renderers import (
    PdfConversionError,
    TemplateNotFoundError,
    UnsupportedTemplateError,
    convert_docx_to_pdf,
    get_template_path,
    render_docx,
    render_xlsx,
)
from .schemas import (
    BulkRenderRequest,
    BulkRenderResponse,
    RenderRequest,
    RenderResponse,
    TemplateInfo,
)
from .utils import build_output_name, ensure_dir, file_size, guess_content_type

app = FastAPI(title='Report Service', version='1.0.0')


def _storage_dir() -> Path:
    return ensure_dir(settings.report_storage_dir)


def _download_url(file_id: str) -> str:
    base_url = settings.report_base_url.rstrip('/')
    return f'{base_url}/reports/download/{file_id}'


def _find_file_by_id(file_id: str) -> Path:
    storage = _storage_dir()
    matches = list(storage.glob(f'{file_id}_*'))
    if not matches:
        raise HTTPException(status_code=404, detail='File not found')
    return matches[0]


def _response_from_file(file_id: str, stored_path: Path, output: str, template: str) -> RenderResponse:
    return RenderResponse(
        file_id=file_id,
        filename=stored_path.name.split('_', 1)[1],
        output=output,  # type: ignore[arg-type]
        content_type=guess_content_type(output),
        download_url=_download_url(file_id),
        size_bytes=file_size(stored_path),
        template=template,
    )


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/templates', response_model=list[TemplateInfo], dependencies=[Depends(verify_token)])
async def list_templates() -> list[TemplateInfo]:
    templates_dir = ensure_dir(settings.report_templates_dir)
    items: list[TemplateInfo] = []
    for path in sorted(templates_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {'.docx', '.json'}:
            items.append(TemplateInfo(name=path.name, ext=path.suffix.lower(), size_bytes=path.stat().st_size))
    return items


@app.post('/reports/render', response_model=RenderResponse, dependencies=[Depends(verify_token)])
async def render_report(payload: RenderRequest) -> RenderResponse:
    storage = _storage_dir()

    try:
        get_template_path(payload.template)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        if payload.output == 'docx':
            file_id, stored_name = build_output_name(payload.filename, 'docx')
            target = storage / stored_name
            render_docx(payload.template, payload.data, target)
            return _response_from_file(file_id, target, 'docx', payload.template)

        if payload.output == 'pdf':
            if not settings.enable_pdf:
                raise HTTPException(status_code=400, detail='PDF output is disabled')

            file_id, stored_name = build_output_name(payload.filename, 'pdf')
            target = storage / stored_name
            temp_docx = storage / f'{file_id}_{payload.filename}.docx'
            render_docx(payload.template, payload.data, temp_docx)
            await convert_docx_to_pdf(temp_docx, target)
            temp_docx.unlink(missing_ok=True)
            return _response_from_file(file_id, target, 'pdf', payload.template)

        if payload.output == 'xlsx':
            if not settings.enable_xlsx:
                raise HTTPException(status_code=400, detail='XLSX output is disabled')

            file_id, stored_name = build_output_name(payload.filename, 'xlsx')
            target = storage / stored_name
            render_xlsx(payload.template, payload.data, target)
            return _response_from_file(file_id, target, 'xlsx', payload.template)

        raise HTTPException(status_code=400, detail='Unsupported output format')
    except UnsupportedTemplateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PdfConversionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post('/reports/render-bulk', response_model=BulkRenderResponse, dependencies=[Depends(verify_token)])
async def render_bulk_reports(payload: BulkRenderRequest) -> BulkRenderResponse:
    files: list[RenderResponse] = []
    for item in payload.items:
        result = await render_report(
            RenderRequest(
                template=payload.template,
                filename=item.filename,
                data=item.data,
                output=payload.output,
            )
        )
        files.append(result)
    return BulkRenderResponse(files=files)


@app.get('/reports/download/{file_id}')
async def download_report(file_id: str) -> FileResponse:
    path = _find_file_by_id(file_id)
    ext = path.suffix.lower().lstrip('.')
    return FileResponse(path=path, filename=path.name.split('_', 1)[1], media_type=guess_content_type(ext))
