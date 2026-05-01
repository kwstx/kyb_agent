from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class HumanAnnotation(Base):
    __tablename__ = 'human_annotations'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    profile_id = Column(String(255), index=True)
    agent_output = Column(JSON)
    corrected_output = Column(JSON)
    reviewer_id = Column(String(255))
    feedback_type = Column(String(50))  # correction, validation, rejection
    notes = Column(Text)
    optimization_status = Column(String(50), default='pending') # pending, processed, skipped

class RegulatoryRule(Base):
    __tablename__ = 'regulatory_rules'

    id = Column(Integer, primary_key=True)
    version = Column(String(50))
    jurisdiction = Column(String(100))
    rule_content = Column(JSON)
    active_from = Column(DateTime)
    active_to = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
