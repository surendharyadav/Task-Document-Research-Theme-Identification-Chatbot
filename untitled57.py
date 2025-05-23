# -*- coding: utf-8 -*-
"""Untitled57.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Xy3rQsYzLnYKm63iYjJ2gu5-ttZQ3wm5
"""

import os

# Create folders
os.makedirs("app/services", exist_ok=True)

# Add __init__.py files so Python treats them as modules
open("app/__init__.py", "a").close()
open("app/services/__init__.py", "a").close()

processor_code = '''
def process_document(file):
    # Dummy processor function
    return f"Processed: {file.filename}"
'''

with open("app/services/processor.py", "w") as f:
    f.write(processor_code)

query_code = '''
def query_documents(question):
    # Dummy query function
    return f"Answer to: {question}"
'''

with open("app/services/query.py", "w") as f:
    f.write(query_code)

import sys
sys.path.append("/content")  # For Colab; adjust if your base path is different
# backend/app/main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from app.services.processor import process_document
from app.services.query import query_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        result = await process_document(file)
        results.append(result)
    return {"status": "success", "processed": results}

@app.get("/query")
async def ask_question(q: str):
    response = await query_documents(q)
    return response

pip install python-multipart

# backend/app/services/processor.py
import os
import pytesseract
from PIL import Image
import pdfplumber
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from sentence_transformers import SentenceTransformer
import shutil

UPLOAD_DIR = "backend/data"
VECTOR_DIR = "backend/data/vector_db"
MODEL = SentenceTransformer('all-MiniLM-L6-v2')

pip install -U langchain-community

pip install pdfplumber

pip install pytesseract

async def process_document(file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    elif file.filename.endswith((".png", ".jpg", ".jpeg")):
        text = pytesseract.image_to_string(Image.open(file_path))
    else:
        return {"error": "Unsupported format"}

    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_text(text)
    documents = [Document(page_content=chunk, metadata={"source": file.filename}) for chunk in chunks]

    if os.path.exists(VECTOR_DIR):
        db = FAISS.load_local(VECTOR_DIR, OpenAIEmbeddings())
        db.add_documents(documents)
    else:
        db = FAISS.from_documents(documents, OpenAIEmbeddings())
    db.save_local(VECTOR_DIR)

    return {"file": file.filename, "chunks": len(chunks)}

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

# backend/app/services/query.py
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from langchain.embeddings import OpenAIEmbeddings

VECTOR_DIR = "backend/data/vector_db"

async def query_documents(query):
    db = FAISS.load_local(VECTOR_DIR, OpenAIEmbeddings())
    retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 5})

    qa = RetrievalQA.from_chain_type(
        llm=OpenAI(temperature=0),
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )

    result = qa({"query": query})
    answer = result["result"]
    citations = [doc.metadata["source"] for doc in result["source_documents"]]
    return {"answer": answer, "citations": citations}