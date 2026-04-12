from __future__ import annotations

from pydantic import BaseModel


class AdvisorItem(BaseModel):
    title: str
    detail: str
    level: str = "info"


class AdvisorQuestionRequest(BaseModel):
    question: str
    tax_year: int
    source_documents: list[str] = []
    warnings: list[str] = []
    advisor_items: list[AdvisorItem] = []
    current_section: str = ""
    current_field_label: str = ""
    current_field_explanation: str = ""
    balance: float = 0
    net_tax: float = 0


class AdvisorAnswerResponse(BaseModel):
    answer: str


class ChatRequest(BaseModel):
    question: str
    tax_year: int
    form_summary: str = ""
    source_documents: list[str] = []
    warnings: list[str] = []
    balance: float = 0
    net_tax: float = 0
