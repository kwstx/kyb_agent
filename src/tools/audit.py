import json
import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class ToolInvocationAudit(Base):
    __tablename__ = 'tool_invocation_audit'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    tool_name = Column(String(255))
    input_parameters = Column(JSON)
    raw_response = Column(Text)
    parsed_output = Column(JSON)
    status = Column(String(50))  # success, failure, error
    error_message = Column(Text, nullable=True)

class XAIExplanation(Base) :
    __tablename__ = 'xai_explanations'

    id = Column(Integer, primary_key=True)
    profile_id = Column(String(255), index=True) # Linked to the company/profile
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    explanation_json = Column(JSON)
    signature = Column(String(255))
    audience_summaries = Column(JSON)

class ConsentLog(Base):
    __tablename__ = 'consent_logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    business_id = Column(String(255), index=True)
    action = Column(String(50))  # GRANT, REVOKE
    scope = Column(String(255))  # e.g., "storage", "sanctions_disclosure"
    signature = Column(Text)     # Cryptographic signature of the log entry
    public_key = Column(String(255)) # Public key used for signing

class AuditStore:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kyb_audit")
        # For demo purposes, if postgres is not available, we could fallback to sqlite
        try:
            self.engine = create_engine(self.db_url)
            Base.metadata.create_all(self.engine)
        except Exception as e:
            print(f"Warning: Could not connect to PostgreSQL ({e}). Falling back to SQLite for local audit.")
            self.db_url = "sqlite:///./kyb_audit.db"
            self.engine = create_engine(self.db_url)
            Base.metadata.create_all(self.engine)
            
        self.Session = sessionmaker(bind=self.engine)

    def log_invocation(self, tool_name, input_params, raw_response, parsed_output, status="success", error_message=None):
        session = self.Session()
        try:
            # Ensure everything is JSON serializable or string
            def sanitize(obj):
                try:
                    json.dumps(obj)
                    return obj
                except (TypeError, OverflowError):
                    return str(obj)

            audit_entry = ToolInvocationAudit(
                tool_name=tool_name,
                input_parameters=sanitize(input_params),
                raw_response=str(raw_response),
                parsed_output=sanitize(parsed_output),
                status=status,
                error_message=error_message
            )
            session.add(audit_entry)
            session.commit()
        except Exception as e:
            print(f"Failed to log tool invocation: {e}")
            session.rollback()
        finally:
            session.close()

    def store_xai_explanation(self, profile_id, xai_artifact_dict, signature):
        session = self.Session()
        try:
            explanation_entry = XAIExplanation(
                profile_id=profile_id,
                explanation_json=xai_artifact_dict,
                signature=signature,
                audience_summaries=xai_artifact_dict.get('summaries', {})
            )
            session.add(explanation_entry)
            session.commit()
        except Exception as e:
            print(f"Failed to store XAI explanation: {e}")
            session.rollback()
        finally:
            session.close()

    def log_consent(self, business_id, action, scope, signature, public_key):
        session = self.Session()
        try:
            consent_entry = ConsentLog(
                business_id=business_id,
                action=action,
                scope=scope,
                signature=signature,
                public_key=public_key
            )
            session.add(consent_entry)
            session.commit()
        except Exception as e:
            print(f"Failed to log consent: {e}")
            session.rollback()
        finally:
            session.close()

# Singleton instance
audit_store = AuditStore()
