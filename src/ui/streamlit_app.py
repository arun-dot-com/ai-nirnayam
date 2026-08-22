import sys
import os

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import json
from dotenv import load_dotenv

from src.observability.langsmith_setup import setup_langsmith
from src.pii_masking.anonymizer import PIIMaskingManager
from src.rag.vector_store import VectorStoreManager
from src.agent.surveyor_agent import SurveyorAgent
from src.guardrails.validators import validate_final_assessment
from src.policy.policy_registry import PolicyRegistry

# Load environment variables
load_dotenv()
setup_langsmith()

st.set_page_config(page_title="Nirnayam", page_icon="⚖️", layout="wide")

st.title("⚖️ Nirnayam: Autonomous Motor OD Claim Adjudicator")
st.markdown("Enterprise-grade surveyor assistant with strict IMT compliance, PII masking, and mathematical guardrails.")

import os

@st.cache_resource
def load_system_components():
    with st.spinner("Loading AI components and Policy Registry..."):
        # 1. Load Vector Store (RAG) - WITH CLOUD FALLBACK
        vs_manager = VectorStoreManager(persist_directory="data/faiss_index")
        
        # If the index doesn't exist (e.g., first boot on Streamlit Cloud), build it!
        if not os.path.exists("data/faiss_index/index.faiss"):
            st.warning("🏗️ FAISS index not found. Building it now... (Takes ~30 seconds)")
            from src.ingestion.pdf_parser import extract_text_from_pdf
            from src.ingestion.chunking import chunk_text
            from langchain_openai import OpenAIEmbeddings
            from langchain_community.vectorstores import FAISS
            
            # Simple inline build for cloud initialization
            all_docs = []
            for folder in ["data/raw_imt_tariffs", "data/policy_wordings"]:
                if os.path.exists(folder):
                    for pdf_file in os.listdir(folder):
                        if pdf_file.endswith(".pdf"):
                            text = extract_text_from_pdf(os.path.join(folder, pdf_file))
                            all_docs.extend(chunk_text(text))
                            
            if all_docs:
                embedder = OpenAIEmbeddings(model="text-embedding-3-small")
                vectorstore = FAISS.from_documents(all_docs, embedder)
                vs_manager.save_index(vectorstore)
            else:
                st.error("No PDFs found in data/ folders to build index!")
                st.stop()
                
        vectorstore = vs_manager.load_index()
        
        # 2. Initialize Agent & Policy Registry
        agent = SurveyorAgent(vectorstore=vectorstore)
        return agent.pii_manager, agent.build_graph(), agent, PolicyRegistry()
pii_manager, agent_graph, agent, policy_registry = load_system_components()

# ==========================================
# SESSION STATE FOR GATEKEEPER FLOW
# ==========================================
if "policy_verified" not in st.session_state:
    st.session_state.policy_verified = False
    st.session_state.policy_details = None
    st.session_state.policy_error = None

# ==========================================
# STEP 1: POLICY VERIFICATION GATEKEEPER
# ==========================================
st.subheader("🛡️ Policy Verification")
st.markdown("Enter the Policy Number to verify active coverage before proceeding with claim details.")

col1, col2 = st.columns([1, 3])
with col1:
    policy_input = st.text_input("Policy Number", placeholder="e.g., POL-MH-9981", key="gatekeeper_policy_input")
with col2:
    st.markdown("<br>", unsafe_allow_html=True) # Spacer
    if st.button("🔍 Verify Policy", type="primary", key="btn_verify"):
        if not policy_input.strip():
            st.session_state.policy_error = "Please enter a policy number."
            st.session_state.policy_verified = False
        else:
            result = policy_registry.verify_by_policy_number(policy_input.strip())
            if result["status"] == "ACTIVE":
                st.session_state.policy_verified = True
                st.session_state.policy_details = result["policy_details"]
                st.session_state.policy_error = None
            else:
                st.session_state.policy_verified = False
                st.session_state.policy_details = None
                st.session_state.policy_error = result["message"]

# Display Verification Status
if st.session_state.policy_error:
    st.error(f"🚫 **Access Denied:** {st.session_state.policy_error}")

