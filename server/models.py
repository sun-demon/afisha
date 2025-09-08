from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Text, ForeignKey, UniqueConstraint, Boolean
from typing import Optional


class Base(DeclarativeBase):
    pass


# -----------------------------
# Events
# -----------------------------
class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, index=True)  # hex id
    title: Mapped[str] = mapped_column(String, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rubrics = relationship("EventRubric", back_populates="event")

    archived: Mapped[Optional[str]] = mapped_column(Boolean, nullable=False, default=False)


# -----------------------------
# Rubrics
# -----------------------------
class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # "cinema", "art", ...


# -----------------------------
# Event <-> Rubric (bundle)
# -----------------------------
class EventRubric(Base):
    __tablename__ = "event_rubrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    rubric_id: Mapped[int] = mapped_column(ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("event_id", "rubric_id", name="uix_event_rubric"),)

    event = relationship("Event", back_populates="rubrics")
    rubric = relationship("Rubric")


# -----------------------------
# Users
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# -----------------------------
# Favorites (user <-> event)
# -----------------------------
class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))

    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uix_user_favorite"),)


# -----------------------------
# Tickets (purchased tickets)
# -----------------------------
class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))

    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uix_user_ticket"),)
