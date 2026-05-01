import json
from typing import List, Dict, Any, Optional, Annotated, Union
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.schema import AgentState, KYBProfile, RegistryData, RiskRating, XAIArtifact, AudienceSummary
import hashlib
import hmac
from src.tools.audit import audit_store

# --- Schema for Reasoning ---

class ReasoningStep(BaseModel):
    thought: str = Field(description="Internal monologue of the investigator")
    plan: str = Field(description="Step-by-step plan for the current action")
    tool_selection: Optional[str] = Field(description="The name of the tool to use or 'FINISH'")
    tool_input: Optional[Dict[str, Any]] = Field(description="Parameters for the tool")
    observation: Optional[str] = Field(description="Result of the tool execution")
    critique: Optional[str] = Field(description="Feedback from the Critic Agent")
    confidence: float = Field(description="Confidence score for this step (0-1)", ge=0, le=1)

class Hypothesis(BaseModel):
    description: str
    rationale: str
    confidence_score: float

class Synthesis(BaseModel):
    final_summary: str
    primary_hypothesis: Hypothesis
    alternative_hypotheses: List[Hypothesis]
    regulatory_alignment: str
    confidence_score: float
    uncertainty_factors: List[str]
    feature_importance: Dict[str, float] # e.g. {"registry_data": 0.4, "document_verification": 0.3, "sanctions_check": 0.3}
    citations: List[Dict[str, str]] # [{ "source": "...", "snippet": "..." }]

# --- Agents ---

class CriticAgent:
    """
    A lightweight agent designed for rapid validation and regulatory alignment checks.
    Uses a faster model (Gemini 3 Flash) to control costs.
    """
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.llm = ChatGoogleGenerativeAI(model=model_name)
    
    async def evaluate_step(self, step: ReasoningStep, context: Dict[str, Any], jurisdiction: str) -> str:
        # Simulate retrieval from a vector database of jurisdiction-specific rules
        rules = self._get_compliance_rules(jurisdiction)
        
        prompt = f"""
        System: You are a Senior Compliance Critic. Your role is to evaluate the reasoning of an Investigator Agent.
        
        JURISDICTION: {jurisdiction}
        REGULATORY RULES: {rules}
        
        INVESTIGATION CONTEXT (PREVIOUS STEPS):
        {json.dumps(context.get('history', []), indent=2)}
        
        CURRENT STEP TO EVALUATE:
        Thought: {step.thought}
        Plan: {step.plan}
        Action: {step.tool_selection} with {step.tool_input}
        Observation: {step.observation}
        
        Evaluate this step for:
        1. Consistency: Does it contradict earlier findings?
        2. Completeness: Does it leave obvious gaps?
        3. Compliance: Does it follow the jurisdiction's specific KYB rules?
        
        Provide a concise critique. Be harsh but fair.
        """
        response = await self.llm.ainvoke(prompt)
        return response.content

    def _get_compliance_rules(self, jurisdiction: str) -> str:
        # Mocking vector DB retrieval for jurisdiction-specific rules
        rules_db = {
            "Delaware": "Verify beneficial ownership if >25% control. Check for OFAC sanctions. Ensure 'Active' status via Secretary of State.",
            "Cayman Islands": "Enhanced Due Diligence (EDD) mandatory. Verify Source of Wealth (SoW). Identify all UBOs regardless of percentage.",
            "UK": "Cross-reference PSC register with Companies House. Verify director identities against disqualified lists.",
            "Singapore": "ACRA verification required. Check for MAS regulatory flags. Verify UBOs via Register of Registrable Controllers."
        }
        return rules_db.get(jurisdiction, "Identify all Ultimate Beneficial Owners (UBOs). Check global sanctions lists. Verify legal incorporation and operational status.")

import os

