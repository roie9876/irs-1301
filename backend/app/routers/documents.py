import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.schemas.documents import (
    EXTRACTION_MODELS,
    ChildInfo,
    DocumentInfo,
    DocumentListResponse,
    FieldValue,
    Form106Extraction,
    IdSupplementExtraction,
    UpdateFieldsRequest,
    UploadResponse,
    UploadResult,
)
from app.services.llm import (
    classify_document,
    classify_document_vision,
    extract_form106_data,
    extract_form867_data,
    extract_rental_payment_data,
    extract_annual_summary_data,
    extract_receipt_data,
    extract_receipt_data_vision,
    extract_life_insurance_data,
    extract_id_supplement_data,
)
from app.services.pdf import EncryptedPdfError, extract_text_from_pdf, render_pdf_page_to_image
from app.services.excel import extract_rental_excel

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
    "life_insurance": extract_life_insurance_data,
}


def _normalize_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _normalize_name(value: str) -> str:
    return " ".join(value.split()).strip()


def _sanitize_id_supplement_extraction(extracted_data: dict) -> tuple[dict, list[ChildInfo], list[str]]:
    sanitized = dict(extracted_data)
    children_raw = sanitized.pop("children", [])
    children = [ChildInfo(**child) for child in children_raw if isinstance(child, dict)]
    warnings: list[str] = []

    child_ids = {_normalize_digits(child.id_number) for child in children if child.id_number}
    child_names = {_normalize_name(child.name) for child in children if child.name}

    spouse_id = _normalize_digits(str(sanitized.get("spouse_id", {}).get("value", ""))) if isinstance(sanitized.get("spouse_id"), dict) else ""
    spouse_name = _normalize_name(str(sanitized.get("spouse_name", {}).get("value", ""))) if isinstance(sanitized.get("spouse_name"), dict) else ""

    if (spouse_id and spouse_id in child_ids) or (spouse_name and spouse_name in child_names):
        sanitized["spouse_name"] = {"value": None, "confidence": 0.0}
        sanitized["spouse_id"] = {"value": None, "confidence": 0.0}
        sanitized["spouse_birth_date"] = {"value": None, "confidence": 0.0}
        warnings.append("זיהוי בן/בת הזוג בספח בוטל כי הערכים התאימו לאחד הילדים")

    return sanitized, children, warnings


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


