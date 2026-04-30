# Data Card: KYB Investigation Corpus

## Dataset Overview
- **Data Subject:** Corporate Registry Data, Identity Documents, Sanctions Lists.
- **Data Sources:** 
    - Official Registries (OpenCorporates, Companies House, ACRA).
    - Commercial Data Providers (Mocks used for development).
    - Global Sanctions Lists (OFAC, EU, UN).
- **Collection Method:** Real-time API retrieval and OCR-based document extraction.

## Data Characteristics
- **Structure:** Hybrid of relational (registry), graph (ownership), and unstructured (PDF documents).
- **Update Frequency:** Real-time (Registry/Sanctions) or on-demand (Documents).

## Data Quality & Validation
- **Verification:** Cross-referenced registry data against user-provided documents.
- **Cleanliness:** Data resolution agent handles fuzzy matching and entity normalization.
- **Provenance:** Every data point is tagged with source URL, timestamp, and retrieval method.

## Privacy & Ethics
- **Personally Identifiable Information (PII):** Handles Director/UBO names, addresses, and ID numbers.
- **Privacy Mitigation:** Data encryption at rest, short TTL for temporary document extracts, and strict ABAC (Attribute-Based Access Control) for data access.
- **Compliance:** Aligned with GDPR and jurisdictional secrecy laws (e.g., Cayman BVI).

## Known Gaps
- **Shell Companies:** Limited visibility into opaque jurisdictions with no public registry.
- **Real-time Lag:** Registry updates may lag behind actual corporate changes by 24-48 hours.
