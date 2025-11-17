from fastapi import FastAPI

from app.llm.router import router as llm_router


app = FastAPI()


app.include_router(llm_router)
