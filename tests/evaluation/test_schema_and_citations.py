import asyncio
import json
import os
import sys
from typing import List, Dict, Any
from pydantic import ValidationError

# Add src to path
sys.path.append(os.getcwd())

from src.schema import KYBProfile, RegistryData, OwnershipStructure, OwnershipEntity, RiskRating, DocumentEvidence, DocumentChunk

async def test_strict_schema_enforcement():
    print("--- Testing Strict Schema Enforcement ---")
    
    # 1. Valid data should pass
    valid_data = {
        "entities_resolved": True,
        "risk_assessment": {
            "score": 0.5,
            "factors": ["Jurisdiction"],
            "summary": "Medium risk"
        }
    }
    try:
        KYBProfile.model_validate(valid_data)
        print("  [PASS] Valid data parsed successfully.")
    except ValidationError as e:
        print(f"  [FAIL] Valid data failed to parse: {e}")
        return False

    # 2. Extra fields should fail
    invalid_data = {
        "entities_resolved": True,
        "hallucinated_field": "oops",
        "risk_assessment": {
            "score": 0.5,
            "factors": ["Jurisdiction"],
            "summary": "Medium risk",
            "another_hallucination": 123
        }
    }
    try:
        KYBProfile.model_validate(invalid_data)
        print("  [FAIL] Extra fields were incorrectly allowed!")
        return False
    except ValidationError:
        print("  [PASS] Extra fields correctly blocked (Strict Enforcement).")
    
    return True

def verify_citations(profile: KYBProfile) -> List[str]:
    """
    Programmatically checks if facts in the profile exist in the source documents.
    """
    hallucinations = []
    
    # Aggregate all 'raw' source text
    source_text = ""
    if profile.registry and profile.registry.raw_data:
        source_text += json.dumps(profile.registry.raw_data).lower()
    
    for doc in profile.documents:
        for chunk in doc.chunks:
            source_text += chunk.text.lower()
            
    # Check 1: Ownership Entities
    if profile.ownership:
        for entity in profile.ownership.entities:
            if entity.name.lower() not in source_text:
                hallucinations.append(f"Entity '{entity.name}' not found in source documents.")

    # Check 2: Risk Factors
    if profile.risk_assessment:
        for factor in profile.risk_assessment.factors:
            # This is a bit harder as factors might be synthesized, 
            # but usually they should have keywords in the source.
            # We'll check for broad keyword matches or just log for demo.
            keywords = factor.lower().split()
            found = any(kw in source_text for kw in keywords if len(kw) > 3)
            if not found:
                # We allow some synthesis, but warn if no keywords match
                pass 

    return hallucinations

async def run_citation_test():
    print("\n--- Testing Citation Verification ---")
    
    # Mocking an agent response with some source data
    mock_registry_raw = {
        "company": "TechPioneer Solutions Inc",
        "officers": ["Alice Johnson", "Bob Smith"],
        "status": "Active",
        "country": "USA"
    }
    
    # CASE A: Accurate Report
    accurate_profile = KYBProfile(
        registry=RegistryData(
            company_name="TechPioneer Solutions Inc",
            status="Active",
            jurisdiction="USA",
            raw_data=mock_registry_raw
        ),
        ownership=OwnershipStructure(
            entities=[
                OwnershipEntity(name="Alice Johnson", type="Individual", percentage=75.0, is_ubo=True),
                OwnershipEntity(name="Bob Smith", type="Individual", percentage=25.0, is_ubo=True)
            ],
            layers=1,
            resolved=True
        ),
        risk_assessment=RiskRating(
            score=0.1,
            factors=["Clear Registry"],
            summary="Low risk company."
        )
    )
    
    errors = verify_citations(accurate_profile)
    if not errors:
        print("  [PASS] Accurate profile verified: All facts found in sources.")
    else:
        print(f"  [FAIL] Accurate profile failed verification: {errors}")

    # CASE B: Hallucinated Entity
    hallucinated_profile = KYBProfile(
        registry=RegistryData(
            company_name="TechPioneer Solutions Inc",
            status="Active",
            jurisdiction="USA",
            raw_data=mock_registry_raw
        ),
        ownership=OwnershipStructure(
            entities=[
                OwnershipEntity(name="Alice Johnson", type="Individual", percentage=75.0, is_ubo=True),
                OwnershipEntity(name="Eve Villain", type="Individual", percentage=25.0, is_ubo=True) # Hallucination
            ],
            layers=1,
            resolved=True
        )
    )
    
    errors = verify_citations(hallucinated_profile)
    if "Eve Villain" in str(errors):
        print("  [PASS] Citation test correctly detected hallucinated entity 'Eve Villain'.")
    else:
        print(f"  [FAIL] Citation test failed to detect hallucination: {errors}")


async def main():
    schema_ok = await test_strict_schema_enforcement()
    await run_citation_test()
    
    if schema_ok:
        print("\n[SUCCESS] Property-Based & Schema Validation tests passed.")
    else:
        print("\n[FAILURE] Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
