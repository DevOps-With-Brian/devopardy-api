from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str


class CategoryInDB(CategoryCreate):
    id: int

    class Config:
        orm_mode = True