class ReasoningAgent:
    """
    The core reasoning agent utilizing frontier models for complex planning and synthesis.
    Implements a ReAct loop with self-critique and Tree-of-Thoughts branching.
    """
    def __init__(self, frontier_model: str = "gpt-4o", critic_model: str = "gemini-1.5-flash"):
        if os.getenv("OPENAI_API_KEY") == "ollama":
            self.llm = ChatOpenAI(
                model="llama3",
                openai_api_base=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1"),
                openai_api_key="ollama"
            )
            # Use phi3 for the critic as it's lightweight and already present
            self.critic = CriticAgent(model_name="phi3")
        else:
            self.llm = ChatOpenAI(model=frontier_model)
            self.critic = CriticAgent(model_name=critic_model)

    async def cross_reference(self, registry_data: RegistryData, document_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Legacy method kept for compatibility with existing nodes, but enhanced with better prompting.
        """
        facts_str = "\n".join([f"- {f['content']} (Source: {f['metadata'].get('doc_id')})" for f in document_facts])
        
        prompt = f"""
        You are a Senior KYB Compliance Investigator. 
        Compare 'Official Registry Data' with 'Extracted Document Facts' and identify contradictions.
        
        Official Registry Data:
        {registry_data.model_dump_json() if registry_data else "None"}
        
        Extracted Document Facts:
        {facts_str}
        
        Format your response as a JSON list of objects:
        [
            {{"fact": "...", "contradiction": true/false, "explanation": "...", "severity": "low/medium/high"}}
        ]
        """
        response = await self.llm.ainvoke(prompt)
        try:
            return json.loads(response.content)
        except:
            return [{"error": "Failed to parse reasoning output"}]

    async def run_investigation_loop(self, state: AgentState) -> AgentState:
        """
        The main reasoning loop (ReAct + Critic).
        """
        jurisdiction = state["results"].registry.jurisdiction if state["results"].registry else "Unknown"
        history = []
        
        for i in range(3): # Limit to 3 reasoning cycles for demo
            # 1. Generate Thought and Plan
            step_output = await self._generate_step(state, history)
            
            # 2. Add Observation (In a real system, this happens via tool execution in LangGraph)
            # For the purpose of this engine, we simulate tool interaction if needed
            if not step_output.observation:
                step_output.observation = "Awaiting execution of: " + (step_output.tool_selection or "Next Step")
            
            # 3. Get Critique from Critic Agent (Gemini)
            context = {"history": [s.model_dump() for s in history]}
            step_output.critique = await self.critic.evaluate_step(step_output, context, jurisdiction)
            
            # 4. Record History
            history.append(step_output)
            state["logs"].append(f"Investigation Step {i+1}: {step_output.thought}")
            state["logs"].append(f"Critic Feedback: {step_output.critique[:100]}...")
            
            # 5. Tree-of-Thoughts Branching for Ambiguity
            if step_output.confidence < 0.6:
                state["logs"].append("High ambiguity detected. Spawning alternative hypotheses.")
                branches = await self._explore_branches(state, step_output)
                # Store branches in state for final synthesis
                if "hypotheses" not in state:
                    state["hypotheses"] = []
                state["hypotheses"].extend([h.model_dump() for h in branches])
                
            if step_output.tool_selection == "FINISH":
                break

        # 6. Final Synthesis
        synthesis = await self._synthesize_findings(state)
        
        # 7. Generate XAI Artifact
        xai_report = await self.generate_xai_artifact(state, synthesis)
        
        # 8. Update State
        state["reasoning_history"] = [s.model_dump() for s in history]
        
        # Update Risk Assessment with synthesized data
        if not state["results"].risk_assessment:
            state["results"].risk_assessment = RiskRating(score=synthesis.confidence_score, factors=[], summary="")
            
        state["results"].risk_assessment.summary = (
            f"REASONING SYNTHESIS:\n{synthesis.final_summary}\n\n"
            f"PRIMARY HYPOTHESIS: {synthesis.primary_hypothesis.description} "
            f"(Confidence: {synthesis.primary_hypothesis.confidence_score})\n"
            f"REGULATORY ALIGNMENT: {synthesis.regulatory_alignment}"
        )
        state["results"].risk_assessment.factors = list(synthesis.feature_importance.keys())
        state["results"].xai_report = xai_report
        
        # Sign the result (Simulated signing)
        report_json = xai_report.model_dump_json()
        signature = hashlib.sha256(report_json.encode()).hexdigest()
        state["results"].signature = signature
        
        # Persist to Audit Store
        profile_id = state.get("registration_number") or state["company_query"]
        audit_store.store_xai_explanation(profile_id, xai_report.model_dump(), signature)
        
        return state

    async def generate_xai_artifact(self, state: AgentState, synthesis: Synthesis) -> XAIArtifact:
        """
        Generates a structured XAI artifact for regulators and compliance officers.
        """
        # Generate audience-tailored summaries
        summaries = await self._generate_audience_summaries(state, synthesis)
        
        return XAIArtifact(
            chain_of_thought=state.get("reasoning_history", []),
            sources=synthesis.citations,
            confidence_calibration={
                "score": synthesis.confidence_score,
                "method": "direct_llm_calibration_with_uncertainty_weighting",
                "uncertainty_factors": synthesis.uncertainty_factors
            },
            feature_importance=synthesis.feature_importance,
            summaries=summaries
        )

    async def _generate_audience_summaries(self, state: AgentState, synthesis: Synthesis) -> AudienceSummary:
        prompt = f"""
        Generate two distinct summaries for the following KYB investigation:
        
        Investigation: {synthesis.final_summary}
        Primary Hypothesis: {synthesis.primary_hypothesis.description}
        Risk Factors: {list(synthesis.feature_importance.keys())}
        
        1. Compliance Officer Summary: Focus on operational risk, missing documentation, and specific red flags.
        2. Regulator Summary: Focus on statutory compliance, jurisdictional alignment, and the robustness of the evidence chain.
        
        Output JSON:
        {{
            "compliance_officer": "...",
            "regulator": "..."
        }}
        """
        response = await self.llm.ainvoke(prompt)
        data = json.loads(response.content)
        return AudienceSummary(**data)

    async def _generate_step(self, state: AgentState, history: List[ReasoningStep]) -> ReasoningStep:
        prompt = f"""
        You are a KYB Investigator Agent. Perform a ReAct reasoning step.
        Current Goal: {state.get('current_task', 'Investigate ' + state['company_query'])}
        Current State: {state['results'].model_dump_json()}
        History: {[s.thought for s in history]}
        
        Output a JSON object following this schema:
        {{
            "thought": "...",
            "plan": "...",
            "tool_selection": "name of tool or 'FINISH'",
            "tool_input": {{...}},
            "confidence": 0.0-1.0
        }}
        """
        response = await self.llm.ainvoke(prompt)
        # Simplified parsing
        data = json.loads(response.content)
        return ReasoningStep(**data)

    async def _explore_branches(self, state: AgentState, step: ReasoningStep) -> List[Hypothesis]:
        prompt = f"""
        As a Senior Investigator, given the ambiguity in: {step.thought}
        Generate 2-3 alternative hypotheses for the corporate structure or risk profile.
        Respond in JSON list of objects: [{{"description": "...", "rationale": "...", "confidence_score": 0.0-1.0}}]
        """
        response = await self.llm.ainvoke(prompt)
        data = json.loads(response.content)
        return [Hypothesis(**h) for h in data]

    async def _synthesize_findings(self, state: AgentState) -> Synthesis:
        prompt = f"""
        Final Synthesis of KYB Investigation for {state['company_query']}.
        Analyze all logs and findings:
        {state['logs']}
        
        Provide a final synthesis including:
        - primary and alternative hypotheses
        - regulatory alignment
        - confidence score (0-1)
        - uncertainty factors (why might you be wrong?)
        - feature importance (SHAP-style weighting for key risk factors)
        - citations for all key claims
        
        Output in JSON format matching the 'Synthesis' schema.
        Note: feature_importance should sum to 1.0 or be normalized.
        """
        response = await self.llm.ainvoke(prompt)
        data = json.loads(response.content)
        return Synthesis(**data)
