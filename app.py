import streamlit as st
import google.generativeai as genai
import json
import time
import re
from fpdf import FPDF

# --- PAGE SETUP ---
st.set_page_config(page_title="Smart ATS CV Builder", page_icon="⚡", layout="wide")
st.title("⚡ Smart ATS CV & Cover Letter Builder")
st.markdown("Commercial ATS Engine: AI Profile Filtering, Match Scoring & Professional Layout Generation.")

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
st.sidebar.caption("⚡ 'gemini-3.5-flash-lite' quota aur speed ke liye optimal hai.")

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

# --- PROFESSIONAL ATS PDF ENGINE ---
class ATSResumePDF(FPDF):
    def header(self):
        pass
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

def build_ats_pdf(raw_text):
    text = raw_text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("…", "...").replace("•", "-")

    pdf = ATSResumePDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=16, top=16, right=16)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    lines = text.split("\n")
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            pdf.ln(2)
            continue
            
        if clean_line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(20, 20, 20)
            name_text = clean_line.replace("# ", "").strip()
            pdf.cell(0, 7, name_text, ln=True, align="C")
            pdf.ln(1)
            
        elif clean_line.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(30, 41, 59)
            heading_text = clean_line.replace("## ", "").strip().upper()
            pdf.cell(0, 6, heading_text, ln=True)
            curr_y = pdf.get_y()
            pdf.set_draw_color(180, 180, 180)
            pdf.set_line_width(0.3)
            pdf.line(16, curr_y, 194, curr_y)
            pdf.ln(2)
            
        elif clean_line.startswith("### "):
            sub_text = clean_line.replace("### ", "").strip()
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 5, sub_text, ln=True)
            
        elif clean_line.startswith("- ") or clean_line.startswith("* "):
            bullet_body = clean_line[2:].strip()
            clean_bullet = re.sub(r"\*\*(.*?)\*\*", r"\1", bullet_body)
            pdf.set_font("Helvetica", size=9.5)
            pdf.set_text_color(50, 50, 50)
            pdf.set_x(18)
            pdf.cell(4, 4.5, chr(149), ln=False)
            pdf.multi_cell(0, 4.5, clean_bullet)
            pdf.ln(0.5)
            
        else:
            pdf.set_font("Helvetica", size=9.5)
            pdf.set_text_color(60, 60, 60)
            clean_body = re.sub(r"\*\*(.*?)\*\*", r"\1", clean_line)
            if pdf.get_y() < 40 and ("|" in clean_body or "@" in clean_body):
                pdf.cell(0, 5, clean_body, ln=True, align="C")
            else:
                pdf.multi_cell(0, 4.5, clean_body)
                pdf.ln(0.5)
                
    return bytes(pdf.output())

# ==========================================
# UI: USER INPUTS
# ==========================================
st.subheader("👤 Step 1: Candidate Master Profile")
raw_profile = st.text_area("Paste complete profile text here:", height=200)

st.subheader("🎯 Step 2: Target Job Description")
job_description = st.text_area("Paste target Job Description (JD) here:", height=150)

generate_btn = st.button("✨ Evaluate & Generate ATS Application", use_container_width=True)

