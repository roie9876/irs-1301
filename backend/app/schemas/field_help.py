from __future__ import annotations

from pydantic import BaseModel


class FieldHelpResponse(BaseModel):
    code: str
    title: str
    description: str
    part_id: str = ""
    part_name_he: str = ""
    section_num: int | None = None
    section_name_he: str = ""
    guide_line: int | None = None
    tax_rate: str = ""
    notes: list[str] = []
