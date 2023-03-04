from sqlmodel import SQLModel, Field


class ClueBase(SQLModel):
    answer: str
    question: str
    value: int


class Clue(ClueBase, table=True):
    id: int = Field(default=None, primary_key=True)


class ClueCreate(ClueBase):
    pass