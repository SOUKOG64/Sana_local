"""Pydantic-схемы запросов и ответов (JSON)."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Weapon = Literal["рапира", "сабля", "шпага", "меч", "кинжал"]
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserCreate(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=120)
    password: str = Field(min_length=6, max_length=64)


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


class FighterCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    weapon: Weapon
    club: Optional[str] = Field(default=None, max_length=80)
    experience_years: int = Field(default=0, ge=0, le=80)
    rating: int = Field(default=0, ge=0, le=10000)
    bio: Optional[str] = Field(default=None, max_length=1000)


class FighterUpdate(BaseModel):
    """Для PATCH: все поля необязательные."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    weapon: Optional[Weapon] = None
    club: Optional[str] = Field(default=None, max_length=80)
    experience_years: Optional[int] = Field(default=None, ge=0, le=80)
    rating: Optional[int] = Field(default=None, ge=0, le=10000)
    bio: Optional[str] = Field(default=None, max_length=1000)


class FighterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    weapon: str
    club: Optional[str] = None
    experience_years: int
    rating: int
    bio: Optional[str] = None
