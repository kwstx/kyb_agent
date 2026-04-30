# Model Card: KYB Investigator Reasoning Engine

## Model Details
- **Developer:** Agentic KYB Team
- **Model Date:** April 2026
- **Model Type:** Multi-agent orchestration (Frontier LLM for Reasoning + Flash LLM for Critique)
- **Primary Tasks:** Corporate structure resolution, risk assessment, document cross-referencing.

## Intended Use
- **Primary User:** Compliance officers and financial institutions.
- **Intended Use Cases:** Automating Know Your Business (KYB) checks, identifying beneficial ownership, detecting regulatory red flags.
- **Out-of-Scope Use Cases:** Credit scoring, individual KYC (without adaptation), automated asset freezing without human oversight.

## Factors
- **Jurisdictions:** Optimized for Delaware, Singapore, UK, and Cayman Islands. Performance may vary in non-standard or opaque jurisdictions.
- **Data Quality:** Dependent on the accuracy of registry data and OCR extraction quality.

## Metrics
- **Confidence Calibration:** Uses direct LLM calibration with uncertainty weighting.
- **Explainability:** Provides full chain-of-thought traces and SHAP-style feature importance.
- **Regulatory Alignment:** Evaluated against jurisdictional rule-sets by a Critic Agent.

## Training Data & Fine-tuning
- **Base Models:** GPT-4o (Reasoning), Gemini 3 Flash (Criticism).
- **Fine-tuning:** Reasoning components are "prompt-tuned" using a curated dataset of complex ownership structures and AML/CFT regulatory guidelines.

## Limitations & Bias Checks
- **Limitations:** May struggle with extremely layered trust structures (10+ layers) or handwritten legacy documents.
- **Bias Checks:** Regular auditing for jurisdictional bias (e.g., higher risk scores for specific regions without objective data).
- **Mitigation:** Self-critique loop and human-in-the-loop escalation for low-confidence decisions (<0.6).
