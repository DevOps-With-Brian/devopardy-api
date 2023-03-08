from pydantic import BaseModel
from .category import CategoryCreate
from typing import Optional


class ClueBase(BaseModel):
    answer: str
    question: str
    value: int
    category_id: int


class ClueCreate(ClueBase):
    pass


class ClueUpdate(ClueCreate):
    pass


class ClueInDB(ClueCreate):
    id: int
    answer: str
    question: str
    value: int
    category_id: Optional[int] = None

    class Config:
        orm_mode = True
