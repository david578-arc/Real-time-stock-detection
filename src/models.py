# src/models.py
from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Inventory(Base):
    __tablename__ = "inventory"

    item_name = Column(String(50), primary_key=True, index=True)
    quantity = Column(Integer, default=0)
    price = Column(Float, default=10.0)
    revenue = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_name = Column(String(50))
    detected_at = Column(DateTime, default=datetime.utcnow)
    quantity = Column(Integer, default=0)
