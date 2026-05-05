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


def extract_text_from_pdf(file_bytes: bytes) -> str:
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