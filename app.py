import os
import shutil
import faiss
import numpy as np

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

# Modern SDK import (google-genai)
from google import genai

# Load environment variables from .env
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env", override=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# Initialize Gemini Client using the new unified SDK
client = genai.Client(api_key=GOOGLE_API_KEY)


# ==========================
# FastAPI App Setup
# ==========================

app = FastAPI(title="ClauseWise AI")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==========================
# Global Variables / Models
# ==========================

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

vector_index = None
document_chunks = []


# ==========================
# Request Model
# ==========================

class Question(BaseModel):
    question: str


# ==========================
# Helper Functions
# ==========================

def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# ==========================
# Routes
# ==========================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_pdf(pdf: UploadFile = File(...)):
    global vector_index
    global document_chunks

    file_path = os.path.join(UPLOAD_FOLDER, pdf.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(pdf.file, f)

    text = extract_text(file_path)
    document_chunks = chunk_text(text)

    # Generate embeddings for PDF chunks
    embeddings = embedding_model.encode(document_chunks, convert_to_numpy=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dimension = embeddings.shape[1]
    vector_index = faiss.IndexFlatL2(dimension)
    vector_index.add(embeddings)

    return {
        "status": "success",
        "message": "PDF uploaded successfully"
    }


@app.post("/ask")
async def ask_question(data: Question):
    global vector_index
    global document_chunks

    if vector_index is None:
        return JSONResponse(
            status_code=400,
            content={"answer": "Please upload a PDF first."}
        )

    # Perform similarity search
    query_embedding = embedding_model.encode([data.question], convert_to_numpy=True)
    query_embedding = np.array(query_embedding, dtype=np.float32)

    distances, indices = vector_index.search(query_embedding, 4)

    context = ""
    for idx in indices[0]:
        if idx < len(document_chunks):
            context += document_chunks[idx] + "\n\n"

    prompt = f"""You are ClauseWise.

Answer ONLY using the given context.
If the answer is not available, say "I couldn't find that information in the document."

Context:
{context}

Question:
{data.question}

Answer:"""

    # Call Gemini via the official google-genai SDK
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return {"answer": response.text}