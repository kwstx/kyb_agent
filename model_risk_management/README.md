# Model Risk Management (MRM) Documentation

## Overview
This folder contains the documentation required for model risk management, including component descriptions, testing results, and change history, as required by regulatory compliance standards.

## Components
- **Investigator Agent**: Responsible for planning and executing data gathering.
- **Critic Agent**: Performs self-critique and validation against compliance rules.
- **Entity Resolution Engine**: Resolves complex ownership structures.
- **Document Intelligence Pipeline**: Processes and extracts data from documents.
- **Safety/Policy Enforcement Layer (PEL)**: Intercepts actions to ensure compliance.

## Testing Strategy
- Unit tests for all core components.
- Integration tests for agent tool use.
- Policy evaluation tests (Guardrails).
- Backtesting against historical KYB cases.

## Feedback & Continuous Improvement
- **Human Annotation Loop**: Reviewers can correct agent outputs via `src.feedback.manager.feedback_manager`.
- **Dataset Generation**: Corrections are automatically collected and can be exported for fine-tuning or prompt optimization (DSPy).
- **Regulatory Rule Versioning**: Regulatory changes are tracked and stored in the knowledge base, with re-validation triggers.

## Compliance & Monitoring Tooling
- **Automated Statistics**: Tracks authorization rates, escalation rates (High risk cases), and agent activity.
- **Regulator-Friendly Exports**: Generates XML audit logs with digital signatures (stubs) for case-by-case disclosure.
- **Periodic Re-validation**: Scheduled checks of existing profiles against the latest regulatory documents in `knowledge_base/regulatory_rules/`.

## Change History
- 2026-05-01: Initial setup of MRM folder, feedback loop, and compliance reporting tools.
