import json
import datetime
import uuid
from typing import Dict, Any, List
from src.privacy.consent import consent_manager

class SSIIssuer:
    def __init__(self, issuer_did: str = "did:kyb:agent"):
        self.issuer_did = issuer_did

    def generate_kyb_vc(self, business_data: Dict[str, Any], selective_fields: List[str] = None) -> Dict[str, Any]:
        """
        Generates a W3C Verifiable Credential for a KYB outcome.
        Supports selective disclosure by filtering fields.
        """
        # Data Minimization: Only include requested fields or default safe fields
        if selective_fields:
            credential_subject = {k: v for k, v in business_data.items() if k in selective_fields}
        else:
            # Default minimal set if no selection provided
            credential_subject = {
                "id": business_data.get("id", str(uuid.uuid4())),
                "company_name": business_data.get("company_name"),
                "registration_status": "verified",
                "sanctions_check": "clear",
                "verification_date": datetime.datetime.utcnow().isoformat()
            }

        vc = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://schema.org/"
            ],
            "id": f"urn:uuid:{uuid.uuid4()}",
            "type": ["VerifiableCredential", "KYBOutcomeCredential"],
            "issuer": self.issuer_did,
            "issuanceDate": datetime.datetime.utcnow().isoformat(),
            "credentialSubject": credential_subject,
            "proof": {
                "type": "RsaSignature2018",
                "created": datetime.datetime.utcnow().isoformat(),
                "proofPurpose": "assertionMethod",
                "verificationMethod": f"{self.issuer_did}#key-1",
                "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..SIGNED_PAYLOAD" # Mock JWS
            }
        }
        
        return vc

    def generate_wallet_link(self, vc: Dict[str, Any]) -> str:
        """
        Simulates generating a digital wallet link for the business to review the VC.
        """
        # In a real scenario, this would post the VC to a mediator or 
        # generate a deep link for a wallet app (like MATTR Pi or Dock Wallet)
        vc_id = vc["id"].split(":")[-1]
        return f"https://wallet.kyb-agent.io/review/{vc_id}"

# Singleton instance
ssi_issuer = SSIIssuer()
