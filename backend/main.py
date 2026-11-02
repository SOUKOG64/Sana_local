"""FastAPI: API для основной сущности «Фехтовальщик» + авторизация.

Запуск:  uvicorn main:app --reload
Swagger: http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import crud
from database import Base, SessionLocal, engine, get_db
from models import User
from schemas import FighterCreate, FighterOut, FighterUpdate, Token, UserCreate, UserLogin
from security import create_token, get_current_user, verify_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        crud.seed(db)
    yield


app = FastAPI(
    title="Арт-Фехтование API",
    description="REST API для учёта фехтовальщиков. Защищённые методы требуют JWT "
                "(кнопка Authorize в Swagger → вставить токен из /api/auth/login).",
    version="1.0",
    lifespan=lifespan,
)


# ---------- обработка ошибок (400, 401, 404, 500) ----------
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"] if x not in ("body", "query", "path"))
        parts.append(f"{loc}: {err['msg']}" if loc else err["msg"])
    return JSONResponse(status_code=400, content={"detail": "; ".join(parts)})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


# ---------- авторизация ----------
@app.post("/api/auth/register", response_model=Token, status_code=201, tags=["Auth"],
          responses={400: {"description": "Некорректные данные или email занят"}})
def register(data: UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    user = crud.create_user(db, data.email, data.password)
    return Token(access_token=create_token(user.id), email=user.email)


@app.post("/api/auth/login", response_model=Token, tags=["Auth"],
          responses={401: {"description": "Неверный email или пароль"}})
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return Token(access_token=create_token(user.id), email=user.email)


# ---------- фехтовальщики: полный CRUD ----------
@app.get("/api/fighters", response_model=List[FighterOut], tags=["Fighters"])
def list_fighters(
    search: Optional[str] = Query(None, description="Поиск по имени или клубу"),
    weapon: Optional[str] = Query(None, description="Фильтр по оружию"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.list_fighters(db, search, weapon)


@app.get("/api/fighters/{fighter_id}", response_model=FighterOut, tags=["Fighters"],
         responses={404: {"description": "Фехтовальщик не найден"}})
def get_fighter(fighter_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    fighter = crud.get_fighter(db, fighter_id)
    if fighter is None:
        raise HTTPException(status_code=404, detail="Фехтовальщик не найден")
    return fighter


@app.post("/api/fighters", response_model=FighterOut, status_code=201, tags=["Fighters"])
def create_fighter(data: FighterCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    return crud.create_fighter(db, data, user)


@app.patch("/api/fighters/{fighter_id}", response_model=FighterOut, tags=["Fighters"],
           responses={404: {"description": "Фехтовальщик не найден"}})
def update_fighter(fighter_id: int, data: FighterUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    fighter = crud.get_fighter(db, fighter_id)
    if fighter is None:
        raise HTTPException(status_code=404, detail="Фехтовальщик не найден")
    return crud.update_fighter(db, fighter, data)


@app.delete("/api/fighters/{fighter_id}", status_code=204, tags=["Fighters"],
            responses={404: {"description": "Фехтовальщик не найден"}})
def delete_fighter(fighter_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    fighter = crud.get_fighter(db, fighter_id)
    if fighter is None:
        raise HTTPException(status_code=404, detail="Фехтовальщик не найден")
    crud.delete_fighter(db, fighter)
    return Response(status_code=204)
