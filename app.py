import streamlit as st
import google.generativeai as genai
import json
import time
import markdown
from fpdf import FPDF

# --- PAGE SETUP ---
st.set_page_config(page_title="Smart ATS CV Builder", page_icon="⚡", layout="wide")
st.title("⚡ Smart ATS CV & Cover Letter Builder")
st.markdown("Din me 100 jobs par apply karein! Apni existing CV ka text paste karein, JD daalein aur magic dekhein.")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("⚙️ Settings")
api_key = st.sidebar.text_input("Enter your Gemini API Key:", type="password")
selected_model = st.sidebar.selectbox(
    "🧠 Select AI Model:", 
    [
        "gemini-3.5-flash-lite", 
        "gemini-3.5-flash", 
        "gemini-3.8-flash", 
        "gemini-3.7-flash"
    ]
)
st.sidebar.caption("⚡ Tip: 'gemini-3.5-flash-lite' is fastest for free tier.")

# --- HELPER FUNCTIONS ---
def call_gemini_with_retry(prompt, model, retries=3, wait_time=5):
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(wait_time)
            else:
                raise e

def create_pdf(md_text):
    md_text = md_text.replace("’", "'").replace("‘", "'")
    md_text = md_text.replace("“", '"').replace("”", '"')
    md_text = md_text.replace("–", "-").replace("—", "-")
    md_text = md_text.replace("…", "...").replace("•", "-") 
    
    html_text = markdown.markdown(md_text)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=11)
    pdf.write_html(html_text)
    return bytes(pdf.output())

# ==========================================
# STEP 1: RAW PROFILE UPLOAD
# ==========================================
st.subheader("👤 Step 1: Paste Your Existing CV/Profile")
st.markdown("Apni purani CV, LinkedIn profile, ya raw text yahan paste karein. AI khud details extract kar lega.")
raw_profile = st.text_area(
    "Paste your complete profile text here:", 
    height=250, 
    placeholder="Example:\nNadir Khan\nCivil Engineer\nExperience: 3 Years...\nEducation: NUST..."
)

# ==========================================
# STEP 2: JOB DESCRIPTION
# ==========================================
st.subheader("🎯 Step 2: Target Job Description")
job_description = st.text_area("Yahan Target Job Description paste karein:", height=150)

generate_btn = st.button("✨ Generate Optimized Application", use_container_width=True)

# --- OPTIMIZED BACKEND LOGIC (2-CHAIN SYSTEM) ---
if generate_btn:
    if not api_key:
        st.warning("⚠️ Please sidebar me apni Gemini API Key enter karein.")
        st.stop()
    if not raw_profile:
        st.warning("⚠️ Please Step 1 me apni profile ya CV ka text paste karein.")
        st.stop()
    if not job_description:
        st.warning("⚠️ Please Step 2 me Job Description paste karein.")
        st.stop()

    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"Model setup error: {e}")
        st.stop()

    with st.spinner(f"🔍 Analyzing Profile & JD..."):
        chain_1_prompt = f"""
        Role: Expert ATS Evaluator and HR Analyst.
        Context: Analyze the Job Description and match it with the Candidate's Raw Profile.
        
        Job Description: {job_description}
        Candidate Profile: {raw_profile}
        
        Task: 
        1. Extract the candidate's full name from their profile text.
        2. Calculate Match Score (0-100).
        3. Output strictly in JSON format.
        
        JSON Format MUST be exactly like this:
        {{
            "candidate_name": "Extracted Name",
            "match_score": 85,
            "eligibility": "Eligible", 
            "matched_skills": ["skill1", "skill2"],
            "missing_skills": ["skill3"]
        }}
        """
        try:
            res1_text = call_gemini_with_retry(chain_1_prompt, model)
            clean_res1 = res1_text.replace("```json", "").replace("```", "").strip()
            match_result = json.loads(clean_res1)
        except Exception as e:
            st.error(f"Chain 1 Error: Server busy ya JSON format issue. Error: {e}")
            st.stop()

    if match_result.get("eligibility") == "Not Eligible" and match_result.get("match_score", 0) < 50:
        st.error(f"⚠️ Match Score: {match_result.get('match_score')}% - Yeh job aapki profile se match nahi karti. Application stopped to save tokens.")
        st.stop()

    st.success(f"✅ Profile Matched! Score: {match_result.get('match_score')}%")
    tab1, tab2 = st.tabs(["📄 ATS Resume", "✉️ Cover Letter"])
    
    cv_text = ""
    cl_text = ""

    with st.spinner("✍️ Generating Tailored CV & Cover Letter..."):
        chain_2_prompt = f"""
        Role: Expert Resume Writer and Career Coach.
        Raw Profile: {raw_profile}
        Job Description: {job_description}
        Matched Skills to Highlight: {match_result.get('matched_skills')}
        
        Task: Generate an ATS-friendly Resume AND a persuasive Cover Letter based ONLY on the Candidate's Raw Profile.
        Constraints: Use Action Verbs. DO NOT hallucinate facts.
        
        FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
        [START_RESUME]
        (Write Resume Markdown Here)
        [END_RESUME]
        
        [START_COVER_LETTER]
        (Write Cover Letter Markdown Here)
        [END_COVER_LETTER]
        """
        try:
            res2_text = call_gemini_with_retry(chain_2_prompt, model, wait_time=8)
            try:
                cv_text = res2_text.split("[START_RESUME]")[1].split("[END_RESUME]")[0].strip()
                cl_text = res2_text.split("[START_COVER_LETTER]")[1].split("[END_COVER_LETTER]")[0].strip()
            except IndexError:
                parts = res2_text.split("Dear")
                cv_text = parts[0].strip()
                cl_text = "Dear" + parts[1].strip() if len(parts) > 1 else ""
                
        except Exception as e:
            st.error(f"Chain 2 Error: {e}")
            st.stop()

    # --- RENDER OUTPUT & PDF BUTTONS ---
    extracted_name = match_result.get("candidate_name", "Candidate")
    safe_name = extracted_name.replace(" ", "_")
    
    with tab1:
        if cv_text:
            st.markdown(cv_text)
            st.download_button("📥 Download CV as PDF", data=create_pdf(cv_text), file_name=f"{safe_name}_ATS_CV.pdf", mime="application/pdf")
            
    with tab2:
        if cl_text:
            st.markdown(cl_text)
            st.download_button("📥 Download Cover Letter as PDF", data=create_pdf(cl_text), file_name=f"{safe_name}_Cover_Letter.pdf", mime="application/pdf")

st.markdown("---")
st.markdown("Developed with ❤️ by **Engineer Nadir Khan** (Gen AI App Developer)")
