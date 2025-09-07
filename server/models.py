from sqlalchemy import Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel


Base = declarative_base()


class EventDB(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    rubric = Column(String, index=True)
    title = Column(String, index=True)
    image_url = Column(String)
    rating = Column(Float)
    price = Column(String)
    details = Column(Text)


class EventCreate(BaseModel):
    rubric: str
    title: str
    image_url: str
    rating: float
    price: str
    details: str


class EventResponse(EventCreate):
    id: int
    
    class Config:
        from_attributes = True