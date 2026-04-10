import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.documents import (
    DocumentInfo,
    DocumentListResponse,
    FieldValue,
    Form106Extraction,
    UpdateFieldsRequest,
    UploadResponse,
    UploadResult,
)
from app.services.llm import extract_form106_data
from app.services.pdf import EncryptedPdfError, extract_text_from_pdf

router = APIRouter(tags=["documents"])

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "user_data" / "documents"


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    passwords: str = Form("{}"),
):
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[UploadResult] = []

    file_passwords: dict[str, str] = {}
    try:
        file_passwords = json.loads(passwords)
    except json.JSONDecodeError:
        pass

    for file in files:
        filename = file.filename or "unknown.pdf"

        if not filename.lower().endswith(".pdf"):
            results.append(UploadResult(
                filename=filename,
                status="error",
                error="הקובץ אינו PDF תקין",
            ))
            continue

        # Check for existing upload with same filename — reuse its doc_id
        existing_doc_id = None
        for sidecar_path in DOCUMENTS_DIR.glob("*.106.json"):
            try:
                existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
                if existing.get("original_filename") == filename:
                    existing_doc_id = existing["doc_id"]
                    # Remove old files to replace with new upload
                    sidecar_path.unlink()
                    for old_file in DOCUMENTS_DIR.glob(f"{existing_doc_id}_*"):
                        if not old_file.name.endswith(".106.json"):
                            old_file.unlink()
                    break
            except (json.JSONDecodeError, KeyError):
                continue

        doc_id = existing_doc_id or uuid.uuid4().hex[:8]
        safe_name = f"{doc_id}_{filename}"
        file_path = DOCUMENTS_DIR / safe_name

        try:
            content = await file.read()
            file_path.write_bytes(content)

            password = file_passwords.get(filename, "")
            raw_text = extract_text_from_pdf(str(file_path), password=password)
            if not raw_text.strip():
                results.append(UploadResult(
                    filename=filename,
                    doc_id=doc_id,
                    status="error",
                    error="לא ניתן לחלץ טקסט מהקובץ",
                ))
                continue

            extracted_data = await extract_form106_data(raw_text)
            extraction = Form106Extraction(**{
                k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
                for k, v in extracted_data.items()
                if k in Form106Extraction.model_fields
            })

            sidecar_path = DOCUMENTS_DIR / f"{safe_name}.106.json"
            sidecar = {
                "doc_id": doc_id,
                "original_filename": filename,
                "extracted": extraction.model_dump(),
                "user_corrected": False,
            }
            sidecar_path.write_text(
                json.dumps(sidecar, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            results.append(UploadResult(
                filename=filename,
                doc_id=doc_id,
                status="success",
                extracted=extraction,
            ))
        except EncryptedPdfError:
            results.append(UploadResult(
                filename=filename,
                doc_id=doc_id,
                status="encrypted",
                error="הקובץ מוגן בסיסמה",
            ))
        except Exception as e:
            results.append(UploadResult(
                filename=filename,
                doc_id=doc_id,
                status="error",
                error=f"שגיאה בחילוץ: {e}",
            ))

    return UploadResponse(results=results)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    if not DOCUMENTS_DIR.exists():
        return DocumentListResponse(documents=[])

    documents: list[DocumentInfo] = []
    for sidecar_path in sorted(DOCUMENTS_DIR.glob("*.106.json")):
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            documents.append(DocumentInfo(
                doc_id=data["doc_id"],
                original_filename=data["original_filename"],
                extracted=Form106Extraction(**{
                    k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
                    for k, v in data["extracted"].items()
                    if k in Form106Extraction.model_fields
                }),
                user_corrected=data.get("user_corrected", False),
            ))
        except (json.JSONDecodeError, KeyError):
            continue

    return DocumentListResponse(documents=documents)


@router.put("/documents/{doc_id}", response_model=DocumentInfo)
async def update_document(doc_id: str, body: UpdateFieldsRequest):
    if not DOCUMENTS_DIR.exists():
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")

    sidecar_path = None
    for path in DOCUMENTS_DIR.glob("*.106.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("doc_id") == doc_id:
                sidecar_path = path
                break
        except (json.JSONDecodeError, KeyError):
            continue

    if sidecar_path is None:
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")

    for field_name, field_value in body.fields.items():
        if field_name in data["extracted"]:
            data["extracted"][field_name] = field_value.model_dump()

    data["user_corrected"] = True
    sidecar_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return DocumentInfo(
        doc_id=data["doc_id"],
        original_filename=data["original_filename"],
        extracted=Form106Extraction(**{
            k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
            for k, v in data["extracted"].items()
            if k in Form106Extraction.model_fields
        }),
        user_corrected=True,
    )


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if not DOCUMENTS_DIR.exists():
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")

    found = False
    for path in DOCUMENTS_DIR.glob("*.106.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("doc_id") == doc_id:
                path.unlink()
                found = True
                break
        except (json.JSONDecodeError, KeyError):
            continue

    if not found:
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")

    # Remove the PDF file too
    for pdf_path in DOCUMENTS_DIR.glob(f"{doc_id}_*"):
        if not pdf_path.name.endswith(".106.json"):
            pdf_path.unlink()

    return {"ok": True}
