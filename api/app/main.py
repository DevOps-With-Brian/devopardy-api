from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import os


from .db import get_session, init_db
from .models import Clue, Category
from .schemas.category import CategoryInDB, CategoryCreate
from .schemas.clue import ClueCreate, ClueUpdate, ClueInDB


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://devopardy-ui:3000",
    "http://devopardy-ui:80",
    "https://devopardy.devopswithbrian.com"
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

# Password hash context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 password bearer flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Hard-coded admin credentials (for demo purposes only)
ADMIN_USERNAME = os.getenv("ADMIN_API_USERNAME")
ADMIN_PASSWORD_HASH = pwd_context.hash(os.getenv("ADMIN_API_USERNAME"))


# Verify user credentials
def verify_user(username: str, password: str):
    if username == ADMIN_USERNAME and pwd_context.verify(password, ADMIN_PASSWORD_HASH):
        return True
    else:
        return False


# Define a function to check if the current user is an admin
def get_admin_user(current_user: str = Depends(oauth2_scheme)):
    try:
        # Decode the JWT token to get the payload
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        # Extract the 'sub' claim (username) from the payload
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check if the user is an admin
    if username != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return username


# Authenticate user and generate access token
def authenticate_user(username: str, password: str):
    if verify_user(username, password):
        access_token_expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token_payload = {"sub": username, "exp": access_token_expires}
        access_token = jwt.encode(access_token_payload, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=400, detail="Incorrect username or password")


# Login endpoint
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return authenticate_user(form_data.username, form_data.password)


# Protected endpoint
@app.get("/admin-only")
async def admin_only(current_user: str = Depends(oauth2_scheme)):
    try:
        # Decode the JWT token to get the payload
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        # Extract the 'sub' claim (username) from the payload
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")
    if username != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Not authorized")
    else:
        return {"message": "Hello, admin!"}
    

@app.get('/categories')
async def get_categories(count: int = 6, session: AsyncSession = Depends(get_session)):
    async with session as s:
        stmt = select(Category).order_by(Category.id).limit(count)
        result = await s.execute(stmt)
        categories = result.scalars().all()
        return categories


@app.get('/categories/{category_id}')
async def get_category(category_id: int, session: AsyncSession = Depends(get_session)):
    async with session as s:
        stmt = select(Category).where(Category.id == category_id)
        result = await s.execute(stmt)
        category = result.scalar()
        if category is None:
            raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
        return category


@app.post('/categories', response_model=List[CategoryInDB])
async def create_categories(categories: List[CategoryCreate], session: AsyncSession = Depends(get_session), current_user: str = Depends(get_admin_user)):
    async with session as s:
        new_categories = []
        for category in categories:
            new_category = Category(name=category.name)
            s.add(new_category)
            try:
                await s.commit()
                await s.refresh(new_category)
                new_categories.append(new_category)
            except IntegrityError:
                await s.rollback()
                raise HTTPException(status_code=400, detail="Category name already exists")
        return new_categories


@app.put('/categories/{category_id}', response_model=CategoryInDB)
async def update_category(category_id: int, category: CategoryCreate, session: AsyncSession = Depends(get_session), current_user: str = Depends(get_admin_user)):
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
async def delete_category(category_id: int, session: AsyncSession = Depends(get_session), current_user: str = Depends(get_admin_user)):
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
    


@app.get('/categories/{category_id}/start_game')
async def start_game(category_id: int, session: AsyncSession = Depends(get_session)):
    async with session as s:
        clues = []
        for value in [100, 200, 300, 400, 500]:
            stmt = select(Clue).join(Category).filter(Clue.category_id == category_id, Clue.value == value).order_by(func.random()).limit(1)
            result = await s.execute(stmt)
            clue = result.scalar()
            if clue is None:
                raise HTTPException(status_code=404, detail=f"No clue found for category_id {category_id} and value {value}")
            clues.append(clue)
        return clues



@app.get('/clues')
async def get_clues(count: int = 6, session: AsyncSession = Depends(get_session), current_user: str = Depends(get_admin_user)):
    async with session as s:
        stmt = select(Clue).order_by(func.random()).limit(count)
        result = await s.execute(stmt)
        clues = result.scalars().all()
        return clues
    

@app.post('/clues', response_model=List[ClueInDB])
async def create_clues(clues: List[ClueCreate], session: AsyncSession = Depends(get_session), current_user: str = Depends(get_admin_user)):
    created_clues = []
    async with session as s:
        for clue in clues:
            category = await s.get(Category, clue.category_id)
            if category is None:
                raise HTTPException(status_code=404, detail="Category not found")
            new_clue = Clue(**clue.dict(), category=category)
            s.add(new_clue)
            try:
                await s.commit()
                await s.refresh(new_clue)
                created_clues.append(new_clue)
            except IntegrityError:
                await s.rollback()
                raise HTTPException(status_code=400, detail="Clue already exists")
    return created_clues


# Update an existing clue
@app.put('/clues/{clue_id}', response_model=ClueInDB)
async def update_clue(clue_id: int, clue: ClueUpdate, session: AsyncSession = Depends(get_session), current_user: str = Depends(get_admin_user)):
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
async def delete_clue(clue_id: int, session: AsyncSession = Depends(get_session), current_user: str = Depends(get_admin_user)):
    async with session as s:
        existing_clue = await s.get(Clue, clue_id)
        if existing_clue is None:
            raise HTTPException(status_code=404, detail="Clue not found")
        await s.delete(existing_clue)
        await s.commit()
        return {"clue deleted": existing_clue.answer}