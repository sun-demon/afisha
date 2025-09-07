from typing import List, AsyncIterator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import init_db, get_db
from models import EventDB, EventCreate, EventResponse
from utils import ensure_data_directory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan handler for initialization and clearing"""
    # Startup
    await ensure_data_directory()
    init_db()
    print('Application started successfully')
    
    yield
    
    # Shutdown (if neeeded)
    print('Application shutting down')


app = FastAPI(
    title='Afisha API', 
    version='1.0.0',
    lifespan=lifespan
)


@app.get('/')
async def root():
    return {'message': 'Afisha API work'}


@app.post('/load-events/', response_model=List[EventResponse])
async def load_events(
    file_path: str = 'data/moscow_events.json',
    db: Session = Depends(get_db)
):
    """Load events from file to database"""
    from app.utils import process_events_file  # Local import for avoidance cyclic dependencies
    
    try:
        events = await process_events_file(file_path)
        
        # Save events to database
        saved_events = []
        for event in events:
            db_event = EventDB(**event.dict())
            db.add(db_event)
            db.commit()
            db.refresh(db_event)
            saved_events.append(db_event)
        
        return saved_events
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error downloading: {str(e)}')


@app.get('/events/', response_model=List[EventResponse])
async def get_events(
    skip: int = 0,
    limit: int = 100,
    rubric: str = None,
    db: Session = Depends(get_db)
):
    """Getting event list with filtration by rubtic"""
    query = db.query(EventDB)
    
    if rubric:
        query = query.filter(EventDB.rubric == rubric)
    
    events = query.offset(skip).limit(limit).all()
    return events


@app.get('/events/{event_id}', response_model=EventResponse)
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """Getting concrete event by ID"""
    event = db.query(EventDB).filter(EventDB.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail='Event not found')
    return event


@app.get('/rubrics/')
async def get_rubrics(db: Session = Depends(get_db)):
    """Getting all rubric list"""
    rubrics = db.query(EventDB.rubric).distinct().all()
    return {'rubrics': [r[0] for r in rubrics]}


@app.delete("/events/{event_id}")
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Deletting event by id"""
    event = db.query(EventDB).filter(EventDB.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail='Event not found')
    
    db.delete(event)
    db.commit()
    return {'message': 'Event deleted'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)