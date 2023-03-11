from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload


from .db import get_session, init_db
from .models import Clue, Category
from .schemas.category import CategoryInDB, CategoryCreate
from .schemas.clue import ClueCreate, ClueUpdate, ClueInDB


app = FastAPI()

origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.get('/categories')
async def get_categories(count: int = 6, session: AsyncSession = Depends(get_session)):
    async with session as s:
        stmt = select(Category).order_by(Category.id).limit(count)
        result = await s.execute(stmt)
        categories = result.scalars().all()
        return categories


@app.post('/categories', response_model=CategoryInDB)
async def create_category(category: CategoryCreate, session: AsyncSession = Depends(get_session)):
    async with session as s:
        new_category = Category(name=category.name)
        s.add(new_category)
        try:
            await s.commit()
            await s.refresh(new_category)
            print(new_category.name)
            return new_category
        except IntegrityError:
            await s.rollback()
            raise HTTPException(status_code=400, detail="Category name already exists")


@app.put('/categories/{category_id}', response_model=CategoryInDB)
async def update_category(category_id: int, category: CategoryCreate, session: AsyncSession = Depends(get_session)):
    async with session as s:
        existing_category = await s.get(Category, category_id)
        if existing_category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        existing_category.name = category.name
        try:
            await s.commit()
        except IntegrityError:
            await s.rollback()
            raise HTTPException(status_code=400, detail="Category already exists")
        except Exception:
            await s.rollback()
            raise HTTPException(status_code=500, detail="Server error")
        return existing_category
    

@app.delete('/categories/{category_id}')
async def delete_category(category_id: int, session: AsyncSession = Depends(get_session)):
    async with session as s:
        existing_category = await s.get(Category, category_id)
        if existing_category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        try:
            await s.delete(existing_category)
            await s.commit()
            return {"message": "Category deleted successfully."}
        except Exception as e:
            await s.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    

@app.get('/categories/{category_id}/clues')
async def get_clues_by_category(category_id: int, session: AsyncSession = Depends(get_session)):
    async with session as s:
        stmt = select(Category).options(selectinload(Category.clues)).where(Category.id == category_id)
        result = await s.execute(stmt)
        category = result.scalar()
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return category.clues
    

@app.get('/categories/{category_id}/start_game')
async def start_game(category_id: int, session: AsyncSession = Depends(get_session)):
    async with session as s:
        clues = []
        for value in [100, 200, 300, 400, 500]:
            stmt = select(Clue).where(Clue.category_id == category_id, Clue.value == value).order_by(func.random()).limit(1)
            result = await s.execute(stmt)
            clue = result.scalar()
            if clue is None:
                raise HTTPException(status_code=404, detail=f"No clue found for category_id {category_id} and value {value}")
            clues.append(clue)
        return clues



@app.get('/clues')
async def get_clues(count: int = 6, session: AsyncSession = Depends(get_session)):
    async with session as s:
        stmt = select(Clue).order_by(func.random()).limit(count)
        result = await s.execute(stmt)
        clues = result.scalars().all()
        return clues
    

@app.post('/clues', response_model=ClueInDB)
async def create_clue(clue: ClueCreate, session: AsyncSession = Depends(get_session)):
    async with session as s:
        category = await s.get(Category, clue.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        new_clue = Clue(**clue.dict(), category=category)
        s.add(new_clue)
        try:
            await s.commit()
            await s.refresh(new_clue)
            return new_clue
        except IntegrityError:
            await s.rollback()
            raise HTTPException(status_code=400, detail="Clue already exists")


# Update an existing clue
@app.put('/clues/{clue_id}', response_model=ClueInDB)
async def update_clue(clue_id: int, clue: ClueUpdate, session: AsyncSession = Depends(get_session)):
    async with session as s:
        existing_clue = await s.get(Clue, clue_id)
        if existing_clue is None:
            raise HTTPException(status_code=404, detail="Clue not found")
        for key, value in clue.dict(exclude_unset=True).items():
            setattr(existing_clue, key, value)
        try:
            await s.commit()
        except IntegrityError:
            await s.rollback()
            raise HTTPException(status_code=400, detail="Clue value and category_id pair already exists")
        return existing_clue


# Delete an existing clue
@app.delete('/clues/{clue_id}', response_model=dict)
async def delete_clue(clue_id: int, session: AsyncSession = Depends(get_session)):
    async with session as s:
        existing_clue = await s.get(Clue, clue_id)
        if existing_clue is None:
            raise HTTPException(status_code=404, detail="Clue not found")
        await s.delete(existing_clue)
        await s.commit()
        return {"clue deleted": existing_clue.answer}