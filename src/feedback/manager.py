import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from feedback.models import Base, HumanAnnotation, RegulatoryRule
import datetime

class FeedbackManager:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///./kyb_feedback.db")
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def record_correction(self, profile_id, agent_output, corrected_output, reviewer_id, notes=None):
        session = self.Session()
        try:
            annotation = HumanAnnotation(
                profile_id=profile_id,
                agent_output=agent_output,
                corrected_output=corrected_output,
                reviewer_id=reviewer_id,
                feedback_type='correction',
                notes=notes
            )
            session.add(annotation)
            session.commit()
            return annotation.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def export_for_finetuning(self, format='jsonl'):
        """Exports high-quality corrections for fine-tuning or prompt optimization."""
        session = self.Session()
        try:
            annotations = session.query(HumanAnnotation).filter(HumanAnnotation.feedback_type == 'correction').all()
            dataset = []
            for a in annotations:
                dataset.append({
                    "input": a.agent_output.get('prompt', ''), # Assuming prompt is stored
                    "ideal_output": a.corrected_output
                })
            
            if format == 'jsonl':
                output_path = "finetuning_dataset.jsonl"
                with open(output_path, 'w') as f:
                    for entry in dataset:
                        f.write(json.dumps(entry) + '\n')
                return output_path
            return dataset
        finally:
            session.close()

    def update_regulatory_rules(self, jurisdiction, rules_json, version):
        """Versioned storage of regulatory rules."""
        session = self.Session()
        try:
            rule = RegulatoryRule(
                jurisdiction=jurisdiction,
                rule_content=rules_json,
                version=version,
                active_from=datetime.datetime.utcnow()
            )
            session.add(rule)
            session.commit()
        finally:
            session.close()

# Singleton instance
feedback_manager = FeedbackManager()
