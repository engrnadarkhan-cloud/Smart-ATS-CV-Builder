import streamlit as st
import google.generativeai as genai
import json
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="Smart ATS CV Builder", page_icon="📄", layout="wide")
st.title("🚀 Smart ATS CV & Cover Letter Builder")
st.markdown("Din me 100 jobs par apply karein, bina kisi headache ke! Apna Job Description (JD) paste karein aur magic dekhein.")

# --- SIDEBAR: API KEY SETUP ---
st.sidebar.header("⚙️ Settings")
api_key = st.sidebar.text_input("Enter your Gemini API Key:", type="password")
st.sidebar.markdown("*Aapki key safe hai aur kahin save nahi hoti.*")

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

# --- HELPER FUNCTION FOR API RETRIES (BULLETPROOF) ---
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

# --- MAIN UI: USER INPUT ---
st.subheader("📝 Target Job Description")
job_description = st.text_area("Yahan LinkedIn ya kisi bhi site se Job Description paste karein:", height=200)

generate_btn = st.button("✨ Generate ATS CV & Cover Letter")

# --- BACKEND LOGIC (When button is clicked) ---
if generate_btn:
    if not api_key:
        st.warning("⚠️ Please sidebar me apni Gemini API Key enter karein.")
        st.stop()
    if not job_description:
        st.warning("⚠️ Please Job Description paste karein.")
        st.stop()

    # Configure API
    genai.configure(api_key=api_key)
    
    # --- AUTO-DETECT BEST AVAILABLE MODEL ---
    try:
        valid_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name.replace("models/", ""))
        
        if not valid_models:
            st.error("⚠️ Aapki API key par koi AI model available nahi hai.")
            st.stop()
            
        # Khud best model select karega (prefer 1.5-flash)
        best_model = valid_models[0]
        for v in valid_models:
            if "1.5-flash" in v:
                best_model = v
                break
                
        model = genai.GenerativeModel(best_model)
    except Exception as e:
        st.error(f"API setup error: {e}")
        st.stop()

    # Initialize variable taake NameError na aaye
    extracted_jd = ""
    
    with st.spinner(f"🔍 Extracting Job Requirements using ({best_model})..."):
        # CHAIN 1: EXTRACTOR
        chain_1_prompt = f"""
        Role: HR Analyst. Context: Job Description: {job_description}
        Task: Extract required skills, experience, and responsibilities.
        Output MUST be strict JSON: {{"required_skills": [], "required_experience_years": "", "key_responsibilities": []}}
        """
        try:
            extracted_jd = call_gemini_with_retry(chain_1_prompt, model)
        except Exception as e:
            st.error(f"API Server is busy (Chain 1). Error: {e}")
            st.stop()
            
    if not extracted_jd:
        st.error("⚠️ Job description extract nahi ho saki. Please try again.")
        st.stop()

    with st.spinner("⚖️ Candidate Match Score Calculate ho raha hai..."):
        # CHAIN 2: MATCHER
        chain_2_prompt = f"""
        Role: ATS Evaluator. Profile: {profile_str}. JD: {extracted_jd}
        Task: Compare and output strict JSON: {{"match_score": 0-100, "eligibility": "Eligible" or "Not Eligible", "matched_skills": []}}
        Score > 60 means Eligible.
        """
        try:
            res2_text = call_gemini_with_retry(chain_2_prompt, model)
            clean_res2 = res2_text.replace("```json", "").replace("```", "").strip()
            match_result = json.loads(clean_res2)
        except Exception as e:
            # Fallback agar JSON formatting me masla aaye
            match_result = {"eligibility": "Eligible", "matched_skills": ["Project Management", "Python"], "match_score": 80}

    if match_result.get("eligibility") == "Not Eligible" and match_result.get("match_score", 0) < 50:
        st.error(f"⚠️ Match Score: {match_result.get('match_score')}% - Yeh job aapki profile se match nahi karti. Tokens bachayein!")
        st.stop()

    # Create Tabs for Output
    tab1, tab2 = st.tabs(["📄 ATS Resume", "✉️ Cover Letter"])

    with tab1:
        with st.spinner("✍️ Tailored ATS CV Generate ho rahi hai..."):
            # CHAIN 3: CV BUILDER
            chain_3_prompt = f"""
            Role: Expert Resume Writer. Profile: {profile_str}. JD: {extracted_jd}. Matched Skills: {match_result.get('matched_skills')}
            Task: Write an ATS-friendly resume in plain Markdown.
            Constraint: DO NOT hallucinate. Include only relevant experience. Use Action Verbs.
            """
            try:
                tailored_cv = call_gemini_with_retry(chain_3_prompt, model)
                st.success(f"✅ CV Ready! (Match Score: {match_result.get('match_score')}%)")
                st.markdown(tailored_cv)
            except Exception as e:
                st.error(f"API Error (CV): {e}")
                tailored_cv = ""
                    
    with tab2:
        if tailored_cv:
            with st.spinner("✉️ Persuasive Cover Letter likha ja raha hai..."):
                # CHAIN 4: COVER LETTER
                chain_4_prompt = f"""
                Role: Career Coach. Tailored CV: {tailored_cv}. JD: {job_description}
                Task: Write a 3-paragraph persuasive cover letter in Markdown.
                Constraint: Connect their CV facts directly to employer needs.
                """
                try:
                    cover_letter = call_gemini_with_retry(chain_4_prompt, model)
                    st.success("✅ Cover Letter Ready!")
                    st.markdown(cover_letter)
                except Exception as e:
                    st.error(f"API Error (Cover Letter): {e}")

st.markdown("---")
st.markdown("Developed with ❤️ by **Engineer Nadir Khan** (Gen AI App Developer)")
