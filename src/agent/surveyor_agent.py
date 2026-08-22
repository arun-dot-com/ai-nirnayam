import os
import logging
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from src.agent.state import AgentState
from src.pii_masking.anonymizer import PIIMaskingManager
from src.rag.retriever import PolicyRetriever
from src.memory.mem0_manager import Mem0Manager
from src.tools.part_classifier import classify_part
from src.tools.depreciation_calc import get_depreciation_percentage
from src.tools.labour_rates import calculate_painting_costs
from src.policy.policy_registry import PolicyRegistry
# CRITICAL: Load environment variables before initializing the LLM
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize LLM (using gpt-4o-mini for cost-effective, fast entity extraction)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

class SurveyorAgent:
    def __init__(self, vectorstore, redis_url: str = None):
        self.policy_registry = PolicyRegistry()
        self.pii_manager = PIIMaskingManager()
        self.mem0_manager = Mem0Manager()
        self.retriever = PolicyRetriever(vectorstore, k=3)
        
        # Entity Extraction Prompt
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Motor Claims Surveyor. Extract the following information from the garage estimate or claim description. 
            Return ONLY a valid JSON object with these exact keys:
            - "vehicle_age_years": float (e.g., 3.5)
            - "has_zero_depreciation": boolean
            - "has_engine_protect": boolean
            - "vehicle_rc_anonymized": string (look for <ANON_IN_VEHICLE_RC_...> tags)
            - "parts": list of objects, each with "name" (string) and "claimed_cost_inr" (float). If it's a painting/denting labour charge, name it "Painting/Denting Labour"."""),
            ("human", "{masked_text}")
        ])
        self.extraction_chain = self.extraction_prompt | llm

    def verify_policy_node(self, state: AgentState) -> Dict[str, Any]:
        """Gatekeeper Node: Verifies if the vehicle actually has an active policy."""
        logger.info("Executing Policy Verification Gatekeeper...")
        
        policy_number = state.get("policy_number")
        vehicle_rc = state.get("extracted_vehicle_rc")
        
        verification_result = {"status": "UNKNOWN", "message": "No Policy Number or RC provided. Proceeding with manual assumptions."}
        
        # 1. Try to verify by Policy Number first (Most reliable)
        if policy_number:
            verification_result = self.policy_registry.verify_by_policy_number(policy_number)
        # 2. Fallback to Vehicle RC if Policy Number wasn't provided
        elif vehicle_rc:
            verification_result = self.policy_registry.verify_coverage(vehicle_rc)
            
        # 3. If EXPIRED or NOT_FOUND, REJECT the claim immediately
        if verification_result["status"] in ["EXPIRED", "NOT_FOUND"]:
            return {
                "policy_status": verification_result["status"],
                "policy_message": verification_result["message"],
                "verified_add_ons": {},
                "errors": state.get("errors", []) + [f"COVERAGE REJECTED: {verification_result['message']}"]
            }
            
        # 4. If ACTIVE, inject the TRUE add-ons and RC from the database
        if verification_result["status"] == "ACTIVE":
            true_add_ons = verification_result["policy_details"]
            return {
                "policy_status": "ACTIVE",
                "policy_message": verification_result["message"],
                "has_zero_depreciation": true_add_ons["has_zero_dep"],       # Override LLM/Manual guesses
                "has_engine_protect": true_add_ons["has_engine_protect"],    # Override LLM/Manual guesses
                "extracted_vehicle_rc": true_add_ons.get("vehicle_rc", vehicle_rc), # Inject RC from DB
                "verified_add_ons": true_add_ons
            }
            
        # Fallback for UNKNOWN
        return {
            "policy_status": "UNKNOWN",
            "policy_message": verification_result["message"],
            "verified_add_ons": {}
        }

    def extract_entities_node(self, state: AgentState) -> Dict[str, Any]:
        """Node 1: Use LLM to extract structured entities from the masked text."""
        logger.info("Executing Entity Extraction Node...")
        
        # CRITICAL FIX: If entities were already provided (e.g., via Manual Entry UI), 
        # skip LLM extraction entirely to preserve exact user inputs.
        if state.get("extracted_parts"):
            logger.info("✅ Entities already provided in state (Manual Entry). Skipping LLM extraction.")
            return {
                "vehicle_age_years": state.get("vehicle_age_years", 0.0),
                "has_zero_depreciation": state.get("has_zero_depreciation", False),
                "has_engine_protect": state.get("has_engine_protect", False),
                "extracted_vehicle_rc": state.get("extracted_vehicle_rc"),
                "extracted_parts": state.get("extracted_parts", []),
                "errors": state.get("errors", [])
            }

        try:
            response = self.extraction_chain.invoke({"masked_text": state["masked_input_text"]})
            # Clean up markdown JSON formatting if the LLM adds it
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            extracted = json.loads(content)
            
            return {
                "vehicle_age_years": float(extracted.get("vehicle_age_years", 0.0)),
                "has_zero_depreciation": bool(extracted.get("has_zero_depreciation", False)),
                "has_engine_protect": bool(extracted.get("has_engine_protect", False)),
                "extracted_vehicle_rc": extracted.get("vehicle_rc_anonymized"),
                "extracted_parts": extracted.get("parts", []),
                "errors": state.get("errors", [])
            }
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return {"errors": state.get("errors", []) + [f"Extraction failed: {str(e)}"]}

    def retrieve_context_node(self, state: AgentState) -> Dict[str, Any]:
        """Node 2: Query RAG for IMT rules and Mem0 for vehicle history."""
        logger.info("Executing Context Retrieval Node...")
        rag_clauses = []
        memory_history = []
        
        # 1. RAG Retrieval based on extracted parts
        part_names = [p["name"] for p in state.get("extracted_parts", [])]
        if part_names:
            query = f"Depreciation rules and exclusions for: {', '.join(part_names)}"
            rag_clauses = self.retriever.retrieve_clauses(query)
            
        # 2. Mem0 Retrieval based on anonymized RC
        rc = state.get("extracted_vehicle_rc")
        if rc and rc.startswith("<ANON"):
            memory_history = self.mem0_manager.get_vehicle_history(
                anonymized_vehicle_id=rc, 
                query="past claims, NCB status, and previous damages"
            )
            
        return {
            "rag_clauses": rag_clauses,
            "memory_history": memory_history
        }

    def calculate_depreciation_node(self, state: AgentState) -> Dict[str, Any]:
        """Node 3: Deterministic tool calling for math and classification."""
        logger.info("Executing Deterministic Calculation Node...")
        tool_results = []
        vehicle_age = state.get("vehicle_age_years", 0.0)
        has_zero_dep = state.get("has_zero_depreciation", False)
        has_engine_protect = state.get("has_engine_protect", False)
        
        for part in state.get("extracted_parts", []):
            part_name = part["name"]
            claimed_cost = float(part.get("claimed_cost_inr", 0.0))
            
            # 1. Classify Part
            category = classify_part(part_name)
            
            # 2. Check Engine Protect Exclusion (Added missing depreciation_amount_inr)
            if category == "MECHANICAL_EXCLUSION" and "engine" in part_name.lower() and not has_engine_protect:
                tool_results.append({
                    "part_name": part_name,
                    "category": category,
                    "claimed_cost_inr": claimed_cost,
                    "depreciation_percentage": 100.0,
                    "depreciation_amount_inr": claimed_cost,  # <-- FIX: 100% of claimed cost
                    "approved_cost_inr": 0.0,
                    "reason": "Mechanical/Consequential damage excluded. Engine Protect add-on not found."
                })
                continue
                
            # 3. Handle Painting/Labour separately (Added missing depreciation fields)
            if category == "LABOUR_PAINTING":
                painting_result = calculate_painting_costs(claimed_cost, has_zero_dep, vehicle_age)
                dep_amount = painting_result["material_depreciation_inr"]
                
                # Calculate the effective overall depreciation percentage for the consolidated bill
                dep_pct = round((dep_amount / claimed_cost) * 100, 2) if claimed_cost > 0 else 0.0
                
                tool_results.append({
                    "part_name": part_name,
                    "category": category,
                    "claimed_cost_inr": claimed_cost,
                    "depreciation_percentage": dep_pct,         # <-- FIX: Effective overall %
                    "depreciation_amount_inr": dep_amount,      # <-- FIX: The actual INR amount
                    "calculation_details": painting_result,
                    "approved_cost_inr": painting_result["net_approved_painting_inr"],
                    "reason": f"Painting split: 25% material, 75% labour. Material depreciated at {painting_result['material_depreciation_percentage']}%."
                })
                continue
                
            # 4. Standard Depreciation Calculation
            dep_pct = get_depreciation_percentage(category, vehicle_age, has_zero_dep, part_name)
            dep_amount = claimed_cost * (dep_pct / 100.0)
            approved_cost = claimed_cost - dep_amount
            
            tool_results.append({
                "part_name": part_name,
                "category": category,
                "claimed_cost_inr": claimed_cost,
                "depreciation_percentage": dep_pct,
                "depreciation_amount_inr": round(dep_amount, 2),
                "approved_cost_inr": round(approved_cost, 2),
                "reason": f"Standard IMT depreciation applied for {category} at {dep_pct}%."
            })
            
        return {"tool_calculations": tool_results}

    def finalize_assessment_node(self, state: AgentState) -> Dict[str, Any]:
        """Node 4: Compile final structured assessment."""
        logger.info("Executing Final Assessment Node...")
        
        total_claimed = sum(t.get("claimed_cost_inr", 0) for t in state.get("tool_calculations", []))
        total_approved = sum(t.get("approved_cost_inr", 0) for t in state.get("tool_calculations", []))
        
        # Detect if user lied about add-ons in the raw text vs database truth
        warnings = []
        raw_text_lower = state.get("raw_input_text", "").lower()
        verified = state.get("verified_add_ons", {})
        
        # Check for Engine Protect variations (e.g., "engine cover", "engine protection")
        if verified.get("has_engine_protect") is False and any(kw in raw_text_lower for kw in ["engine protect", "engine cover", "engine protection"]):
            warnings.append("⚠️ Claim text mentions 'Engine Cover/Protect', but policy records show this add-on is NOT active. Evaluated without it.")
            
        # Check for Zero Dep variations (e.g., "zero dep", "bumper to bumper")
        if verified.get("has_zero_dep") is False and any(kw in raw_text_lower for kw in ["zero dep", "zero depreciation", "bumper to bumper", "nil depreciation"]):
            warnings.append("⚠️ Claim text mentions 'Zero Depreciation', but policy records show this add-on is NOT active. Evaluated without it.")

        final_assessment = {
            "claim_id": state.get("claim_id"),
            "vehicle_age_years": state.get("vehicle_age_years"),
            "policy_status": state.get("policy_status", "UNKNOWN"),
            "policy_message": state.get("policy_message", "No policy verified."),
            "add_ons_detected": {
                "zero_depreciation": state.get("has_zero_depreciation"),
                "engine_protect": state.get("has_engine_protect")
            },
            "ncb_history_note": "No prior claims found." if not state.get("memory_history") else f"Prior history: {state['memory_history'][0].get('content')}",
            "line_items": state.get("tool_calculations", []),
            "system_warnings": warnings, # <-- This passes the warnings to the schema
            "summary": {
                "total_claimed_inr": round(total_claimed, 2),
                "total_approved_inr": round(total_approved, 2),
                "total_depreciation_inr": round(total_claimed - total_approved, 2)
            }
        }
        
        return {"final_assessment": final_assessment}

    def build_graph(self):
        """Constructs and compiles the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("extract", self.extract_entities_node)
        workflow.add_node("verify", self.verify_policy_node)      # <-- NEW GATEKEEPER
        workflow.add_node("retrieve", self.retrieve_context_node)
        workflow.add_node("calculate", self.calculate_depreciation_node)
        workflow.add_node("finalize", self.finalize_assessment_node)
        
        workflow.set_entry_point("extract")
        workflow.add_edge("extract", "verify")
        
        # Conditional edge: If policy fails, skip straight to finalize (rejection)
        workflow.add_conditional_edges(
            "verify",
            lambda state: "finalize" if state.get("policy_status") in ["EXPIRED", "NOT_FOUND"] else "retrieve",
            {
                "retrieve": "retrieve",
                "finalize": "finalize"
            }
        )
        
        workflow.add_edge("retrieve", "calculate")
        workflow.add_edge("calculate", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
