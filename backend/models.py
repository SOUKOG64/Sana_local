"""ORM-модели: 8 таблиц предметной области «Арт-фехтование»."""
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="participant")  # participant / judge / organizer
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    fighters: Mapped[List["Fighter"]] = relationship(back_populates="owner")
    scores: Mapped[List["Score"]] = relationship(back_populates="judge")


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    city: Mapped[Optional[str]] = mapped_column(String(80))

    fighters: Mapped[List["Fighter"]] = relationship(back_populates="club_ref")


class Fighter(Base):
    """Главная сущность — фехтовальщик (участник)."""
    __tablename__ = "fighters"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    weapon: Mapped[str] = mapped_column(String(20))
    experience_years: Mapped[int] = mapped_column(default=0)
    rating: Mapped[int] = mapped_column(default=0)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    club_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clubs.id"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    club_ref: Mapped[Optional[Club]] = relationship(back_populates="fighters")
    owner: Mapped[Optional[User]] = relationship(back_populates="fighters")
    registrations: Mapped[List["Registration"]] = relationship(
        back_populates="fighter", cascade="all, delete-orphan")
    performances: Mapped[List["Performance"]] = relationship(
        back_populates="fighter", cascade="all, delete-orphan")

    @property
    def club(self) -> Optional[str]:
        """Название клуба для схемы ответа."""
        return self.club_ref.name if self.club_ref else None


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    event_date: Mapped[Optional[date]] = mapped_column(Date)
    city: Mapped[Optional[str]] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="announced")

    nominations: Mapped[List["Nomination"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan")
    registrations: Mapped[List["Registration"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan")


class Nomination(Base):
    __tablename__ = "nominations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))  # «Шпага соло», «Рапира дуэт»
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))

    tournament: Mapped[Tournament] = relationship(back_populates="nominations")
    performances: Mapped[List["Performance"]] = relationship(back_populates="nomination")


class Registration(Base):
    """Заявка участника на турнир (связь многие-ко-многим)."""
    __tablename__ = "registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    fighter_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    fighter: Mapped[Fighter] = relationship(back_populates="registrations")
    tournament: Mapped[Tournament] = relationship(back_populates="registrations")


class Performance(Base):
    __tablename__ = "performances"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    duration_sec: Mapped[int] = mapped_column(default=0)
    fighter_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    nomination_id: Mapped[int] = mapped_column(ForeignKey("nominations.id"))

    fighter: Mapped[Fighter] = relationship(back_populates="performances")
    nomination: Mapped[Nomination] = relationship(back_populates="performances")
    scores: Mapped[List["Score"]] = relationship(
        back_populates="performance", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    technique: Mapped[float] = mapped_column(default=0)
    artistry: Mapped[float] = mapped_column(default=0)
    costume: Mapped[float] = mapped_column(default=0)
    performance_id: Mapped[int] = mapped_column(ForeignKey("performances.id"))
    judge_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    performance: Mapped[Performance] = relationship(back_populates="scores")
    judge: Mapped[User] = relationship(back_populates="scores")
