import os
import json
import tempfile
import requests
import pdfplumber
import pytesseract

from pdf2image import convert_from_bytes
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# ==========================================
# Tesseract Configuration (Windows local install)
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pytesseract.pytesseract.tesseract_cmd = os.path.join(BASE_DIR, "tesseract.exe")
os.environ["TESSDATA_PREFIX"] = os.path.join(BASE_DIR, "tessdata")


# ==========================================
# Configuration
# ==========================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = "openai/gpt-4o"

app = FastAPI(
    title="Resume Parser API",
    description="API for parsing resumes and extracting structured information and returning JSON",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to your Blazor URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Step 1a: Extract text from text-based PDF
# ==========================================
def extract_text_from_uploaded_pdf(file_bytes: bytes) -> str:
    """
    Helper function to extract text from uploaded PDF using pdfplumber.
    Saves the uploaded file to a temporary location on the disk, extracts text,
    and then deletes the temporary file.
    This approach is necessary because pdfplumber requires a file path to read
    the PDF, and it cannot directly read from bytes in memory.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    text = ""

    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    os.remove(tmp_path)

    return text.strip()


# ==========================================
# Step 1b: Extract text from scanned PDF (OCR fallback)
# ==========================================
def extract_text_from_scanned_pdf(file_bytes: bytes) -> str:
    """
    Helper function to extract text from scanned PDF.
    First, converts bytes to images using pdf2image,
    then uses OCR to extract text from each page image.
    """
    print("Parsing scanned PDF...")

    images = convert_from_bytes(file_bytes, dpi=200)

    text = ""
    for i, image in enumerate(images):
        print(f"Processing page {i + 1} of {len(images)}...")
        page_text = pytesseract.image_to_string(image)
        if page_text:
            text += page_text + "\n"

    return text.strip()


# ==========================================
# Step 1: Extract text from PDF
# Tries text-based first, falls back to OCR
# ==========================================
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Main function to extract text from PDF.
    First, tries to extract uploaded PDF.
    If that doesn't work, it assumes it's a scanned PDF
    and tries to extract text using OCR.
    """
    text = extract_text_from_uploaded_pdf(file_bytes)

    if not text:
        text = extract_text_from_scanned_pdf(file_bytes)

    return text


# ==========================================
# Step 2: Extract career info via LLM
# ==========================================
def extract_career_info_from_resume(resume_text: str) -> dict:
    """
    Passes raw resume text to an LLM to output structured career
    information in JSON format.
    """
    prompt = f"""
You are a resume parser. Extract all career-relevant information from the resume below.

Return ONLY a valid JSON object with these exact fields:
{{
    "full_name": "string or null",
    "email": "string or null",
    "summary": "string or null",
    "skills": ["list of technical or soft skills or null"],
    "work_experience": [
    {{
        "job_title": "job title or null",
        "company_name": "company name or null",
        "start_date": "string or null",
        "end_date": "string or null",
        "is_current": true or false,
        "description": "key responsibilities and achievements or null"
    }}
    ],
    "activity_scores": []
    {{
        "estimating_quantifiable_characteristics_score": "0-5 or null",
        "getting_information_score": "0-5 or null",
        "identifying_objects_actions_and_events_score": "0-5 or null",
        "inspecting_equipment_structures_or_material_score": "0-5 or null",
        "monitoring_processes_materials_or_surroundings_score": "0-5 or null",
        "controlling_machines_and_processes_score": "0-5 or null",
        "developing_technical_instructions_score": "0-5 or null",
        "clerical_activities_score": "0-5 or null",
        "electronic_maintenance_score": "0-5 or null",
        "handling_and_moving_objects_score": "0-5 or null",
        "interacting_with_computers_score": "0-5 or null",
        "managing_resources_score": "0-5 or null",
        "mechanical_maintenance_score": "0-5 or null",
        "operating_vehicles_mechanized_devices_or_equipment_score": "0-5 or null",
        "performing_general_physical_activities_score": "0-5 or null",
        "processing_information_score": "0-5 or null",
        "analyzing_data_or_information_score": "0-5 or null",
        "developing_objectives_and_strategies_score": "0-5 or null",
        "evaluating_info_to_determine_compliance_with_standards_score": "0-5 or null",
        "judging_quality_score": "0-5 or null",
        "making_decisions_score": "0-5 or null",
        "planning_and_organizing_score": "0-5 or null",
        "scheduling_work_and_activities_score": "0-5 or null",
        "thinking_creatively_score": "0-5 or null",
        "using_new_relevant_knowledge_score": "0-5 or null",
        "assisting_and_caring_for_others_score": "0-5 or null",
        "coaching_and_developing_others_score": "0-5 or null",
        "communicating_with_persons_outside_organization_score": "0-5 or null",
        "communicating_with_coworkers_score": "0-5 or null",
        "coordinating_work_and_activities_of_others_score": "0-5 or null",
        "establishing_and_maintaining_interpersonal_relationships_score": "0-5 or null",
        "interpreting_meaning_of_information_for_others_score": "0-5 or null",
        "performing_for_or_working_directly_with_public_score": "0-5 or null",
        "providing_consultation_and_advice_score": "0-5 or null",
        "resolving_conflicts_and_negotiating_with_others_score": "0-5 or null",
        "selling_or_influencing_others_score": "0-5 or null",
        "staffing_score": "0-5 or null",
        "supervising_subordinates_score": "0-5 or null",
        "team_building_score": "0-5 or null",
        "training_and_teaching_score": "0-5 or null"
    }}
     ],
    "education": [
    {{
        "degree_type": "degree or null",
        "field_of_study": "field of study or null",
        "institution_name": "institution name or null",
        "graduation_year": "string or null",
        "specialization": "string or null",
        "start_date": "string or null",
        "end_date": "string or null",
        "gpa": "grade point average or null",
        "is_current": true or false,
        "description": "key details and achievements or null"
    }}
    ],
    "personality_scores": 
    {
        "achievement_effort_score": "1-5 or null",
        "adaptability_flexibility_score": "1-5 or null",
        "stress_tolerance_score": "1-5 or null",
        "initiative_score": "1-5 or null",
        "analytical_thinking_score": "1-5 or null",
        "attention_to_detail_score": "1-5 or null",
        "innovation_score": "1-5 or null",
        "concern_for_others_score": "1-5 or null",
        "collaboration_score": "1-5 or null",
        "service_orientation_score": "1-5 or null",
        "integrity_score": "1-5 or null",
        "social_orientation_score": "1-5 or null",
        "independence_score": "1-5 or null",
        "accountability_score": "1-5 or null",
        "competitive_drive_score": "1-5 or null",
        "charisma_score": "1-5 or null"
    },
    "volunteering": [
    {{
        "organization": "organization name or null",
        "position": "position or null",
        "start_date": "string or null",
        "end_date": "string or null",
        "description": "key details and achievements or null"
    }}
    ],
    "certifications": [
    {{
        "description": "certification details or null"
    }}
    ],
    "languages": [
    {{
        "language_name": "language name or null",
        "proficiency_level": "proficiency level or null"
    }}
    ],
    "awards": [
    {{
        "description": "key details and achievements or null"
    }}
    ]
}}

Rules:
- Return ONLY the JSON object, no preamble, no explanation, no markdown backticks
- If a field has no information, use null for strings or empty array [] for lists
- Be thorough - extract everything career-relevant
- For activity_scores, score each activity from 0 to 5 based on evidence found in the resume:
    0 = no evidence
    1 = minimal evidence
    2 = some evidence
    3 = moderate evidence
    4 = strong evidence
    5 = exceptional evidence
  If there is no evidence at all, return null.
- For personality_scores, leave all of them as TBD for now since we have not 
    done any personality analysis yet. We will fill these in later after we implement that part.

Resume:
{resume_text}
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0,
        },
        timeout=60,
    )

    if response.status_code != 200:
        raise Exception(f"LLM error {response.status_code}: {response.text}")

    raw_output = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    # Strip markdown backticks if model adds them
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]

    return json.loads(raw_output.strip())


# ==========================================
# Endpoint: POST /extract_from_resume
# ==========================================
@app.post("/extract_from_resume")
async def extract_from_resume(file: UploadFile = File(...)):
    """
    API endpoint to receive a resume PDF, extract text,
    and return structured career information in JSON format.
    """

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        resume_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")

    if not resume_text:
        raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")

    try:
        career_info = extract_career_info_from_resume(resume_text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON. Try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting career info: {str(e)}")

    return career_info


# ==========================================
# Endpoint: GET /health
# ==========================================
@app.get("/health")
def health_check():
    """
    Simple health check endpoint to verify that the API is running.
    """
    return {"status": "ok"}

        




            






