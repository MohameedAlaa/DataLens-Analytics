from fastapi import FastAPI

from api.chat import router as chat_router
from api.filter import router as filter_router
from api.upload import router as upload_router

app = FastAPI()

@app.get("/")
async def index():
    return {
        "message": "DataLens Analytics API"
    }

app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(filter_router, prefix="/filter", tags=["filter"])
app.include_router(upload_router, prefix="/upload", tags=["upload"])