elif st.session_state.policy_verified and st.session_state.policy_details:
    st.success(f"✅ **Policy Verified Successfully!** \n\n **Policy:** `{st.session_state.policy_details['policy_number']}` | **Owner:** {st.session_state.policy_details['owner_name']} | **Vehicle:** `{st.session_state.policy_details['vehicle_rc']}`")
    
    # Optional: Add a button to reset and check a different policy
    if st.button("🔄 Check Different Policy", key="btn_reset_policy"):
        st.session_state.policy_verified = False
        st.session_state.policy_details = None
        st.session_state.policy_error = None
        st.rerun()

    st.markdown("---")

    # ==========================================
    # STEP 2: CLAIM ENTRY (Only visible if verified)
    # ==========================================
    tab1, tab2 = st.tabs(["✨ AI Auto-Extract (Recommended)", "⌨️ Manual Structured Entry"])

    # Initialize session state for manual line items
    if "line_items" not in st.session_state:
        st.session_state.line_items = [{"part_name": "", "claimed_cost_inr": 0.0}]

    def add_line_item():
        st.session_state.line_items.append({"part_name": "", "claimed_cost_inr": 0.0})

    def remove_line_item(index):
        if len(st.session_state.line_items) > 1:
            st.session_state.line_items.pop(index)

    # ==========================================
    # TAB 1: AI AUTO-EXTRACT
    # ==========================================
    with tab1:
        st.subheader("Paste Raw Garage Estimate or Surveyor Notes")
        claim_id_ai = st.text_input("Claim ID", value="CLM-AI-001", key="ai_claim_id")
        
        # Pre-fill the verified vehicle RC to help the LLM, but allow editing if needed
        verified_rc = st.session_state.policy_details["vehicle_rc"]
        raw_text = st.text_area(
            "Claim Description",
            height=150,
            placeholder=f"Example: Vehicle {verified_rc}, age 3.5 years. Damaged: Front Bumper (Rs. 4000).",
            key="ai_raw_text"
        )
        
        if st.button("🔍 Extract & Process Claim", type="primary", key="btn_ai"):
            if not raw_text.strip():
                st.warning("Please enter a claim description.")
            else:
                with st.spinner("AI is extracting entities, retrieving RAG context, and calculating deterministic depreciation..."):
                    try:
                        # Mask PII
                        masked_text, active_claim_id = pii_manager.mask_pii(raw_text, claim_id=claim_id_ai)
                        
                        initial_state = {
                            "claim_id": active_claim_id,
                            "policy_number": st.session_state.policy_details["policy_number"], # Hardcoded from verification
                            "raw_input_text": raw_text,
                            "masked_input_text": masked_text,
                            "vehicle_age_years": 0.0,
                            "has_zero_depreciation": False, # Will be overridden by gatekeeper node
                            "has_engine_protect": False,    # Will be overridden by gatekeeper node
                            "extracted_parts": [],
                            "extracted_vehicle_rc": verified_rc,
                            "rag_clauses": [],
                            "memory_history": [],
                            "tool_calculations": [],
                            "final_assessment": {},
                            "errors": []
                        }
                        
                        result = agent_graph.invoke(initial_state)
                        
                        if result.get("errors"):
                            st.error("Agent encountered errors:")
                            for err in result["errors"]:
                                st.error(f"- {err}")
                        else:
                            validated_assessment = validate_final_assessment(result["final_assessment"])
                            st.session_state["last_assessment"] = validated_assessment
                            st.success("✅ Claim processed and validated successfully!")
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {str(e)}")

    # ==========================================
    # TAB 2: MANUAL STRUCTURED ENTRY
    # ==========================================
    with tab2:
        st.subheader("Enter Claim Details Directly")
        col1, col2, col3 = st.columns(3)
        with col1:
            claim_id_manual = st.text_input("Claim ID", value="CLM-MAN-001", key="man_claim_id")
        with col2:
            vehicle_age = st.number_input("Vehicle Age (Years)", min_value=0.0, max_value=15.0, step=0.5, value=3.5, key="man_age")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            # Show verified add-ons as read-only info
            zd = st.session_state.policy_details["has_zero_dep"]
            ep = st.session_state.policy_details["has_engine_protect"]
            st.info(f"**Verified Add-ons:**\nZero Dep: {'✅' if zd else '❌'}\nEngine Protect: {'✅' if ep else '❌'}")

        st.markdown("### 🛠️ Damaged Parts & Labour")
        for i, item in enumerate(st.session_state.line_items):
            cols = st.columns([4, 2, 1])
            with cols[0]:
                item["part_name"] = st.text_input("Part Name / Labour Description", value=item["part_name"], key=f"part_{i}")
            with cols[1]:
                item["claimed_cost_inr"] = st.number_input("Claimed Cost (₹)", min_value=0.0, step=100.0, value=item["claimed_cost_inr"], key=f"cost_{i}")
            with cols[2]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("❌", key=f"del_{i}"):
                    remove_line_item(i)
                    st.rerun()

        st.button("➕ Add Another Line Item", on_click=add_line_item)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ Calculate Deterministic Assessment", type="primary", key="btn_manual"):
            masked_text, active_claim_id = pii_manager.mask_pii(
                f"Vehicle {verified_rc} age {vehicle_age}. Parts: {', '.join([i['part_name'] for i in st.session_state.line_items])}", 
                claim_id=claim_id_manual
            )
            
            initial_state = {
                "claim_id": active_claim_id,
                "policy_number": st.session_state.policy_details["policy_number"], # Hardcoded from verification
                "raw_input_text": "Manual Entry",
                "masked_input_text": masked_text,
                "vehicle_age_years": float(vehicle_age),
                "has_zero_depreciation": bool(zd), # Use verified data
                "has_engine_protect": bool(ep),    # Use verified data
                "extracted_parts": [{"name": i["part_name"], "claimed_cost_inr": float(i["claimed_cost_inr"])} for i in st.session_state.line_items if i["part_name"]],
                "extracted_vehicle_rc": verified_rc,
                "rag_clauses": [],
                "memory_history": [],
                "tool_calculations": [],
                "final_assessment": {},
                "errors": []
            }
            
            with st.spinner("Calculating deterministic depreciation and validating guardrails..."):
                try:
                    result = agent_graph.invoke(initial_state)
                    
                    if result.get("errors"):
                        st.error("Errors:")
                        for err in result["errors"]:
                            st.error(f"- {err}")
                    else:
                        validated_assessment = validate_final_assessment(result["final_assessment"])
                        st.session_state["last_assessment"] = validated_assessment
                        st.success("✅ Assessment calculated successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # ==========================================
    # RESULTS DISPLAY (Shared across tabs)
    # ==========================================
    if "last_assessment" in st.session_state:
        assessment = st.session_state["last_assessment"]
        
        st.markdown("---")
        st.subheader("📊 Final Assessment Summary")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Claimed", f"₹{assessment.summary.total_claimed_inr:,.2f}")
        col2.metric("Total Depreciation", f"₹{assessment.summary.total_depreciation_inr:,.2f}", delta=f"-{assessment.summary.total_depreciation_inr:,.2f}", delta_color="inverse")
        col3.metric("Net Approved", f"₹{assessment.summary.total_approved_inr:,.2f}", delta_color="normal")
        
        st.markdown(f"**📜 NCB / History Note:** {assessment.ncb_history_note}")
        
        st.markdown("### 📝 Line Item Breakdown")
        if assessment.system_warnings:
            st.markdown("### ⚠️ System Warnings")
            for warning in assessment.system_warnings:
                st.warning(warning)

        for item in assessment.line_items:
            with st.expander(f"**{item.part_name}** ({item.category}) — Approved: **₹{item.approved_cost_inr:,.2f}**"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Claimed", f"₹{item.claimed_cost_inr:,.2f}")
                c2.metric("Depreciation", f"{item.depreciation_percentage}% (₹{item.depreciation_amount_inr:,.2f})")
                c3.metric("Approved", f"₹{item.approved_cost_inr:,.2f}")
                st.info(f"**Reasoning:** {item.reason}")

        with st.expander("🔧 View Raw Validated JSON (Audit Trail)"):
            st.json(assessment.model_dump())

else:
    # Fallback message when no policy is verified yet
    st.markdown("---")
    st.info("👆 **Please verify a policy number above to begin claim adjudication.**")