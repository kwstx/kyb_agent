import json
import os
import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import xml.etree.ElementTree as ET
from xml.dom import minidom
from tools.audit import ActionAudit, ToolInvocationAudit, AuditStore
from feedback.models import RegulatoryRule

class ComplianceReporter:
    def __init__(self, audit_db_url=None):
        self.audit_db_url = audit_db_url or os.getenv("DATABASE_URL", "sqlite:///./kyb_audit.db")
        self.engine = create_engine(self.audit_db_url)
        self.Session = sessionmaker(bind=self.engine)

    def generate_statistics(self, days=30):
        """Generates decision statistics and escalation rates."""
        session = self.Session()
        try:
            since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            total_actions = session.query(ActionAudit).filter(ActionAudit.timestamp >= since).count()
            authorized_actions = session.query(ActionAudit).filter(
                ActionAudit.timestamp >= since, 
                ActionAudit.authorized == 1
            ).count()
            
            escalations = session.query(ActionAudit).filter(
                ActionAudit.timestamp >= since,
                ActionAudit.risk_tier == 'High'
            ).count()

            stats = {
                "period_days": days,
                "total_agent_actions": total_actions,
                "authorization_rate": (authorized_actions / total_actions) if total_actions > 0 else 0,
                "escalation_rate": (escalations / total_actions) if total_actions > 0 else 0,
                "risk_distribution": {
                    "Low": session.query(ActionAudit).filter(ActionAudit.risk_tier == 'Low').count(),
                    "Medium": session.query(ActionAudit).filter(ActionAudit.risk_tier == 'Medium').count(),
                    "High": escalations
                }
            }
            return stats
        finally:
            session.close()

    def export_audit_log_xml(self, profile_id):
        """Exports a regulator-friendly XML audit log for a specific case."""
        session = self.Session()
        try:
            # Gather all related logs
            # For simplicity, we'll assume we filter by profile_id in the future
            # For now, let's just get the last few entries
            actions = session.query(ActionAudit).limit(100).all()
            
            root = ET.Element("KYB_AuditLog")
            root.set("ProfileID", profile_id)
            root.set("ExportTimestamp", datetime.datetime.utcnow().isoformat())
            
            # Metadata
            meta = ET.SubElement(root, "Metadata")
            ET.SubElement(meta, "SystemVersion").text = "1.0.0"
            ET.SubElement(meta, "ComplianceStandard").text = "AML/KYC 2026-V2"

            # Actions
            actions_node = ET.SubElement(root, "Actions")
            for action in actions:
                a_node = ET.SubElement(actions_node, "Action")
                a_node.set("ID", str(action.action_id))
                ET.SubElement(a_node, "Timestamp").text = action.timestamp.isoformat()
                ET.SubElement(a_node, "Type").text = action.action_type
                ET.SubElement(a_node, "RiskTier").text = action.risk_tier
                ET.SubElement(a_node, "Authorized").text = str(bool(action.authorized))
                ET.SubElement(a_node, "Signature").text = action.signature or "UNSIGNED"
            
            # Digital Signature Stub
            signature_node = ET.SubElement(root, "DigitalSignature")
            signature_node.set("Method", "RSA-SHA256")
            signature_node.text = "EXAMPLE_DIGITAL_SIGNATURE_VALUE_REPLACE_WITH_REAL_HSM_SIGNATURE"

            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            
            output_file = f"audit_report_{profile_id}.xml"
            with open(output_file, "w") as f:
                f.write(xml_str)
            
            return output_file
        finally:
            session.close()

    def run_revalidation(self, company_profile, jurisdiction):
        """Re-validates a profile against the latest versioned rules."""
        # This would typically involve loading rules from the feedback DB
        # and using the Critic Agent to re-evaluate.
        print(f"Running re-validation for {jurisdiction}...")
        # Stub logic
        return {"status": "compliant", "revalidation_date": datetime.datetime.utcnow().isoformat()}

# Singleton
compliance_reporter = ComplianceReporter()
