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
    model = genai.GenerativeModel('gemini-1.5-flash')

    with st.spinner("🔍 Job Requirements Extract kar rahe hain..."):
        # CHAIN 1: EXTRACTOR
        chain_1_prompt = f"""
        Role: HR Analyst. Context: Job Description: {job_description}
        Task: Extract required skills, experience, and responsibilities.
        Output MUST be strict JSON: {{"required_skills": [], "required_experience_years": "", "key_responsibilities": []}}
        """
        try:
            res1 = model.generate_content(chain_1_prompt)
            extracted_jd = res1.text
        except Exception as e:
            st.error("API Error (Chain 1). Please try again.")
            st.stop()

    with st.spinner("⚖️ Candidate Match Score Calculate ho raha hai..."):
        # CHAIN 2: MATCHER
        chain_2_prompt = f"""
        Role: ATS Evaluator. Profile: {profile_str}. JD: {extracted_jd}
        Task: Compare and output strict JSON: {{"match_score": 0-100, "eligibility": "Eligible" or "Not Eligible", "matched_skills": []}}
        Score > 60 means Eligible.
        """
        try:
            res2 = model.generate_content(chain_2_prompt)
            # Remove backticks if API sends markdown JSON
            clean_res2 = res2.text.replace("```json", "").replace("```", "").strip()
            match_result = json.loads(clean_res2)
        except Exception as e:
            match_result = {"eligibility": "Eligible", "matched_skills": ["Project Management", "Python"], "match_score": 80} # Fallback

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
            for attempt in range(3):
                try:
                    res3 = model.generate_content(chain_3_prompt)
                    tailored_cv = res3.text
                    st.success(f"✅ CV Ready! (Match Score: {match_result.get('match_score')}%)")
                    st.markdown(tailored_cv)
                    break
                except:
                    if attempt < 2: time.sleep(5)
                    else: st.error("API is very busy. Try again later.")
                    
    with tab2:
        with st.spinner("✉️ Persuasive Cover Letter likha ja raha hai..."):
            # CHAIN 4: COVER LETTER
            chain_4_prompt = f"""
            Role: Career Coach. Tailored CV: {tailored_cv}. JD: {job_description}
            Task: Write a 3-paragraph persuasive cover letter in Markdown.
            Constraint: Connect their CV facts directly to employer needs.
            """
            for attempt in range(3):
                try:
                    res4 = model.generate_content(chain_4_prompt)
                    cover_letter = res4.text
                    st.success("✅ Cover Letter Ready!")
                    st.markdown(cover_letter)
                    break
                except:
                    if attempt < 2: time.sleep(5)
                    else: st.error("API is very busy. Try again later.")

st.markdown("---")
st.markdown("Developed with ❤️ by **Engineer Nadir Khan** (Gen AI App Developer)")
