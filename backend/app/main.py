from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import settings, documents, form1301

app = FastAPI(title="עוזר דוח שנתי 1301")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(form1301.router, prefix="/api")
