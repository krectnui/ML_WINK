from pydantic import BaseModel


class Allm(BaseModel):
    detail: str
    result: dict