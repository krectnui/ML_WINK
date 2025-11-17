import os
from fastapi import File, UploadFile

from app.llm.full_pipeline import process_script


async def send_llm(file: UploadFile = File(...)):
    save_path = f"doc/{file.filename}"

    os.makedirs("doc", exist_ok=True)

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {
        "detail": "Все успешно загрузилось",
        "result": process_script(input_path=save_path),
    }
