import os
import json
import tempfile
import requests
import pdfplumber
import pytesseract

from PIL import Image
from pdf2image import convert_from_bytes
from fastapi import FastAPI, File, UploadFile, HTTPException


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pytesseract.pytesseract.tesseract_cmd = os.path.join(BASE_DIR, "tesseract.exe")
os.environ["TESSDATA_PREFIX"] = os.path.join(BASE_DIR, "tessdata")


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = "gpt-4o"

app = FastAPI(
    title="Resume Parser API",
    description="API for parsing resumes and extracting structured information and returning JSON",
    version="1.0.0",)


def extract_text_from_uploaded_pdf(file_bytes: bytes) -> str:
    """
    Helper function to extract text from uploaded PDF using pdfplumber
    Saves the uploaded file to a temporary location on the disk, extracts text, and then deletes the temporary file
    This approach is necessary because pdfplumber requires a file path to read the PDF, and it cannot directly read from bytes in memory

    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        as tmp:
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


    

    def extract_text_from_scanned_pdf(file_bytes: bytes) -> str:
        """
        Helper function to extract text from scanned PDF. 
        First, converts bytes to images using pdf2image, 
        then uses OCR to extract text from each page image.
        """
        print("Parsing scanned PDF...")

        #Convert PDF pages to images
        images = convert_from_bytes(file_bytes, dpi=200)

        text = ""
        for i, image in enumerate(images):
            print(f"Processing page {i + 1} of {len(images)}...")
            page_text = pytesseract.image_to_string(image)
            if page_text:
                text += page_text + "\n"

        return text.strip()



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

        
        
        def extract_career_info_from_resume(resume_text: str) -> dict:
            """
            Passes raw resume text to an LLM to output structured career information in JSON format.
            """

            prompt = f"""
            You are a resume parser. Extract all career-relevant information from the 
            resume below.

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
                    "is_current": "boolean",
                    "description": "key responsibilities and achievements or null"
                }}
                ],
                "activity_scores": [
                {{
                    "getting_information_score": "0-5 or null",
                    "identifying_objects_actions_and_events_score": "0-5 or null",
                    "monitoring_processes_materials_or_surroundings_score": "0-5 or null",
                    "inspecting_equipment_structures_or_materials_score": "0-5 or null",
                    "estimating_quantifiable_characteristics_score": "0-5 or null",
                    "judging_qualities_of_objects_services_or_people_score": "0-5 or null",
                    "evaluating_information_compliance_with_standards_score": "0-5 or null",
                    "processing_information_score": "0-5 or null",
                    "analyzing_data_or_information_score": "0-5 or null",
                    "making_decisions_and_solving_problems_score": "0-5 or null",
                    "thinking_creatively_score": "0-5 or null",
                    "updating_and_using_relevant_knowledge_score": "0-5 or null",
                    "developing_objectives_and_strategies_score": "0-5 or null",
                    "scheduling_work_and_activities_score": "0-5 or null",
                    "organizing_planning_and_prioritizing_work_score": "0-5 or null",
                    "performing_general_physical_activities_score": "0-5 or null",
                    "handling_and_moving_objects_score": "0-5 or null",
                    "controlling_machines_and_processes_score": "0-5 or null",
                    "working_with_computers_score": "0-5 or null",
                    "operating_vehicles_mechanized_devices_or_equipment_score": "0-5 or null",
                    "drafting_laying_out_and_specifying_technical_devices_score": "0-5 or null",
                    "repairing_and_maintaining_mechanical_equipment_score": "0-5 or null",
                    "repairing_and_maintaining_electronic_equipment_score": "0-5 or null",
                    "documenting_recording_information_score": "0-5 or null",
                    "interpreting_meaning_of_information_for_others_score": "0-5 or null",
                    "communicating_with_supervisors_peers_or_subordinates_score": "0-5 or null",
                    "communicating_with_people_outside_organization_score": "0-5 or null",
                    "establishing_and_maintaining_interpersonal_relationships_score": "0-5 or null",
                    "assisting_and_caring_for_others_score": "0-5 or null",
                    "selling_or_influencing_others_score": "0-5 or null",
                    "resolving_conflicts_and_negotiating_with_others_score": "0-5 or null",
                    "performing_for_or_working_directly_with_public_score": "0-5 or null",
                    "coordinating_work_and_activities_of_others_score": "0-5 or null",
                    "developing_and_building_teams_score": "0-5 or null",
                    "training_and_teaching_others_score": "0-5 or null",
                    "guiding_directing_and_motivating_subordinates_score": "0-5 or null",
                    "coaching_and_developing_others_score": "0-5 or null",
                    "providing_consultation_and_advice_to_others_score": "0-5 or null",
                    "performing_administrative_activities_score": "0-5 or null",
                    "staffing_organizational_units_score": "0-5 or null",
                    "monitoring_and_controlling_resources_score": "0-5 or null"
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
                    "is_current": "boolean",
                    "description": "key details and achievements or null",
                    "city_id": "city id or null",
                    "created_at": "timestamp or null"
                }}
                ],
                "marks": [
                {{
                    "administration_and_management_mark": "0-100 or null",
                    "administrative_mark": "0-100 or null",
                    "economics_and_accounting_mark": "0-100 or null",
                    "sales_and_marketing_mark": "0-100 or null",
                    "customer_and_personal_service_mark": "0-100 or null",
                    "personnel_and_human_resources_mark": "0-100 or null",
                    "production_and_processing_mark": "0-100 or null",
                    "food_production_mark": "0-100 or null",
                    "computers_and_electronics_mark": "0-100 or null",
                    "engineering_and_technology_mark": "0-100 or null",
                    "design_mark": "0-100 or null",
                    "building_and_construction_mark": "0-100 or null",
                    "mechanical_mark": "0-100 or null",
                    "mathematics_mark": "0-100 or null",
                    "physics_mark": "0-100 or null",
                    "chemistry_mark": "0-100 or null",
                    "biology_mark": "0-100 or null",
                    "psychology_mark": "0-100 or null",
                    "sociology_and_anthropology_mark": "0-100 or null",
                    "geography_mark": "0-100 or null",
                    "medicine_and_dentistry_mark": "0-100 or null",
                    "therapy_and_counseling_mark": "0-100 or null",
                    "education_and_training_mark": "0-100 or null",
                    "english_language_mark": "0-100 or null",
                    "foreign_language_mark": "0-100 or null",
                    "fine_arts_mark": "0-100 or null",
                    "history_and_archaeology_mark": "0-100 or null",
                    "philosophy_and_theology_mark": "0-100 or null",
                    "public_safety_and_security_mark": "0-100 or null",
                    "law_and_government_mark": "0-100 or null",
                    "telecommunications_mark": "0-100 or null",
                    "communications_and_media_mark": "0-100 or null",
                    "transportation_mark": "0-100 or null"
                }}
                ],
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
            - Return ONLY the JSON object, no preamble, no explanation, no 
              markdown backticks
            - If a field has no information, use null for strings or empty array [] for lists
            - Be thorough - extract everything career-relevant
            - For activity_scores, score each activity from 0 to 5 based on
              evidence found in the resume:
               0 = no evidence
               1 = minimal evidence
               2 = some evidence
               3 = moderate evidence
               4 = strong evidence
               5 = exceptional evidence
              If there is no evidence at all, return null.
            - For marks, assign a score from 0 to 100 based on any percentages or letter grades mentioned in the resume.
              If there is no evidence for a particular mark, return null.

            
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
                    "max_tokens": 2000,
                    "temperature": 0,  # Deterministic output
                },
                timeout=60,
            )  

            




