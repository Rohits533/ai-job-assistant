import streamlit as st
from groq import Groq
import PyPDF2
import io
import json
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

st.set_page_config(
    page_title="AI Career Coach",
    page_icon="💼",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .stApp { 
        background: linear-gradient(135deg, #0f1117 0%, #1a1a2e 50%, #16213e 100%);
        font-family: 'Inter', sans-serif;
    }
    h1 { 
        background: linear-gradient(90deg, #00d4ff, #7b2ff7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-size: 2.5em !important;
        font-weight: 700 !important;
    }
    h2 { color: #00d4ff !important; }
    h3 { color: #7b2ff7 !important; }
    p { color: #888; }
    .score-box {
        background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
        border-radius: 20px;
        padding: 30px;
        border: 1px solid rgba(0, 212, 255, 0.2);
        text-align: center;
        margin: 10px 0;
    }
    .skill-found {
        background: rgba(166, 227, 161, 0.1);
        border: 1px solid rgba(166, 227, 161, 0.3);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 12px;
        color: #a6e3a1;
        display: inline-block;
        margin: 3px;
    }
    .skill-missing {
        background: rgba(243, 139, 168, 0.1);
        border: 1px solid rgba(243, 139, 168, 0.3);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 12px;
        color: #f38ba8;
        display: inline-block;
        margin: 3px;
    }
    .stButton button {
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Database setup
def init_db():
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            job_title TEXT,
            match_score REAL,
            date_applied TEXT,
            status TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_application(company, job_title, match_score, status="Applied", notes=""):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO applications (company, job_title, match_score, date_applied, status, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (company, job_title, match_score, datetime.now().strftime("%Y-%m-%d"), status, notes))
    conn.commit()
    conn.close()

def get_applications():
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT * FROM applications ORDER BY date_applied DESC')
    data = c.fetchall()
    conn.close()
    return data

def extract_pdf_text(pdf_file):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def calculate_match_score(resume_text, job_desc):
    resume_words = set(resume_text.lower().split())
    job_words = set(job_desc.lower().split())
    common = resume_words.intersection(job_words)
    score = (len(common) / len(job_words)) * 100
    return min(score * 2, 100)

def generate_pdf_report(name, job_title, company, score, analysis, cover_letter):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=20*mm, leftMargin=20*mm,
                           topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                fontSize=18, textColor=colors.HexColor('#00d4ff'),
                                spaceAfter=10)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                               fontSize=10, spaceAfter=6, leading=14)
    story = []
    story.append(Paragraph(f"Career Coach Report: {name}", title_style))
    story.append(Paragraph(f"Job: {job_title} at {company}", body_style))
    story.append(Paragraph(f"Match Score: {score:.1f}%", body_style))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("Analysis:", title_style))
    for line in analysis.split('\n'):
        if line.strip():
            story.append(Paragraph(line.strip(), body_style))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Cover Letter:", title_style))
    for line in cover_letter.split('\n'):
        if line.strip():
            story.append(Paragraph(line.strip(), body_style))
    doc.build(story)
    buffer.seek(0)
    return buffer

init_db()

api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)

st.markdown("<h1>💼 AI Career Coach</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:16px'>Upload your resume, paste a job description — AI analyzes your match and helps you land the job!</p>", unsafe_allow_html=True)
st.divider()

tab1, tab2, tab3 = st.tabs(["🎯 Job Matcher", "✉️ Cover Letter", "📊 Application Tracker"])

with tab1:
    st.markdown("## 🎯 Resume Job Matcher")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 Your Resume")
        resume_file = st.file_uploader("Upload Resume (PDF):", type=["pdf"])
        your_name = st.text_input("Your Name:", placeholder="Rohit Savan")

    with col2:
        st.markdown("### 💼 Job Details")
        company_name = st.text_input("Company Name:", placeholder="Google, Microsoft, etc.")
        job_title = st.text_input("Job Title:", placeholder="AI Engineer, Data Scientist, etc.")
        job_description = st.text_area("Paste Job Description:", height=200,
                                      placeholder="Paste the full job description here...")

    if st.button("🎯 Analyze Match", use_container_width=True):
        if resume_file and job_description and your_name:
            with st.spinner("Analyzing your resume against job description..."):
                resume_text = extract_pdf_text(resume_file)
                match_score = calculate_match_score(resume_text, job_description)

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": """You are an expert career coach and ATS specialist. 
Analyze the resume against the job description and provide:
1. Key matching skills found
2. Important missing skills
3. Specific improvement suggestions
4. ATS optimization tips
Be specific and actionable."""},
                        {"role": "user", "content": f"""
Resume:
{resume_text[:3000]}

Job Description:
{job_description[:2000]}

Provide detailed analysis with:
- MATCHING SKILLS: list skills found in both
- MISSING SKILLS: list important skills from job not in resume  
- IMPROVEMENTS: 5 specific suggestions
- ATS TIPS: 3 tips to pass ATS systems
"""}
                    ]
                )
                analysis = response.choices[0].message.content

            st.divider()

            col1, col2, col3 = st.columns(3)
            with col1:
                color = "#00d4ff" if match_score >= 70 else "#fab387" if match_score >= 50 else "#f38ba8"
                st.markdown(f"""
                <div class="score-box">
                    <p style="color:#888; font-size:13px; margin:0">MATCH SCORE</p>
                    <p style="color:{color}; font-size:48px; font-weight:800; margin:8px 0">{match_score:.0f}%</p>
                    <p style="color:#888; font-size:12px; margin:0">
                    {"Strong Match! 🔥" if match_score >= 70 else "Good Match 👍" if match_score >= 50 else "Needs Work 📚"}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="score-box">
                    <p style="color:#888; font-size:13px; margin:0">COMPANY</p>
                    <p style="color:#00d4ff; font-size:24px; font-weight:700; margin:8px 0">{company_name or 'Not specified'}</p>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                <div class="score-box">
                    <p style="color:#888; font-size:13px; margin:0">POSITION</p>
                    <p style="color:#7b2ff7; font-size:20px; font-weight:700; margin:8px 0">{job_title or 'Not specified'}</p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("### 📋 Detailed Analysis")
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e1e2e, #2a2a3e); border-radius: 16px; 
                        padding: 25px; border: 1px solid rgba(0,212,255,0.2); margin: 10px 0;">
                <p style="color:#cdd6f4; font-size:14px; line-height:1.8; white-space:pre-wrap">{analysis}</p>
            </div>
            """, unsafe_allow_html=True)

            st.session_state.resume_text = resume_text
            st.session_state.job_description = job_description
            st.session_state.match_score = match_score
            st.session_state.analysis = analysis
            st.session_state.your_name = your_name
            st.session_state.company_name = company_name
            st.session_state.job_title = job_title

            if company_name and job_title:
                if st.button("💾 Save to Tracker"):
                    save_application(company_name, job_title, match_score)
                    st.success("✅ Saved to Application Tracker!")

            pdf = generate_pdf_report(your_name, job_title, company_name,
                                     match_score, analysis, "")
            st.download_button(
                label="📥 Download Analysis Report",
                data=pdf,
                file_name=f"career_analysis_{your_name}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.warning("Please upload your resume, enter your name and paste the job description!")

with tab2:
    st.markdown("## ✉️ Cover Letter Generator")

    if "resume_text" in st.session_state:
        st.success(f"✅ Using resume and job from Job Matcher tab!")
        tone = st.selectbox("Cover Letter Tone:", ["Professional", "Enthusiastic", "Concise", "Creative"])

        if st.button("✉️ Generate Cover Letter", use_container_width=True):
            with st.spinner("Writing your personalized cover letter..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": f"You are an expert cover letter writer. Write {tone.lower()} cover letters that get interviews."},
                        {"role": "user", "content": f"""
Write a {tone.lower()} cover letter for:
Name: {st.session_state.get('your_name', 'Candidate')}
Applying for: {st.session_state.get('job_title', 'Position')} at {st.session_state.get('company_name', 'Company')}

Resume highlights:
{st.session_state.resume_text[:2000]}

Job Description:
{st.session_state.job_description[:1500]}

Write a compelling, personalized cover letter that highlights matching skills and shows enthusiasm.
"""}
                    ]
                )
                cover_letter = response.choices[0].message.content

            st.markdown("### ✉️ Your Cover Letter")
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e1e2e, #2a2a3e); border-radius: 16px;
                        padding: 25px; border: 1px solid rgba(0,212,255,0.2);">
                <p style="color:#cdd6f4; font-size:14px; line-height:1.9; white-space:pre-wrap">{cover_letter}</p>
            </div>
            """, unsafe_allow_html=True)

            st.download_button(
                label="📥 Download Cover Letter",
                data=cover_letter,
                file_name=f"cover_letter_{st.session_state.get('company_name', 'company')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    else:
        st.info("👆 First analyze your resume in the Job Matcher tab!")

with tab3:
    st.markdown("## 📊 Application Tracker")
    st.markdown("Track all your job applications in one place!")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        new_company = st.text_input("Company:", key="new_company")
    with col2:
        new_title = st.text_input("Job Title:", key="new_title")
    with col3:
        new_score = st.number_input("Match %:", 0, 100, 75, key="new_score")
    with col4:
        new_status = st.selectbox("Status:", ["Applied", "Interview", "Offer", "Rejected"], key="new_status")

    new_notes = st.text_input("Notes:", placeholder="Any notes about this application...")

    if st.button("➕ Add Application", use_container_width=True):
        if new_company and new_title:
            save_application(new_company, new_title, new_score, new_status, new_notes)
            st.success("✅ Application saved!")
            st.rerun()

    st.divider()
    st.markdown("### 📋 Your Applications")

    applications = get_applications()
    if applications:
        import pandas as pd
        df = pd.DataFrame(applications,
                         columns=["ID", "Company", "Job Title", "Match %",
                                 "Date Applied", "Status", "Notes"])

        total = len(df)
        interviews = len(df[df["Status"] == "Interview"])
        offers = len(df[df["Status"] == "Offer"])
        avg_score = df["Match %"].mean()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class="score-box">
                <p style="color:#00d4ff; font-size:28px; font-weight:700; margin:0">{total}</p>
                <p style="color:#888; margin:0">Total Applied</p></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="score-box">
                <p style="color:#a6e3a1; font-size:28px; font-weight:700; margin:0">{interviews}</p>
                <p style="color:#888; margin:0">Interviews</p></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="score-box">
                <p style="color:#7b2ff7; font-size:28px; font-weight:700; margin:0">{offers}</p>
                <p style="color:#888; margin:0">Offers</p></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="score-box">
                <p style="color:#fab387; font-size:28px; font-weight:700; margin:0">{avg_score:.0f}%</p>
                <p style="color:#888; margin:0">Avg Match</p></div>""", unsafe_allow_html=True)

        st.divider()
        st.dataframe(df.drop("ID", axis=1), use_container_width=True)
    else:
        st.info("No applications yet — start applying! 💪")

st.markdown("<p style='text-align:center; margin-top:20px'>Built by Rohit • AI Career Coach • Free Alternative to Jobscan</p>", unsafe_allow_html=True)
