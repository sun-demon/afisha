import os
import glob
import json
from datetime import datetime
from typing import Optional, Union
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi_utils.tasks import repeat_every

from models import Event, EventRubric, Rubric, Base, Favorite, Ticket, User
from logging_utils import setup_logging


DATA_DIR = './data'
DATABASE_DIRNAME = 'db'
os.makedirs(DATABASE_DIRNAME, exist_ok=True)
DATABASE_URL = f'sqlite:///./{DATABASE_DIRNAME}/afisha.sqlite3'  # for start SQLite, after can Postgres


engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine) # Create tables


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- on startup (startup) ---
    db = SessionLocal()
    try:
        latest_file = get_latest_data_file()
        if latest_file:
            logger.info(f'[{datetime.now()}] Initial DB update from {latest_file}')
            load_events_from_json(db, latest_file)
        else:
            logger.warning(f'[{datetime.now()}] No data files found in {DATA_DIR}')
    finally:
        db.close()

    # -----------------------------
    # Planner: update events once a day
    # -----------------------------
    @repeat_every(seconds=60*60*24)  # every 24 hours
    def update_db_from_file_task() -> None:
        db = SessionLocal()
        try:
            latest_file = get_latest_data_file()
            if latest_file:
                print(f'[{datetime.now()}] Updating DB from {latest_file}')
                load_events_from_json(db, latest_file)
            else:
                print(f'[{datetime.now()}] No data files found in {DATA_DIR}')
        finally:
            db.close()

    # --- continue app work ---
    yield

    # --- on shutdown (shutdown) ---
    logger.info(f'[{datetime.now()}] Server shutting down…')


app = FastAPI(title='Afisha API', lifespan=lifespan)


def get_latest_data_file() -> Union[str, None]:
    files = glob.glob(os.path.join(DATA_DIR, 'moscow_events*.json'))
    if not files:
        return None
    return max(files)  # lexicographic order


def _to_float_or_none(value) -> Optional[float]:
    if value is None:
        return None
    try:
        # in JSON rating may be '6.7' or '6,7' — try replace comma to dot
        if isinstance(value, str):
            v = value.replace(',', '.').strip()
            return float(v)
        return float(value)
    except Exception:
        return None


def load_events_from_json(db: Session, filepath: str) -> dict:
    """Load events from JSON file, update Events and EventRubric."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError('Expected top-level JSON object mapping event_id -> event_data')

    visited_ids = set()

    try:
        for event_id, event_payload in data.items():
            visited_ids.add(event_id)

            title = event_payload.get('title')
            image_url = event_payload.get('image_url')
            rating = _to_float_or_none(event_payload.get('rating'))
            price = event_payload.get('price')
            details = event_payload.get('details')

            # upsert event
            event = db.query(Event).filter_by(id=event_id).first()
            if event:
                event.title = title
                event.image_url = image_url
                event.rating = rating
                event.price = price
                event.details = details

                event.archived = False
            else:
                event = Event(
                    id=event_id,
                    
                    title=title,
                    image_url=image_url,
                    rating=rating,
                    price=price,
                    details=details,
                    
                    archived=False,
                )
                db.add(event)
                db.flush()

            # handle rubrics (event_payload['rubrics'] — rubric code list, for example ['cinema', 'art'])
            rubrics = event_payload.get('rubrics')
            # delete old bundels and insert new (simple for study project)
            db.query(EventRubric).filter(EventRubric.event_id == event_id).delete()

            for rubric_code in rubrics:
                rubric_code = str(rubric_code).strip()
                if not rubric_code:
                    continue
                rubric = db.query(Rubric).filter(Rubric.code == rubric_code).first()
                if not rubric:
                    # Create new rubric 'by code' (title same, because only english rubric name)
                    rubric = Rubric(code=rubric_code)
                    db.add(rubric)
                    db.flush()  # For getting rubric id
                # Add bundle
                event_rubric = EventRubric(event_id=event_id, rubric_id=rubric.id)
                db.add(event_rubric)

        # archivate events that don't found in new event list
        if visited_ids:
            # update rows set
            db.query(Event).filter(~Event.id.in_(list(visited_ids))).update({'archived': True}, synchronize_session=False)

        db.commit()
    except Exception:
        db.rollback()
        raise


# -----------------------------
# Dependency for database
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# Events
# -----------------------------
@app.get('/api/events')
def get_events(rubric: Union[str, None] = None, user_id: Union[int, None] = None, token: Union[str, None] = None, db: Session = Depends(get_db)):
    """Get all events or events by rubric (?rubric=cinema)"""
    query = db.query(Event)
    if rubric:
        query = query.join(EventRubric).join(Rubric).filter(Rubric.code == rubric)
    return query.all()


# -----------------------------
# Auth
# -----------------------------
@app.post('/api/register')
def register_user(username: str, password: str, email: Union[str, None] = None, db: Session = Depends(get_db)):
    """Register new user (now without JWT, just a blank)."""
    user = User(username=username, email=email, password_hash=password)  # TODO: hash password
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail='Username or email already exists')
    return {'message': 'User registered successfully'}


@app.post('/api/login')
def login_user(username: str, password: str, db: Session = Depends(get_db)):
    """Login (a blank, now without JWT)."""
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password_hash != password:
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return {'message': f'Welcome {user.username}!'}


# -----------------------------
# Favorites
# -----------------------------
@app.get('/api/favorites')
def get_favorites(user_id: int, db: Session = Depends(get_db)):
    """Get user favorite events."""
    favs = db.query(Favorite).filter(Favorite.user_id == user_id).all()
    return favs


@app.post('/api/favorites/{event_id}')
def add_favorite(event_id: str, user_id: int, db: Session = Depends(get_db)):
    """Add event to favorites."""
    fav = Favorite(user_id=user_id, event_id=event_id)
    db.add(fav)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail='Already in favorites')
    return {'message': 'Added to favorites'}


@app.delete('/api/favorites/{event_id}')
def remove_favorite(event_id: str, user_id: int, db: Session = Depends(get_db)):
    """Delete event from favorites."""
    fav = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.event_id == event_id).first()
    if not fav:
        raise HTTPException(status_code=404, detail='Not found')
    db.delete(fav)
    db.commit()
    return {'message': 'Removed from favorites'}


# -----------------------------
# Tickets
# -----------------------------
@app.get('/api/tickets')
def get_tickets(user_id: int, db: Session = Depends(get_db)):
    """Get user tickets."""
    return db.query(Ticket).filter(Ticket.user_id == user_id).all()


@app.post('/api/tickets/{event_id}')
def buy_ticket(event_id: str, user_id: int, db: Session = Depends(get_db)):
    """Buy ticket (if was in favorites, delete from favorites)."""
    ticket = Ticket(user_id=user_id, event_id=event_id)
    db.add(ticket)

    # Delete from favorites
    fav = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.event_id == event_id).first()
    if fav:
        db.delete(fav)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail='Already purchased')
    return {'message': 'Ticket purchased'}
