# CV Parser API - Apenas URLs + Parser Avançado
import os
import re
import time
import hashlib
import tempfile
import requests
from urllib.parse import urlparse
from typing import List, Optional, Dict, Any, Tuple

from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import fitz  # PyMuPDF

# ===== opcional: spaCy para PT =====
try:
    import spacy
    _NLP = spacy.load("pt_core_news_lg")
except Exception:
    _NLP = None

# ===== config =====
load_dotenv()

# ===== funções de download =====
def download_pdf_from_url(url: str) -> str:
    """Baixa um PDF de uma URL e retorna o caminho do arquivo temporário"""
    try:
        # Extrai ID do Google Drive se for uma URL de visualização
        if "drive.google.com/file/d/" in url and "view" in url:
            file_id = url.split('/d/')[1].split('/')[0]
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            print(f"DEBUG: Converted Google Drive URL to direct download: {url}")

        # Valida se é uma URL válida
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("URL inválida")
        
        # URLs do Google Drive são aceitas automaticamente
        if not url.lower().endswith('.pdf') and 'drive.google.com' not in url.lower():
            # Faz uma requisição HEAD para verificar o content-type
            head_response = requests.head(url, timeout=10, allow_redirects=True)
            content_type = head_response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type:
                raise ValueError("URL não aponta para um arquivo PDF")
        
        # Baixa o arquivo
        response = requests.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        # Verifica se o conteúdo é realmente um PDF
        if not response.content.startswith(b'%PDF'):
            raise ValueError("Arquivo baixado não é um PDF válido")
        
        # Cria arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(response.content)
        temp_file.close()
        
        return temp_file.name
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Erro ao baixar PDF: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar URL: {str(e)}")

def cleanup_temp_file(file_path: str):
    """Remove arquivo temporário"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception:
        pass  # Ignora erros de limpeza

# ===== modelos =====
class CandidateLocation(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "Brasil"

class CandidateLinks(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

class Candidate(BaseModel):
    full_name: Optional[str] = None
    emails: List[str] = []
    phones: List[str] = []
    location: CandidateLocation = CandidateLocation()
    links: CandidateLinks = CandidateLinks()

class Experience(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    employment_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    location: Optional[str] = None
    achievements: List[str] = []
    tech_stack: List[str] = []
    confidence: float = 0.0

class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    confidence: float = 0.0

class Skill(BaseModel):
    name: str
    level: Optional[str] = "na"
    confidence: float = 0.0

class Language(BaseModel):
    name: str
    level_cefr: Optional[str] = None
    confidence: float = 0.0

class ParsedCV(BaseModel):
    candidate: Candidate = Candidate()
    summary: Optional[str] = None
    skills: List[Skill] = []
    languages: List[Language] = []
    experiences: List[Experience] = []
    education: List[Education] = []
    certifications: List[Dict[str, Any]] = []
    expected_salary: Optional[Dict[str, Any]] = None
    availability: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = {}

class ParseItem(BaseModel):
    file: str
    hash: str
    data: ParsedCV
    confidence_overall: float = Field(ge=0, le=1)
    processing_ms: int

# ===== modelos para URLs =====
class ParseSingleUrlBody(BaseModel):
    url: str = Field(..., description="URL do PDF para processar")

# ===== app =====
app = FastAPI(title="CV Parser API - URLs + Parser Avançado", version="1.0.0")

@app.get("/health")
def health():
    return {"ok": True, "message": "CV Parser API - Apenas URLs + Parser Avançado"}

def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def read_pdf_text(path: str) -> str:
    doc = fitz.open(path)
    out = []
    for p in doc:
        t = p.get_text("text") or ""
        out.append(t)
    return "\n".join(out)

# ===== ENDPOINT PRINCIPAL =====
@app.post("/cv:parse-single-url-enhanced", response_model=ParseItem)
def parse_single_url_enhanced(body: ParseSingleUrlBody):
    """Parse um único PDF a partir de URL com parser melhorado"""
    try:
        from enhanced_parser import EnhancedParser
        enhanced_parser = EnhancedParser()
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Parser melhorado não disponível: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao inicializar parser: {str(e)}")
    
    temp_file = None
    started = time.time()
    
    try:
        # Baixa o PDF da URL
        temp_file = download_pdf_from_url(body.url)
        
        # Processa o PDF
        raw_text = read_pdf_text(temp_file)
        data = enhanced_parser.parse_enhanced(raw_text)
        
        # Calcula confiança melhorada
        conf = 0.6
        if data.candidate.full_name: conf += 0.15
        if data.candidate.emails: conf += 0.1
        if data.summary: conf += 0.05
        if data.skills: conf += 0.1
        if data.experiences: conf += 0.1
        if data.education: conf += 0.05
        if data.certifications: conf += 0.03
        if data.meta.get("projects"): conf += 0.02
        if data.meta.get("achievements"): conf += 0.02
        conf = min(conf, 0.98)
        
        # Extrai nome do arquivo da URL
        filename = os.path.basename(urlparse(body.url).path) or "pdf.pdf"
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        return ParseItem(
            file=filename,
            hash=text_sha256(raw_text),
            data=data,
            confidence_overall=conf,
            processing_ms=int((time.time()-started)*1000)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")
    finally:
        # Limpa arquivo temporário
        if temp_file:
            cleanup_temp_file(temp_file)
