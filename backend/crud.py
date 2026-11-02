"""CRUD через ORM (Session, select, commit, rollback) — без прямого SQL."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from models import Club, Fighter, User
from schemas import FighterCreate, FighterUpdate
from security import hash_password


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def _get_or_create_club(db: Session, name: Optional[str]) -> Optional[Club]:
    name = (name or "").strip()
    if not name:
        return None
    club = db.scalar(select(Club).where(Club.name == name))
    if club is None:
        club = Club(name=name)
        db.add(club)
        db.flush()  # чтобы следующий select увидел этот клуб
    return club


# ---------- пользователи ----------
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def create_user(db: Session, email: str, password: str) -> User:
    user = User(email=email.strip().lower(), password_hash=hash_password(password))
    db.add(user)
    _commit(db)
    db.refresh(user)
    return user


# ---------- фехтовальщики ----------
def list_fighters(db: Session, search: Optional[str], weapon: Optional[str]) -> List[Fighter]:
    stmt = (
        select(Fighter)
        .options(selectinload(Fighter.club_ref))
        .order_by(Fighter.rating.desc(), Fighter.full_name)
    )
    if weapon:
        stmt = stmt.where(Fighter.weapon == weapon)
    items = list(db.scalars(stmt))
    if search:
        # SQLite не умеет регистронезависимый поиск по кириллице, поэтому фильтруем в Python
        s = search.strip().casefold()
        items = [f for f in items if s in f.full_name.casefold() or s in (f.club or "").casefold()]
    return items


def get_fighter(db: Session, fighter_id: int) -> Optional[Fighter]:
    return db.get(Fighter, fighter_id)


def create_fighter(db: Session, data: FighterCreate, owner: User) -> Fighter:
    fighter = Fighter(
        full_name=data.full_name.strip(),
        weapon=data.weapon,
        experience_years=data.experience_years,
        rating=data.rating,
        bio=data.bio,
        club_ref=_get_or_create_club(db, data.club),
        owner=owner,
    )
    db.add(fighter)
    _commit(db)
    db.refresh(fighter)
    return fighter


def update_fighter(db: Session, fighter: Fighter, data: FighterUpdate) -> Fighter:
    changes = data.model_dump(exclude_unset=True)
    if "club" in changes:
        fighter.club_ref = _get_or_create_club(db, changes.pop("club"))
    for field, value in changes.items():
        if value is not None:
            setattr(fighter, field, value)
    _commit(db)
    db.refresh(fighter)
    return fighter


def delete_fighter(db: Session, fighter: Fighter) -> None:
    db.delete(fighter)
    _commit(db)


def seed(db: Session) -> None:
    """Демо-данные при первом запуске."""
    if db.scalar(select(Fighter).limit(1)) is not None:
        return
    demo = [
        ("Иван Громов", "шпага", "Клуб «Эфес»", 7, 920, "Победитель фестиваля «Стальной ветер»."),
        ("Мария Волкова", "рапира", "Клуб «Эфес»", 5, 870, "Любит театральные дуэты."),
        ("Алексей Соколов", "сабля", "Школа «Дамаск»", 3, 640, None),
        ("Ольга Морозова", "меч", "Школа «Дамаск»", 9, 990, "Постановщик групповых боёв."),
    ]
    for name, weapon, club, exp, rating, bio in demo:
        db.add(Fighter(full_name=name, weapon=weapon, experience_years=exp, rating=rating,
                       bio=bio, club_ref=_get_or_create_club(db, club)))
    _commit(db)
