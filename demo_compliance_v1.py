import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from feedback.manager import feedback_manager
from compliance.reporter import compliance_reporter
from tools.audit import audit_store
import json
import uuid

def demo():
    print("--- Starting Compliance & Monitoring Demo ---")

    # 1. Simulate an Agent Action being logged
    action_id = str(uuid.uuid4())
    print(f"Logging simulated agent action: {action_id}")
    audit_store.log_action(
        agent_id="Investigator_001",
        action_id=action_id,
        action_type="FETCH_REGISTRY_DATA",
        risk_tier="Medium",
        signature="CRYPTO_SIG_XYZ",
        authorized=True,
        explanation="Necessary for UBO resolution in UK jurisdiction."
    )

    # 2. Record Human Feedback (Correction)
    print("\nRecording human correction for profile 'ABC_CORP'...")
    profile_id = "ABC_CORP_123"
    agent_output = {"ubo_identified": ["John Doe"], "confidence": 0.8}
    corrected_output = {"ubo_identified": ["John Doe", "Jane Smith"], "confidence": 1.0}
    
    feedback_id = feedback_manager.record_correction(
        profile_id=profile_id,
        agent_output=agent_output,
        corrected_output=corrected_output,
        reviewer_id="Reviewer_Compliance_Lead",
        notes="Missed secondary shareholder Jane Smith due to complex trust layer."
    )
    print(f"Feedback recorded with ID: {feedback_id}")

    # 3. Generate Statistics
    print("\nGenerating Compliance Statistics...")
    stats = compliance_reporter.generate_statistics()
    print(json.dumps(stats, indent=2))

    # 4. Export XML Audit Log
    print(f"\nExporting XML Audit Log for profile {profile_id}...")
    xml_file = compliance_reporter.export_audit_log_xml(profile_id)
    print(f"Audit log exported to: {xml_file}")

    # 5. Export for Fine-tuning
    print("\nExporting feedback for fine-tuning...")
    dataset_path = feedback_manager.export_for_finetuning()
    print(f"Dataset ready at: {dataset_path}")

    print("\n--- Demo Completed Successfully ---")

if __name__ == "__main__":
    demo()
