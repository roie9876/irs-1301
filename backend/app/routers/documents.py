import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.documents import (
    EXTRACTION_MODELS,
    DocumentInfo,
    DocumentListResponse,
    FieldValue,
    Form106Extraction,
    UpdateFieldsRequest,
    UploadResponse,
    UploadResult,
)
from app.services.llm import (
    classify_document,
    extract_form106_data,
    extract_form867_data,
    extract_rental_payment_data,
    extract_annual_summary_data,
    extract_receipt_data,
)
from app.services.pdf import EncryptedPdfError, extract_text_from_pdf

router = APIRouter(tags=["documents"])

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "user_data" / "documents"

SIDECAR_SUFFIX = ".doc.json"

# Map document type to extraction function
EXTRACTORS = {
    "form_106": extract_form106_data,
    "form_867": extract_form867_data,
    "rental_payment": extract_rental_payment_data,
    "annual_summary": extract_annual_summary_data,
    "receipt": extract_receipt_data,
}


def _find_sidecar(doc_id: str) -> Path | None:
    """Find sidecar file by doc_id, checking both old and new suffixes."""
    if not DOCUMENTS_DIR.exists():
        return None
    # Check new suffix first, then legacy
    for suffix in (SIDECAR_SUFFIX, ".106.json"):
        for path in DOCUMENTS_DIR.glob(f"*{suffix}"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("doc_id") == doc_id:
                    return path
            except (json.JSONDecodeError, KeyError):
                continue
    return None


def _list_sidecars() -> list[Path]:
    """List all sidecar files (new and legacy)."""
    if not DOCUMENTS_DIR.exists():
        return []
    paths = list(DOCUMENTS_DIR.glob(f"*{SIDECAR_SUFFIX}"))
    paths += [p for p in DOCUMENTS_DIR.glob("*.106.json") if not p.name.endswith(SIDECAR_SUFFIX)]
    return sorted(set(paths))


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
        for sidecar_path in _list_sidecars():
            try:
                existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
                if existing.get("original_filename") == filename:
                    existing_doc_id = existing["doc_id"]
                    sidecar_path.unlink()
                    for old_file in DOCUMENTS_DIR.glob(f"{existing_doc_id}_*"):
                        if not old_file.name.endswith(SIDECAR_SUFFIX) and not old_file.name.endswith(".106.json"):
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

            # Step 1: Classify document type
            classification = await classify_document(raw_text)
            doc_type = classification.get("document_type", "unknown")

            if doc_type not in EXTRACTORS:
                # Unknown — still save the PDF but skip extraction
                results.append(UploadResult(
                    filename=filename,
                    doc_id=doc_id,
                    status="error",
                    document_type=doc_type,
                    error=f"סוג מסמך לא נתמך: {classification.get('description', doc_type)}",
                ))
                continue

            # Step 2: Extract with type-specific extractor
            extractor = EXTRACTORS[doc_type]
            extracted_data = await extractor(raw_text)

            # Validate against pydantic model
            model_cls = EXTRACTION_MODELS[doc_type]
            extraction_obj = model_cls(**{
                k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
                for k, v in extracted_data.items()
                if k in model_cls.model_fields
            })

            sidecar_path = DOCUMENTS_DIR / f"{safe_name}{SIDECAR_SUFFIX}"
            sidecar = {
                "doc_id": doc_id,
                "original_filename": filename,
                "document_type": doc_type,
                "extracted": extraction_obj.model_dump(),
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
                document_type=doc_type,
                extracted=extraction_obj.model_dump(),
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
    documents: list[DocumentInfo] = []
    for sidecar_path in _list_sidecars():
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            doc_type = data.get("document_type", "form_106")
            documents.append(DocumentInfo(
                doc_id=data["doc_id"],
                original_filename=data["original_filename"],
                document_type=doc_type,
                extracted=data["extracted"],
                user_corrected=data.get("user_corrected", False),
            ))
        except (json.JSONDecodeError, KeyError):
            continue

    return DocumentListResponse(documents=documents)


@router.put("/documents/{doc_id}", response_model=DocumentInfo)
async def update_document(doc_id: str, body: UpdateFieldsRequest):
    sidecar_path = _find_sidecar(doc_id)
    if sidecar_path is None:
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")

    data = json.loads(sidecar_path.read_text(encoding="utf-8"))

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
        document_type=data.get("document_type", "form_106"),
        extracted=data["extracted"],
        user_corrected=True,
    )


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    sidecar_path = _find_sidecar(doc_id)
    if sidecar_path is None:
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")

    sidecar_path.unlink()

    # Remove the PDF file too
    for pdf_path in DOCUMENTS_DIR.glob(f"{doc_id}_*"):
        if not pdf_path.name.endswith(SIDECAR_SUFFIX) and not pdf_path.name.endswith(".106.json"):
            pdf_path.unlink()

    return {"ok": True}
