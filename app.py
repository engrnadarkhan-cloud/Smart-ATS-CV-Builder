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
    ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.7-flash"]
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
    text = raw_text.replace("’", "'").replace("‘", "'").replace("`", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = text.replace("…", "...").replace("•", "-").replace("·", "-")
    text = text.replace("\t", "    ")

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
            
        if clean_line.startswith("## ") and pdf.get_y() > 255:
            pdf.add_page()
        elif clean_line.startswith("### ") and pdf.get_y() > 265:
            pdf.add_page()
            
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
with st.container():
    st.markdown("### 👤 Step 1: Candidate Master Profile")
    st.info("💡 Tip: Apna LinkedIn profile text, purani CV, ya raw notes yahan paste karein. AI format khud theek kar lega.")
    raw_profile = st.text_area("Paste complete profile text here:", height=200, label_visibility="collapsed")

with st.container():
    st.markdown("### 🎯 Step 2: Target Job Description")
    st.info("💡 Tip: Job posting se requirements aur responsibilities copy kar ke yahan paste karein.")
    job_description = st.text_area("Paste target Job Description (JD) here:", height=150, label_visibility="collapsed")

st.markdown("", unsafe_allow_html=True)
generate_btn = st.button("✨ Evaluate & Generate ATS Application", use_container_width=True)
==========================================
BACKEND LOGIC WITH PROGRESSIVE UI
==========================================

if generate_btn:
if not api_key:
st.warning("⚠️ Please sidebar me Gemini API Key enter karein.")
st.stop()
