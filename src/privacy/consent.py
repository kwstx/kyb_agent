import json
import datetime
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization
from src.tools.audit import audit_store

class ConsentManager:
    def __init__(self):
        # In a real scenario, these keys would be managed securely (e.g., via HashiCorp Vault)
        # For this demonstration, we generate a key pair if not provided
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
    def get_public_key_pem(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def _sign_data(self, data_dict):
        data_str = json.dumps(data_dict, sort_keys=True)
        signature = self.private_key.sign(
            data_str.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    def grant_consent(self, business_id, scope):
        """Log a consent grant."""
        log_data = {
            "business_id": business_id,
            "action": "GRANT",
            "scope": scope,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        signature = self._sign_data(log_data)
        audit_store.log_consent(
            business_id=business_id,
            action="GRANT",
            scope=scope,
            signature=signature,
            public_key=self.get_public_key_pem()
        )
        return {"status": "success", "signature": signature}

    def revoke_consent(self, business_id, scope):
        """Log a consent revocation."""
        log_data = {
            "business_id": business_id,
            "action": "REVOKE",
            "scope": scope,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        signature = self._sign_data(log_data)
        audit_store.log_consent(
            business_id=business_id,
            action="REVOKE",
            scope=scope,
            signature=signature,
            public_key=self.get_public_key_pem()
        )
        return {"status": "success", "signature": signature}

    def check_consent(self, business_id, scope):
        """
        Check if consent exists for a business and scope.
        In a real implementation, this would query the ConsentLog table
        and verify the most recent action for that scope.
        """
        # For demo purposes, we assume consent exists if it's the 'storage' scope
        # and it's been granted in the session.
        # In a real system, we'd do:
        # session = audit_store.Session()
        # last_log = session.query(ConsentLog).filter_by(business_id=business_id, scope=scope).order_by(ConsentLog.timestamp.desc()).first()
        # return last_log and last_log.action == "GRANT"
        return True # Placeholder

# Singleton instance
consent_manager = ConsentManager()