async def _reextract_document_sidecar(sidecar_path: Path) -> dict:
    data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    doc_id = data["doc_id"]
    document_type = data.get("document_type", "unknown")
    filename = data.get("original_filename", "?")

    if document_type not in EXTRACTORS and document_type != "id_supplement":
        return {"doc_id": doc_id, "filename": filename, "status": "skipped", "reason": f"no extractor for {document_type}"}

    if data.get("user_corrected"):
        return {"doc_id": doc_id, "filename": filename, "status": "skipped", "reason": "user_corrected"}

    source_path = None
    for candidate in DOCUMENTS_DIR.glob(f"{doc_id}_*"):
        if candidate.name.endswith(SIDECAR_SUFFIX) or candidate.name.endswith(".106.json"):
            continue
        source_path = candidate
        break

    if source_path is None or not source_path.exists():
        return {"doc_id": doc_id, "filename": filename, "status": "error", "reason": "PDF not found"}

    model_cls = EXTRACTION_MODELS[document_type]

    if document_type == "id_supplement":
        image_bytes = source_path.read_bytes()
        extracted_data = await extract_id_supplement_data(image_bytes, source_path.name)
        extracted_data, children, extraction_warnings = _sanitize_id_supplement_extraction(extracted_data)
        extraction_obj = IdSupplementExtraction(
            **{
                k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
                for k, v in extracted_data.items()
                if k in IdSupplementExtraction.model_fields and k != "children"
            },
            children=children,
        )
    else:
        raw_text = extract_text_from_pdf(str(source_path))
        if not raw_text.strip():
            return {"doc_id": doc_id, "filename": filename, "status": "error", "reason": "empty text"}

        extractor = EXTRACTORS[document_type]
        extracted_data = await extractor(raw_text)
        extraction_warnings = []
        extraction_obj = model_cls(**{
            k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
            for k, v in extracted_data.items()
            if k in model_cls.model_fields
        })

    data["extracted"] = extraction_obj.model_dump()
    data["extraction_warnings"] = extraction_warnings
    sidecar_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"doc_id": doc_id, "filename": filename, "status": "success", "warnings": extraction_warnings}


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    passwords: str = Form("{}"),
    tax_year: str = Form(""),
):
    upload_tax_year = int(tax_year) if tax_year.strip() else None
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[UploadResult] = []

    file_passwords: dict[str, str] = {}
    try:
        file_passwords = json.loads(passwords)
    except json.JSONDecodeError:
        pass

    for file in files:
        filename = file.filename or "unknown.pdf"

        is_pdf = filename.lower().endswith(".pdf")
        is_xlsx = filename.lower().endswith(".xlsx")
        is_image = filename.lower().rsplit(".", 1)[-1] in ("jpg", "jpeg", "png", "webp") if "." in filename.lower() else False

        if not is_pdf and not is_xlsx and not is_image:
            results.append(UploadResult(
                filename=filename,
                status="error",
                error="הקובץ אינו PDF, Excel או תמונה תקינה",
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

            if is_xlsx:
                # Excel files: direct programmatic extraction, no LLM needed
                doc_type = "rental_excel"
                extracted_data = extract_rental_excel(str(file_path))

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
                if upload_tax_year is not None:
                    sidecar["upload_tax_year"] = upload_tax_year
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
                continue

            if is_image:
                # Image files: treat as ID supplement (ספח תעודת זהות)
                doc_type = "id_supplement"
                extracted_data = await extract_id_supplement_data(content, filename)
                extracted_data, children, extraction_warnings = _sanitize_id_supplement_extraction(extracted_data)

                extraction_obj = IdSupplementExtraction(
                    **{
                        k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
                        for k, v in extracted_data.items()
                        if k in IdSupplementExtraction.model_fields and k != "children"
                    },
                    children=children,
                )

                sidecar_path = DOCUMENTS_DIR / f"{safe_name}{SIDECAR_SUFFIX}"
                sidecar = {
                    "doc_id": doc_id,
                    "original_filename": filename,
                    "document_type": doc_type,
                    "extracted": extraction_obj.model_dump(),
                    "user_corrected": False,
                }
                if upload_tax_year is not None:
                    sidecar["upload_tax_year"] = upload_tax_year
                if extraction_warnings:
                    sidecar["extraction_warnings"] = extraction_warnings
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
                continue

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

            # Step 1: Classify document type (text-based, with filename hint)
            classification = await classify_document(raw_text, filename)
            doc_type = classification.get("document_type", "unknown")

            # Vision fallback: if text-based classification failed, render
            # the first page as an image and classify visually
            page_image = None
            if doc_type not in EXTRACTORS:
                try:
                    page_image = render_pdf_page_to_image(str(file_path))
                    vision_cls = await classify_document_vision(page_image, filename)
                    vision_type = vision_cls.get("document_type", "unknown")
                    if vision_type in EXTRACTORS:
                        doc_type = vision_type
                        classification = vision_cls
                except Exception:
                    pass

            if doc_type not in EXTRACTORS:
                # Not a source document — skip gracefully
                desc = classification.get('description', doc_type)
                results.append(UploadResult(
                    filename=filename,
                    doc_id=doc_id,
                    status="skipped",
                    document_type=doc_type,
                    error=f"סוג מסמך לא נתמך: {desc}. זה לא אחד מסוגי המסמכים הנתמכים ברשימה.",
                ))
                continue

            # Step 2: Extract with type-specific extractor
            # If vision was needed for classification, the text is garbled —
            # use vision-based extraction for supported types
            if page_image is not None and doc_type == "receipt":
                extracted_data = await extract_receipt_data_vision(page_image)
            else:
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
            if upload_tax_year is not None:
                sidecar["upload_tax_year"] = upload_tax_year
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
                extraction_warnings=data.get("extraction_warnings", []),
                upload_tax_year=data.get("upload_tax_year"),
            ))
        except (json.JSONDecodeError, KeyError):
            continue

    return DocumentListResponse(documents=documents)


@router.get("/documents/{doc_id}/file")
async def get_document_file(doc_id: str):
    """Serve the original uploaded document file (PDF/image)."""
    if not DOCUMENTS_DIR.exists():
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")
    # Find file matching doc_id prefix (excluding sidecars)
    for path in DOCUMENTS_DIR.iterdir():
        if path.name.startswith(f"{doc_id}_") and not path.name.endswith(SIDECAR_SUFFIX):
            media_types = {
                ".pdf": "application/pdf",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            suffix = path.suffix.lower()
            media_type = media_types.get(suffix, "application/octet-stream")
            return FileResponse(path, media_type=media_type)
    raise HTTPException(status_code=404, detail="קובץ מסמך לא נמצא")


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
        extraction_warnings=data.get("extraction_warnings", []),
    )


