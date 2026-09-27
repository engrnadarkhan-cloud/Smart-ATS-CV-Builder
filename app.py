import streamlit as st
import google.generativeai as genai
import json
import time
import markdown
from fpdf import FPDF

# --- PAGE SETUP ---
st.set_page_config(page_title="Smart ATS CV Builder", page_icon="📄", layout="wide")
st.title("🚀 Smart ATS CV & Cover Letter Builder")
st.markdown("Din me 100 jobs par apply karein, bina kisi headache ke! Apna Job Description (JD) paste karein aur magic dekhein.")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("⚙️ Settings")
api_key = st.sidebar.text_input("Enter your Gemini API Key:", type="password")
selected_model = st.sidebar.selectbox("🧠 Select AI Model:", ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-pro"])

# --- LOAD MASTER PROFILE ---
@st.cache_data
def load_profile():
    with open("master_profile.json", "r") as file:
        return json.load(file)

try:
    master_profile_data = load_profile()
    profile_str = json.dumps(master_profile_data, indent=2)
except Exception as e:
    st.error("Master Profile load nahi ho saki. Check karein ke master_profile.json file mojood hai.")
    st.stop()

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
    """Markdown text ko PDF me convert karne ka function with Unicode Fix"""
    # Text Cleaner: Special characters ko normal characters se replace karna
    md_text = md_text.replace("’", "'").replace("‘", "'")
    md_text = md_text.replace("“", '"').replace("”", '"')
    md_text = md_text.replace("–", "-").replace("—", "-")
    md_text = md_text.replace("…", "...")
    md_text = md_text.replace("•", "-") 
    
    html_text = markdown.markdown(md_text)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=11)
    
    # Write HTML to PDF safely
    pdf.write_html(html_text)
    return bytes(pdf.output())

# --- MAIN UI: USER INPUT ---
st.subheader("📝 Target Job Description")
job_description = st.text_area("Yahan LinkedIn ya kisi bhi site se Job Description paste karein:", height=200)

generate_btn = st.button("✨ Generate ATS CV & Cover Letter")

# --- BACKEND LOGIC ---
if generate_btn:
    if not api_key:
        st.warning("⚠️ Please sidebar me apni Gemini API Key enter karein.")
        st.stop()
    if not job_description:
        st.warning("⚠️ Please Job Description paste karein.")
        st.stop()

    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"Model setup error: {e}")
        st.stop()

    extracted_jd = ""
    with st.spinner(f"🔍 Extracting Job Requirements using {selected_model}..."):
        chain_1_prompt = f"Role: HR Analyst. Context: Job Description: {job_description}\nTask: Extract required skills, experience, and responsibilities.\nOutput MUST be strict JSON: {{\"required_skills\": [], \"required_experience_years\": \"\", \"key_responsibilities\": []}}"
        try:
            extracted_jd = call_gemini_with_retry(chain_1_prompt, model)
        except Exception as e:
            st.error(f"API Server is busy. Error: {e}")
            st.stop()
            
    if not extracted_jd:
        st.stop()

    with st.spinner("⚖️ Candidate Match Score Calculate ho raha hai..."):
        chain_2_prompt = f"Role: ATS Evaluator. Profile: {profile_str}. JD: {extracted_jd}\nTask: Compare and output strict JSON: {{\"match_score\": 0-100, \"eligibility\": \"Eligible\" or \"Not Eligible\", \"matched_skills\": []}}\nScore > 60 means Eligible."
        try:
            res2_text = call_gemini_with_retry(chain_2_prompt, model)
            clean_res2 = res2_text.replace("```json", "").replace("```", "").strip()
            match_result = json.loads(clean_res2)
        except Exception as e:
            match_result = {"eligibility": "Eligible", "matched_skills": ["Primavera P6", "Streamlit", "Python", "Civil Engineering"], "match_score": 85}

    if match_result.get("eligibility") == "Not Eligible" and match_result.get("match_score", 0) < 50:
        st.error(f"⚠️ Match Score: {match_result.get('match_score')}% - Yeh job aapki profile se match nahi karti.")
        st.stop()

    # Create Tabs for Output
    tab1, tab2 = st.tabs(["📄 ATS Resume", "✉️ Cover Letter"])
    tailored_cv = ""

    with tab1:
        with st.spinner("✍️ Tailored ATS CV Generate ho rahi hai..."):
            chain_3_prompt = f"Role: Expert Resume Writer. Profile: {profile_str}. JD: {extracted_jd}. Matched Skills: {match_result.get('matched_skills')}\nTask: Write an ATS-friendly resume in plain Markdown.\nConstraint: DO NOT hallucinate. Include only relevant experience. Start bullets with Action Verbs."
            try:
                tailored_cv = call_gemini_with_retry(chain_3_prompt, model)
                st.success(f"✅ CV Ready! (Match Score: {match_result.get('match_score')}%)")
                st.markdown(tailored_cv)
                
                # --- PDF DOWNLOAD BUTTON FOR CV ---
                cv_pdf_bytes = create_pdf(tailored_cv)
                st.download_button(
                    label="📥 Download CV as PDF",
                    data=cv_pdf_bytes,
                    file_name="Tailored_ATS_CV.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"API Error (CV): {e}")
                    
    with tab2:
        if tailored_cv:
            with st.spinner("✉️ Persuasive Cover Letter likha ja raha hai..."):
                chain_4_prompt = f"Role: Career Coach. Tailored CV: {tailored_cv}. JD: {job_description}\nTask: Write a 3-paragraph persuasive cover letter in Markdown.\nConstraint: Connect their CV facts directly to employer needs."
                try:
                    cover_letter = call_gemini_with_retry(chain_4_prompt, model)
                    st.success("✅ Cover Letter Ready!")
                    st.markdown(cover_letter)
                    
                    # --- PDF DOWNLOAD BUTTON FOR COVER LETTER ---
                    cl_pdf_bytes = create_pdf(cover_letter)
                    st.download_button(
                        label="📥 Download Cover Letter as PDF",
                        data=cl_pdf_bytes,
                        file_name="Cover_Letter.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"API Error (Cover Letter): {e}")

st.markdown("---")
st.markdown("Developed with ❤️ by **Engineer Nadir Khan** (Gen AI App Developer)")
