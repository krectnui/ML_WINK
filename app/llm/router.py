from fastapi import APIRouter, File, UploadFile
from app.llm.schemas import Allm
from app.llm.service import send_llm

router = APIRouter(prefix="/api/llm", tags=["API llm"])


@router.post("/send", response_model=Allm)
async def send_llm_api(file: UploadFile = File(...)):
    return await send_llm(file)