@router.post("/documents/{doc_id}/reextract", response_model=DocumentInfo)
async def reextract_document(doc_id: str):
    sidecar_path = _find_sidecar(doc_id)
    if sidecar_path is None:
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")

    result = await _reextract_document_sidecar(sidecar_path)
    if result["status"] == "skipped":
        raise HTTPException(status_code=400, detail=f"לא ניתן לחלץ מחדש: {result['reason']}")
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=f"חילוץ מחדש נכשל: {result['reason']}")

    data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    return DocumentInfo(
        doc_id=data["doc_id"],
        original_filename=data["original_filename"],
        document_type=data.get("document_type", "form_106"),
        extracted=data["extracted"],
        user_corrected=data.get("user_corrected", False),
        extraction_warnings=data.get("extraction_warnings", []),
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


@router.post("/documents/reextract-all")
async def reextract_all_documents(doc_type: str | None = None):
    """Re-extract all PDF documents using updated prompts. Skips user-corrected docs.
    Optional doc_type filter: 'form_106', 'form_867', etc.
    """
    results: list[dict] = []
    for sidecar_path in _list_sidecars():
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            continue

        doc_id = data["doc_id"]
        document_type = data.get("document_type", "unknown")
        filename = data.get("original_filename", "?")

        if doc_type and document_type != doc_type:
            results.append({"doc_id": doc_id, "filename": filename, "status": "skipped", "reason": f"type {document_type} != {doc_type}"})
            continue

        if data.get("user_corrected"):
            results.append({"doc_id": doc_id, "filename": filename, "status": "skipped", "reason": "user_corrected"})
            continue

        if document_type not in EXTRACTORS and document_type != "id_supplement":
            results.append({"doc_id": doc_id, "filename": filename, "status": "skipped", "reason": f"no extractor for {document_type}"})
            continue

        # Find the source PDF
        pdf_path = None
        for candidate in DOCUMENTS_DIR.glob(f"{doc_id}_*"):
            if candidate.name.endswith(SIDECAR_SUFFIX) or candidate.name.endswith(".106.json"):
                continue
            pdf_path = candidate
            break

        if pdf_path is None or not pdf_path.exists():
            results.append({"doc_id": doc_id, "filename": filename, "status": "error", "reason": "PDF not found"})
            continue

        try:
            model_cls = EXTRACTION_MODELS[document_type]

            if document_type == "id_supplement":
                image_bytes = pdf_path.read_bytes()
                extracted_data = await extract_id_supplement_data(image_bytes, pdf_path.name)
                extracted_data, children, extraction_warnings = _sanitize_id_supplement_extraction(extracted_data)
                extraction_obj = IdSupplementExtraction(
                    **{
                        k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
                        for k, v in extracted_data.items()
                        if k in IdSupplementExtraction.model_fields and k != "children"
                    },
                    children=children,
                )
            else:
                raw_text = extract_text_from_pdf(str(pdf_path))
                if not raw_text.strip():
                    results.append({"doc_id": doc_id, "filename": filename, "status": "error", "reason": "empty text"})
                    continue

                extractor = EXTRACTORS[document_type]
                extracted_data = await extractor(raw_text)

                extraction_obj = model_cls(**{
                    k: FieldValue(**v) if isinstance(v, dict) else FieldValue()
                    for k, v in extracted_data.items()
                    if k in model_cls.model_fields
                })

            old_extracted = data.get("extracted", {})
            outcome = await _reextract_document_sidecar(sidecar_path)
            if outcome["status"] != "success":
                results.append(outcome)
                continue

            refreshed = json.loads(sidecar_path.read_text(encoding="utf-8"))
            diffs = []
            for field, new_val in refreshed["extracted"].items():
                old_val = old_extracted.get(field, {}).get("value") if isinstance(old_extracted.get(field), dict) else None
                val = new_val.get("value") if isinstance(new_val, dict) else None
                if old_val != val:
                    diffs.append(field)

            results.append({"doc_id": doc_id, "filename": filename, "status": "reextracted", "changed_fields": diffs, "warnings": refreshed.get("extraction_warnings", [])})
        except Exception as e:
            results.append({"doc_id": doc_id, "filename": filename, "status": "error", "reason": str(e)})
