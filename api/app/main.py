from fastapi import Depends, FastAPI
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db import get_session, init_db
from app.models import Clue, ClueCreate

app = FastAPI()


@app.get("/status")
async def status():
    return {"status": "ok"}


@app.get("/clues", response_model=List[Clue])
async def get_clues(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Clue))
    clues = result.scalars().all()
    return [Clue(answer=clue.answer, question=clue.question, value=clue.value, id=clue.id) for clue in clues]

@app.post("/clues")
async def add_clue(clue: ClueCreate, session: AsyncSession = Depends(get_session)):
    clue = Clue(answer=clue.answer, question=clue.question, value=clue.value)
    session.add(clue)
    await session.commit()
    await session.refresh(clue)
    return clue