# ==========================================
# BACKEND LOGIC
# ==========================================
if generate_btn:
    if not api_key:
        st.warning("⚠️ Please sidebar me Gemini API Key enter karein.")
        st.stop()
    if not raw_profile or not job_description:
        st.warning("⚠️ Please Step 1 aur Step 2 dono fill karein.")
        st.stop()

    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"Model initialization error: {e}")
        st.stop()

    # --- CHAIN 1: EXTRACTOR & EVALUATOR ---
    with st.spinner(f"🔍 Analyzing JD & Evaluating Profile via {selected_model}..."):
        chain_1_prompt = f"""
        Role: Senior Technical Recruiter & ATS Algorithm Specialist.
        
        Job Description:
        {job_description}
        
        Candidate Profile:
        {raw_profile}
        
        Task:
        1. Extract the exact full name of the candidate.
        2. Calculate a realistic ATS Match Score (0-100).
        3. Identify 3-4 Key Strengths (why they are a good fit).
        4. Identify 2-3 Weaknesses or Missing Skills (what they lack based on JD).
        5. Identify elements to exclude for the tailored CV.
        
        Output MUST be strict JSON only:
        {{
            "candidate_name": "Full Name",
            "match_score": 85,
            "eligibility": "Eligible",
            "strengths": ["Matched Primavera P6", "3 years of site supervision"],
            "weaknesses": ["No mention of multistory buildings", "Missing advanced AutoCAD details"],
            "skills_to_include": ["skill1", "skill2"],
            "elements_to_exclude": ["unrelated item 1"]
        }}
        """
        try:
            res1_text = call_gemini_with_retry(chain_1_prompt, model)
            clean_res1 = res1_text.replace("```json", "").replace("```", "").strip()
            match_result = json.loads(clean_res1)
        except Exception as e:
            st.error(f"Chain 1 Error: {e}")
            st.stop()

    # --- UI: ATS EVALUATION DASHBOARD ---
    st.markdown("---")
    st.markdown("### 📊 ATS Match Evaluation Report")
    
    score = match_result.get('match_score', 0)
    
    col1, col2, col3 = st.columns([1, 2, 2])
    
    with col1:
        st.metric(label="ATS Match Score", value=f"{score}%")
        if score >= 70:
            st.success("High Probability of Shortlisting")
        elif score >= 50:
            st.warning("Moderate Fit - Needs Tailoring")
        else:
            st.error("Low Probability - Consider Missing Skills")
            
    with col2:
        st.markdown("#### ✅ Candidate Strengths")
        for strength in match_result.get('strengths', []):
            st.markdown(f"- {strength}")
            
    with col3:
        st.markdown("#### ⚠️ Weaknesses / Missing")
        weaknesses = match_result.get('weaknesses', [])
        if weaknesses:
            for weakness in weaknesses:
                st.markdown(f"- {weakness}")
        else:
            st.markdown("- None identified.")

    if match_result.get("eligibility") == "Not Eligible" and score < 50:
        st.error("⚠️ Application stopped to save tokens due to low match score.")
        st.stop()

    st.markdown("---")
    
    # --- CHAIN 2: TAILORED BUILDER ---
    tab1, tab2 = st.tabs(["📄 Tailored ATS CV", "✉️ Targeted Cover Letter"])
    cv_text, cl_text = "", ""

    with st.spinner("✍️ Compiling Targeted ATS Application..."):
        chain_2_prompt = f"""
        Role: Professional Executive Resume Strategist.
        Raw Profile Data: {raw_profile}
        Target Job Description: {job_description}
        Matched Skills to Highlight: {match_result.get('skills_to_include')}
        
        Mandatory Directives:
        1. SELECTIVE FILTERING: Include ONLY relevant experiences/skills. Omit unrelated data.
        2. ATS STRUCTURE:
           - '# [Candidate Name]' at top
           - Centered contact line (Email | Phone | Location)
           - '## PROFESSIONAL SUMMARY' 
           - '## CORE COMPETENCIES'
           - '## PROFESSIONAL EXPERIENCE'
           - '## EDUCATION'
           - '## RELEVANT CERTIFICATIONS'
        3. Address the identified weaknesses IF possible by highlighting transferable skills, but DO NOT hallucinate.

        FORMAT OUTPUT STRICTLY AS:
        [START_RESUME]
        (ATS Markdown CV)
        [END_RESUME]

        [START_COVER_LETTER]
        (Cover Letter Markdown)
        [END_COVER_LETTER]
        """
        try:
            res2_text = call_gemini_with_retry(chain_2_prompt, model, wait_time=6)
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

    # --- EXPORT & UI RENDERING ---
    candidate_name = match_result.get("candidate_name", "Candidate")
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', candidate_name)

    with tab1:
        if cv_text:
            st.markdown(cv_text)
            st.download_button("📥 Download ATS-Compliant CV (PDF)", data=build_ats_pdf(cv_text), file_name=f"{safe_name}_ATS_CV.pdf", mime="application/pdf")

    with tab2:
        if cl_text:
            st.markdown(cl_text)
            st.download_button("📥 Download Cover Letter (PDF)", data=build_ats_pdf(f"# {candidate_name}\n\n## APPLICATION COVER LETTER\n\n" + cl_text), file_name=f"{safe_name}_Cover_Letter.pdf", mime="application/pdf")

st.markdown("---")
st.markdown("Developed with ❤️ by **Engineer Nadir Khan** (Gen AI App Developer)")
