# main.py  (v0.9.5)
import os
import re
import time
import hashlib
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
SOURCE_DIR = os.getenv("SOURCE_DIR", r"C:\Users\joao.miguel\Documents\Curriculum")

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

class ParseAllResponse(BaseModel):
    results: List[ParseItem]
    scanned_dir: str

# ===== regex & constantes =====
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_BR_RE = re.compile(r"(?:\+?55)?\s*\(?\d{2}\)?\s*\d{4,5}-?\d{4}")
URL_RE = re.compile(r"(https?://[^\s]+|\bwww\.[^\s]+)", re.I)
LINKEDIN_HOST_RE = re.compile(r"linkedin\.com", re.I)
GITHUB_HOST_RE   = re.compile(r"github\.com", re.I)

TECH_HINTS = [
    # Languages & Frameworks
    "java","spring","quarkus","node","javascript","typescript","python","react",
    "angular","vue","flask","django","dotnet","php","golang","rust",
    
    # Cloud & Infrastructure  
    "aws","azure","gcp","kubernetes","docker","terraform","jenkins","ansible",
    
    # Databases
    "mysql","postgresql","mongodb","redis","elasticsearch","cassandra",
    
    # Tools & Practices
    "git","ci/cd","agile","scrum","jira","confluence","junit","jest",
    
    # Architecture
    "microservices","api","rest","graphql","grpc","event-driven",
    "domain-driven","clean-architecture"
]

HEADER_STOPWORDS = {
    # pt
    "resumo","summary","principais competências","skills & proficiencies","skills",
    "contato","contact","experiência","experience","experiência profissional",
    "professional experience","education","formação","formação acadêmica",
    "linguagens","languages","certifications","certificações",
    "perfil","profile","objetivo","objective","sobre","about",
    "localização","location","responsabilidades","responsibilities","projetos","projects",
    "conquistas","realizações","achievements","key achievements"
}
# variações uppercase usadas como cabeçalho (caso do PDF do Marco)
HEADER_UPPER_ALIASES = {
    "KEY ACHIEVEMENTS","EXPERIENCE","PROFESSIONAL EXPERIENCE","EDUCATION",
    "PROJECTS","RESPONSIBILITIES","SUMMARY","PROFILE","SKILLS","LANGUAGES"
}

EDU_KEYWORDS = re.compile(
    r"(universidade|university|faculdade|bachelor|bacharel|graduaç|graduat|licenciatura|tecnólogo|master|mestrado|ph\.?d|pós[- ]grad|post[- ]grad|furb|inpg)",
    re.I
)

ROLE_HINTS = re.compile(
    r"(cpto|cto|chief technology officer|diretor(a)? de tecnologia|architect|arquitet[oa]|engenheir[oa]|engineer|analista|developer|desenvolvedor|coordenador|coordenadora|team lead|team leader|líder|leader|gerente|manager|qa|tester|scrum master|product|designer|founder|empreendedor|tech lead|software)",
    re.I
)

# empresas conhecidas (aliases -> canonical)
KNOWN_COMPANIES_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bSenior\s+Sistemas\b", re.I), "Senior Sistemas"),
    (re.compile(r"\bBenner\s+Sistemas\b", re.I), "Benner Sistemas"),
    (re.compile(r"\bGOVERNANÇABRASIL\b|\bGOVBR\b", re.I), "GOVBR"),
    (re.compile(r"\bPaytrack\b", re.I), "Paytrack"),
    (re.compile(r"\bSocial\s+NT\b", re.I), "Social NT"),
    (re.compile(r"\bCetelbras\s+Educacional\b", re.I), "Cetelbras Educacional"),
    (re.compile(r"\bDock\b", re.I), "Dock"),
    (re.compile(r"\bCaylent\b", re.I), "Caylent"),
]

# termos que NÃO podem ser empresa
COMPANY_BLACKLIST_EXACT = {
    "imprensa", "travel", "cpto", "diretor de tecnologia", "analista de sistemas",
    "development coordinator", "team leader", "empreendedor", "location",
    "key achievements", "responsibilities", "experience", "education", "projects"
}

# localização
LOCATION_TERMS = {"location", "localização", "localidade"}
CITY_COUNTRY_RE = re.compile(
    r"^[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ' .-]+,\s*(?:[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ' .-]+,\s*)?(Brasil|Brazil|United States|USA|Canada|Canad[aá]|Portugal|Germany|Alemanha|Spain|Espanha|UK|United Kingdom|Italy|Itália|France|França|Argentina|Chile|Uruguay|Uruguai|Mexico|México)$",
    re.I
)

DURATION_RE = re.compile(
    r"\b(\d+\s+(anos?|years?)\b(?:\s+\d+\s+(mes(es)?|months?))?|\d+\s+(mes(es)?|months?))\b",
    re.I
)

MONTHS = {
    "janeiro":"01","fevereiro":"02","março":"03","marco":"03","abril":"04",
    "maio":"05","junho":"06","julho":"07","agosto":"08","setembro":"09",
    "outubro":"10","novembro":"11","dezembro":"12",
    "january":"01","february":"02","march":"03","april":"04","may":"05","june":"06",
    "july":"07","august":"08","september":"09","october":"10","november":"11","december":"12"
}
ABBR_MONTH_MAP = {
    "jan":"january","fev":"fevereiro","feb":"february","mar":"march",
    "abr":"abril","apr":"april","mai":"may","jun":"june","jul":"july",
    "ago":"august","aug":"august","set":"setembro","sep":"september",
    "out":"outubro","oct":"october","nov":"november","dez":"dezembro","dec":"december"
}
CURRENT_TOKENS = {"present","current","atual","presente"}
VALID_YEAR_MIN = 1970
VALID_YEAR_MAX = 2035

# ===== utils de texto =====
def read_pdf_text(path: str) -> str:
    doc = fitz.open(path)
    out = []
    for p in doc:
        t = p.get_text("text") or ""
        out.append(t)
    return "\n".join(out)

def split_concatenated_urls(text: str) -> str:
    text = re.sub(r'(?<=[A-Za-z0-9/_-])(?=https?://)', ' ', text)
    text = re.sub(r'(?<=[A-Za-z0-9/_-])(?=\bwww\.)', ' ', text)
    return text

def strip_headers_footers(line: str) -> Optional[str]:
    l = line.strip()
    if not l:
        return None
    if re.search(r"^page\s+\d+\s+of\s+\d+$", l, re.I): return None
    if re.search(r"^página\s+\d+\s+de\s+\d+$", l, re.I): return None
    if l in {"|","—","-","•"}: return None
    return l

def normalize_text_for_parsing(text: str) -> str:
    text = re.sub(r'(https?://\S+|\bwww\.\S+)\s*\n\s*([^\s])', r'\1 \2', text)
    text = text.replace("linkedin.com/in/\n", "linkedin.com/in/")
    text = split_concatenated_urls(text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text

def strip_url_trailing(url: str) -> str:
    return url.rstrip(").,;")

def ensure_http(url: str) -> str:
    return url if url.startswith("http") else "https://" + url

def extract_first_url_by_domain(text: str, domain_regex: re.Pattern) -> Optional[str]:
    for m in URL_RE.finditer(text):
        raw = m.group(0)
        clean = strip_url_trailing(ensure_http(raw))
        if domain_regex.search(clean):
            return clean
    return None

def extract_links(text: str) -> CandidateLinks:
    return CandidateLinks(
        linkedin=extract_first_url_by_domain(text, LINKEDIN_HOST_RE),
        github=extract_first_url_by_domain(text, GITHUB_HOST_RE),
        portfolio=None
    )

def basic_skills(text: str) -> List[Skill]:
    found = set()
    low = text.lower()
    for k in TECH_HINTS:
        if k in low:
            found.add(k)
    return [Skill(name=s, level="na", confidence=0.6) for s in sorted(found)]

def basic_languages(text: str) -> List[Language]:
    langs: List[Language] = []
    text = text.lower()
    
    # Common language patterns
    patterns = [
        (r"english|inglês|ingles", "English"),
        (r"portuguese|português|portugues", "Portuguese"),
        (r"spanish|español|espanhol", "Spanish"),
        (r"french|français|frances", "French"),
        (r"german|deutsch|alemão|alemao", "German")
    ]
    
    # Level patterns
    level_patterns = [
        (r"\b(c2|proficient|fluent|native)\b", "C2"),
        (r"\b(c1|advanced)\b", "C1"), 
        (r"\b(b2|upper.?intermediate)\b", "B2"),
        (r"\b(b1|intermediate)\b", "B1"),
        (r"\b(a2|elementary)\b", "A2"),
        (r"\b(a1|beginner)\b", "A1")
    ]

    for lang_pattern, lang_name in patterns:
        if re.search(lang_pattern, text, re.I):
            # Find level in nearby context
            level = None
            for level_pat, level_name in level_patterns:
                if re.search(level_pat, text, re.I):
                    level = level_name
                    break
                    
            langs.append(Language(
                name=lang_name,
                level_cefr=level,
                confidence=0.8 if level else 0.6
            ))
            
    return langs

def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def looks_like_header(line: str) -> bool:
    l = line.strip()
    low = l.lower()
    if low in HEADER_STOPWORDS: return True
    if l.upper() in HEADER_UPPER_ALIASES: return True
    if len(l) <= 2: return True
    if l.endswith(":"): return True
    return False

# ===== nome do candidato =====
def name_from_linkedin_or_email(text: str) -> Optional[str]:
    m = re.search(r'linkedin\.com/in/([A-Za-z0-9\-_.]+)', text, re.I)
    if m:
        slug = m.group(1)
        parts = re.split(r'[\-_.]+', slug)
        parts = [p for p in parts if p and not p.isdigit()]
        if len(parts) >= 2:
            return " ".join(p.capitalize() for p in parts[:4])
    m = re.search(r'([A-Za-z0-9._-]+)@', text)
    if m:
        local = m.group(1)
        parts = re.split(r'[._-]+', local)
        parts = [p for p in parts if p and not p.isdigit()]
        if len(parts) >= 2:
            return " ".join(p.capitalize() for p in parts[:4])
    return None

def guess_name_from_lines(lines: List[str]) -> Optional[str]:
    if len(lines) >= 2 and lines[0].isupper() and lines[1].isupper():
        cand = f"{lines[0]} {lines[1]}"
        if 3 <= len(cand) <= 80 and 2 <= len(cand.split()) <= 4:
            return cand.title()
    for ln in lines:
        if looks_like_header(ln): continue
        if 2 <= len(ln.split()) <= 4 and re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ.' -]+", ln):
            if not ln.endswith('.'):
                return ln.title()
    return None

def guess_name(text: str) -> Optional[str]:
    best = name_from_linkedin_or_email(text)
    if best: return best
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:12]
    cand = guess_name_from_lines(lines)
    if cand: return cand
    if _NLP:
        doc = _NLP(text[:20000])
        for ent in doc.ents:
            if ent.label_ == "PER" and len(ent.text.split()) >= 2:
                return ent.text.strip()
    return None

# ===== phones =====
def normalize_phone_br(raw: str) -> Optional[str]:
    digits = re.sub(r'\D', '', raw)
    if not digits: return None
    if digits.startswith('55'):
        pass
    elif len(digits) in (10, 11):
        digits = '55' + digits
    else:
        return raw
    return '+' + digits

def normalize_phones(phones_raw: List[str]) -> List[str]:
    out: List[str] = []
    for p in phones_raw:
        np = normalize_phone_br(p)
        if np and np not in out:
            out.append(np)
    return out

# ===== datas =====
def month_to_num(m: str) -> Optional[str]:
    return MONTHS.get(m.strip().lower())

def parse_month_year(token: str) -> Optional[Tuple[str, str]]:
    t = token.strip().lower()

    # YYYY-MM or YYYY/MM
    m = re.match(r"(\d{4})[-/](\d{1,2})$", t)
    if m:
        y, mm = int(m.group(1)), int(m.group(2))
        if not (VALID_YEAR_MIN <= y <= VALID_YEAR_MAX): return None
        if not (1 <= mm <= 12): return None
        return str(y), f"{mm:02d}"

    # MM/YYYY or MM-YYYY
    m = re.match(r"(\d{1,2})[-/](\d{4})$", t)
    if m:
        mm, y = int(m.group(1)), int(m.group(2))
        if not (VALID_YEAR_MIN <= y <= VALID_YEAR_MAX): return None
        if not (1 <= mm <= 12): return None
        return str(y), f"{mm:02d}"

    m = re.match(r"(\d{4})$", t)
    if m:
        y = int(m.group(1))
        if not (1970 <= y <= 2035): return None
        return str(y), "01"

    m = re.match(r"([a-zçãéíóú]+)\s+(?:de\s+)?(\d{4})$", t)
    if m:
        y = int(m.group(2))
        if not (1970 <= y <= 2035): return None
        mon = month_to_num(m.group(1))
        if mon: return str(y), mon

    m = re.match(r"([a-z]{3})\.?\s+(\d{4})$", t)
    if m:
        y = int(m.group(2))
        if not (1970 <= y <= 2035): return None
        abbr = m.group(1)
        full = ABBR_MONTH_MAP.get(abbr)
        if full:
            mon = month_to_num(full)
            if mon: return str(y), mon
    return None

DATE_RANGE_RE = re.compile(
    # supports formats like 'Março de 2023 - Presente', '2022 - 2023', '03/2023 - 07/2024', etc.
    r"([A-Za-zçãéíóú\.]+(?:\s+de)?\s+\d{4}|\d{4}(?:[-/]\d{1,2})?|\d{1,2}[-/]\d{4}|Present|Current|Atual|Presente)\s*[-–]\s*([A-Za-zçãéíóú\.]+(?:\s+de)?\s+\d{4}|\d{4}(?:[-/]\d{1,2})?|\d{1,2}[-/]\d{4}|Present|Current|Atual|Presente)",
    re.I
)

def parse_date_range(s: str) -> Tuple[Optional[str], Optional[str], Optional[bool]]:
    m = DATE_RANGE_RE.search(s)
    if not m:
        return None, None, None
    a, b = m.group(1), m.group(2)

    def to_ym(x: str) -> Optional[Tuple[int,int]]:
        x = x.strip()
        if x.lower() in CURRENT_TOKENS:
            return None
        ym = parse_month_year(x)
        if ym:
            y, mm = ym
            return int(y), int(mm)
        return None

    start_ym = to_ym(a)
    end_ym = to_ym(b)
    is_current = (b.strip().lower() in CURRENT_TOKENS)

    def fmt(ym):
        return f"{ym[0]:04d}-{ym[1]:02d}" if ym else None

    if start_ym and end_ym and (end_ym < start_ym):
        return None, None, None

    start = fmt(start_ym)
    end = fmt(end_ym)
    return start, end, is_current if is_current else None

# ===== util de localização =====
def is_location_line(line: Optional[str]) -> bool:
    if not line:
        return False
    l = line.strip()
    low = l.lower()
    if low in LOCATION_TERMS:
        return True
    if CITY_COUNTRY_RE.match(l):
        return True
    tokens = ["brasil","brazil","sc","santa catarina","blumenau","são paulo","rio de janeiro","curitiba","florianópolis","porto alegre"]
    if any(tok in low for tok in tokens):
        if 2 <= len(l.split()) <= 5:
            return True
    return False

# ===== heurísticas de empresa/cargo =====
COMPANY_VERB_TOKENS = re.compile(
    r"(defini|entreg|funcionalidad|moderniz|lider|respons|área|departament|arquitet|microservi|microfront|soluç|process|projet|produto|suporte|equipe|time|implant|melhor|otimiz|estratég|document|descri|cloudfront)",
    re.I
)

def remove_parentheticals(s: str) -> str:
    return re.sub(r"\([^)]*\)", "", s).strip()

def looks_sentence_like(s: str) -> bool:
    low = s.lower()
    connectors = sum(1 for w in [" de ", " da ", " do ", " para ", " com ", " por ", " que "] if w in f" {low} ")
    many_words = len(s.split()) >= 10
    ends_dot = s.strip().endswith(".")
    has_verby = bool(COMPANY_VERB_TOKENS.search(s))
    return connectors >= 3 or many_words or ends_dot or has_verby

def too_symbolic(s: str) -> bool:
    return bool(re.search(r"[;:<>/|]{2,}", s))

def is_all_caps_multiword(s: str) -> bool:
    words = [w for w in re.split(r"\s+", s.strip()) if w]
    if len(words) < 2:
        return False
    return s.upper() == s and any(len(w) > 1 for w in words)

def capitalized_ratio_ok(s: str) -> bool:
    words = [w for w in re.split(r"\s+", s) if w]
    if not (1 <= len(words) <= 7):
        return False
    caps = sum(1 for w in words if w[0:1].isupper())
    return caps >= max(1, int(0.5 * len(words)))

def sanitize_company_line(s: Optional[str]) -> Optional[str]:
    if not s: return None
    s = s.strip().strip("•-–—").strip()
    if s.upper() in HEADER_UPPER_ALIASES:  # bloqueio extra para cabeçalhos em caps
        return None
    mloc = re.match(r"(.+?)\s+Location$", s, re.I)
    if mloc:
        s = mloc.group(1).strip()
    if is_location_line(s):
        return None
    s = remove_parentheticals(s)
    s = re.sub(r"\s{2,}", " ", s)
    low = s.lower()
    if low in COMPANY_BLACKLIST_EXACT: return None
    if looks_sentence_like(s): return None
    if too_symbolic(s): return None
    if len(s) < 3: return None
    # linha TODA EM CAPS com 2+ palavras só vale se for empresa conhecida
    if is_all_caps_multiword(s):
        if not match_known_company(s):
            return None
    if not capitalized_ratio_ok(s): return None
    return s

def match_known_company(s: str) -> Optional[str]:
    for pat, canon in KNOWN_COMPANIES_PATTERNS:
        if pat.search(s):
            return canon
    return None

def is_skilly_line(line: str) -> bool:
    low = line.lower()
    hits = sum(1 for t in TECH_HINTS if t in low)
    commas = line.count(",")
    return hits >= 2 or commas >= 2

def clean_title(s: Optional[str]) -> Optional[str]:
    if not s: return s
    s = re.sub(r"^\W+", "", s).strip()
    s = s.rstrip(":;,.").strip()
    if looks_like_header(s): return None
    if EDU_KEYWORDS.search(s): return None
    if is_skilly_line(s): return None
    if len(s) > 180: return None
    return s

def score_role(line: str) -> int:
    if is_location_line(line):
        return -10
    score = 0
    # penalize obvious sentence-like lines (achievements / descriptions)
    if looks_sentence_like(line):
        score -= 3
    if ROLE_HINTS.search(line):
        score += 3
    if len(line.split()) >= 2:
        score += 1
    if line and line[0].isupper():
        score += 1
    return score

def score_company(line: str) -> int:
    if is_location_line(line):
        return -10
    if match_known_company(line):
        return 10
    s = sanitize_company_line(line)
    if not s:
        return -10
    if ROLE_HINTS.search(s): return -5
    if is_skilly_line(s): return -5
    
    # Verifica se contém múltiplas tecnologias (não é empresa)
    tech_keywords = [
        "react", "angular", "vue", "flutter", "java", "python", "go", "scala",
        "spring", "quarkus", "aws", "azure", "gcp", "docker", "kubernetes"
    ]
    
    tech_count = 0
    for tech in tech_keywords:
        if tech.lower() in s.lower():
            tech_count += 1
    
    # Se contém 2+ tecnologias, provavelmente não é empresa
    if tech_count >= 2:
        return -8
        
    # Se contém tecnologias separadas por "e" ou ",", não é empresa
    if re.search(r'\b(?:react|angular|vue|flutter|java|python|go|scala|spring|quarkus|aws|azure|gcp)\s*(?:,|\s+e\s+|\sand\s+)\s*(?:react|angular|vue|flutter|java|python|go|scala|spring|quarkus|aws|azure|gcp)\b', s.lower()):
        return -8
    
    score = 0
    if re.search(r"(sistemas|tecnologia|ltda|s\.?a\.?|software|educacional|group|holding|ltd|inc\.?)", s, re.I):
        score += 2
    n = len(s.split())
    caps = sum(1 for w in s.split() if w[:1].isupper())
    if caps >= max(1, n - 1): score += 2
    if 1 <= n <= 4: score += 1
    return score

def parse_composite_role_company(line: str) -> Tuple[Optional[str], Optional[str]]:
    if not line: return None, None
    mloc = re.match(r"(.+?)\s+Location$", line.strip(), re.I)
    if mloc:
        comp = sanitize_company_line(mloc.group(1))
        comp = match_known_company(comp) or comp
        return None, comp

    sep_split = re.split(r"\s[@|•–—\-]\s|[@|]| - ", line)
    if len(sep_split) < 2:
        sep_split = re.split(r"\s[-–—]\s", line)
    if len(sep_split) < 2:
        return None, None

    parts = [clean_title(p) for p in sep_split if clean_title(p)]
    parts = [p for p in parts if p and not is_location_line(p)]
    if not parts:
        return None, None

    best_role = (None, -999)
    best_company = (None, -999)
    for p in parts:
        # Verifica se a parte contém múltiplas tecnologias (não é empresa)
        tech_keywords = [
            "react", "angular", "vue", "flutter", "java", "python", "go", "scala",
            "spring", "quarkus", "aws", "azure", "gcp", "docker", "kubernetes"
        ]
        
        tech_count = 0
        for tech in tech_keywords:
            if tech.lower() in p.lower():
                tech_count += 1
        
        # Se contém 2+ tecnologias, pula esta parte
        if tech_count >= 2:
            continue
            
        # Se contém tecnologias separadas por "e" ou ",", pula esta parte
        if re.search(r'\b(?:react|angular|vue|flutter|java|python|go|scala|spring|quarkus|aws|azure|gcp)\s*(?:,|\s+e\s+|\sand\s+)\s*(?:react|angular|vue|flutter|java|python|go|scala|spring|quarkus|aws|azure|gcp)\b', p.lower()):
            continue
        
        r = score_role(p)
        c = score_company(p)
        if r > best_role[1]:
            best_role = (p, r)
        if c > best_company[1]:
            best_company = (p, c)

    role = best_role[0] if best_role[1] >= 2 else None
    company = best_company[0] if best_company[1] >= 2 else None

    if company:
        known = match_known_company(company)
        company = known or sanitize_company_line(company)

    if company and role and company.lower() == role.lower():
        company = None

    if not company:
        m = re.search(r"@\s*([A-Z][\w ]{1,40})$", line)
        if m:
            ctry = sanitize_company_line(m.group(1))
            known = match_known_company(ctry) if ctry else None
            company = known or ctry

    return role, company

# ===== linhas/auxiliares =====
def clean_line(line: str) -> Optional[str]:
    line = strip_headers_footers(line)
    if not line: return None
    if re.search(r"page\s+\d+\s+of\s+\d+", line, re.I): return None
    return line

def extract_lines(text: str) -> List[str]:
    return [ln for ln in (clean_line(x) for x in text.splitlines()) if ln]

# ===== educação/certificações =====
def extract_education_global(text: str) -> List[Education]:
    lines = extract_lines(text)
    res: List[Education] = []
    YEAR_RANGE_SIMPLE = re.compile(r"\b(\d{4})\s*[-/–]\s*(\d{4})\b")

    for i, ln in enumerate(lines):
        if CERT_KEYWORDS.search(ln):
            continue
        m = YEAR_RANGE_SIMPLE.search(ln)
        if not m:
            continue
        y1, y2 = int(m.group(1)), int(m.group(2))
        if not (VALID_YEAR_MIN <= y1 <= VALID_YEAR_MAX and VALID_YEAR_MIN <= y2 <= VALID_YEAR_MAX):
            continue

        neighbors = [
            lines[i-2] if i-2 >=0 else "",
            lines[i-1] if i-1 >=0 else "",
            lines[i+1] if i+1 < len(lines) else "",
            lines[i+2] if i+2 < len(lines) else ""
        ]

        inst = None
        deg = None

        inst_cands = [n for n in neighbors if n and re.search(r"(universidade|faculdade|furb|inpg)", n, re.I)]
        if inst_cands:
            inst = sorted(inst_cands, key=len, reverse=True)[0][:140].rstrip(":;,.").strip()

        deg_cands = [n for n in neighbors if n and n != inst and not looks_like_header(n)]
        if deg_cands:
            deg = sorted(deg_cands, key=len, reverse=True)[0][:140].rstrip(":;,.").strip()

        if deg and not inst and re.search(r"(universidade|faculdade|furb|inpg)", deg, re.I):
            inst, deg = deg, None

        res.append(Education(
            institution=inst,
            degree=deg,
            start_date=f"{y1}-01",
            end_date=f"{y2}-01",
            confidence=0.7 if (deg or inst) else 0.5
        ))

    for i, ln in enumerate(lines):
        if not EDU_KEYWORDS.search(ln) or CERT_KEYWORDS.search(ln):
            continue
        already = any((ed.institution and ed.institution.lower() in ln.lower()) or
                      (ed.degree and ed.degree.lower() in ln.lower()) for ed in res)
        if already:
            continue
        y1 = y2 = None
        YEAR_RANGE_SIMPLE = re.compile(r"\b(\d{4})\s*[-/–]\s*(\d{4})\b")
        for j in range(max(0, i-5), min(len(lines), i+6)):
            m = YEAR_RANGE_SIMPLE.search(lines[j])
            if m:
                y1, y2 = int(m.group(1)), int(m.group(2))
                if VALID_YEAR_MIN <= y1 <= VALID_YEAR_MAX and VALID_YEAR_MIN <= y2 <= VALID_YEAR_MAX:
                    break
        inst = None
        deg = ln.strip()[:140].rstrip(":;,.")
        if re.search(r"(universidade|faculdade|furb|inpg)", deg, re.I):
            inst, deg = deg, None
        res.append(Education(
            institution=inst,
            degree=deg,
            start_date=f"{y1}-01" if y1 else None,
            end_date=f"{y2}-01" if y2 else None,
            confidence=0.6
        ))

    merged: Dict[Tuple[Optional[str],Optional[str]], Education] = {}
    for ed in res:
        key = (ed.start_date, ed.end_date)
        if key not in merged:
            merged[key] = ed
        else:
            base = merged[key]
            if not base.institution and ed.institution: base.institution = ed.institution
            if not base.degree and ed.degree: base.degree = ed.degree
            base.confidence = max(base.confidence, ed.confidence)
    return list(merged.values())

CERT_KEYWORDS = re.compile(
    r"(certific|psm|professional scrum|aws certified|azure fundamentals|itil|pmi|pmp|scrum master|oracle certified|istqb)",
    re.I
)

CERT_PATTERNS = [
    r"aws certified",
    r"microsoft certified",
    r"oracle certified",
    r"google cloud certified", 
    r"certified scrum",
    r"pmp certified",
    r"itil certified",
    r"comptia",
    r"cissp",
    r"ceh"
]

def extract_certifications(text: str) -> List[Dict[str, Any]]:
    certs = []
    for pattern in CERT_PATTERNS:
        matches = re.finditer(pattern, text, re.I)
        for m in matches:
            # Look for dates near certification
            context = text[max(0,m.start()-50):m.end()+50]
            date_match = re.search(r'\b\d{4}\b', context)
            
            certs.append({
                "name": m.group(),
                "date": date_match.group() if date_match else None,
                "confidence": 0.8
            })
    return certs

# ===== helpers company/role =====
def choose_role_company_from_candidates(candidates: List[str]) -> Tuple[Optional[str], Optional[str]]:
    if not candidates:
        return None, None

    cands = []
    seen = set()
    for c in candidates:
        if not c: continue
        if c.upper() in HEADER_UPPER_ALIASES:  # evita pegar KEY ACHIEVEMENTS como empresa
            continue
        mloc = re.match(r"(.+?)\s+Location$", c.strip(), re.I)
        if mloc:
            comp = sanitize_company_line(mloc.group(1))
            comp = match_known_company(comp) or comp
            if comp:
                cands.append(comp)
            continue
        c = clean_title(c)
        if not c: continue
        if is_location_line(c):
            continue
        if c.lower() in seen: continue
        seen.add(c.lower())
        cands.append(c)

    best_role = (None, -999)
    best_company = (None, -999)
    for c in cands:
        r = score_role(c)
        comp_s = score_company(c)
        if r > best_role[1]:
            best_role = (c, r)
        if comp_s > best_company[1]:
            best_company = (c, comp_s)

    role = best_role[0] if best_role[1] >= 2 else None
    company = best_company[0] if best_company[1] >= 3 else None

    if company:
        kn = match_known_company(company)
        company = kn or sanitize_company_line(company)

    if company and role and company.lower() == role.lower():
        company = None

    return role, company

def find_company_nearby(lines: List[str], idx: int) -> Optional[str]:
    # 1) empresas conhecidas na vizinhança
    for j in range(max(0, idx-6), min(len(lines), idx+7)):
        s = clean_title(lines[j])
        if not s or is_location_line(s): continue
        if s.upper() in HEADER_UPPER_ALIASES: continue
        mloc = re.match(r"(.+?)\s+Location$", s.strip(), re.I)
        if mloc:
            cand = mloc.group(1).strip()
            known = match_known_company(cand)
            return known or sanitize_company_line(cand)
        known = match_known_company(s)
        if known:
            return known

    # 2) candidatos gerais
    window = []
    for j in range(max(0, idx-6), min(len(lines), idx+7)):
        if j == idx: continue
        s = clean_title(lines[j])
        if not s: continue
        if looks_like_header(s): continue
        if s.upper() in HEADER_UPPER_ALIASES: continue
        if is_skilly_line(s): continue
        if EDU_KEYWORDS.search(s): continue
        if ROLE_HINTS.search(s):  # evitar cargo como empresa
            continue
        if is_location_line(s):  # evitar localidade
            continue
        s2 = sanitize_company_line(s)
        if not s2: continue
        window.append(s2)

    best = (None, -999)
    for w in window:
        sc = score_company(w)
        if sc > best[1]:
            best = (w, sc)
    return best[0]

# ===== experiências =====
def is_bullet_like(s: str) -> bool:
    return bool(re.match(r"^\s*(?:[-•·–—]|\d+\.)\s+", s))

def near_education_context(lines: List[str], pivot: int) -> bool:
    # Narrow the window to immediate neighbours and prefer explicit edu headers
    for j in range(max(0, pivot-1), min(len(lines), pivot+2)):
        ln = lines[j]
        if EDU_KEYWORDS.search(ln):
            return True
        up = ln.strip().upper()
        if up in HEADER_UPPER_ALIASES and ("EDUC" in up or "FORMA" in up or "EDUCA" in up):
            return True
    return False

def _range_to_ymval(s: Optional[str]) -> Optional[int]:
    # convert YYYY-MM to integer months since year 0 for easy comparison
    if not s: return None
    m = re.match(r"(\d{4})-(\d{2})", s)
    if not m: return None
    y, mm = int(m.group(1)), int(m.group(2))
    return y * 12 + mm


def extract_experiences_global(text: str, educations: Optional[List[Education]] = None) -> List[Experience]:
    lines = extract_lines(text)
    exps: List[Experience] = []

    # build education ranges for exclusion
    edu_ranges: List[Tuple[Optional[int], Optional[int]]] = []
    if educations:
        for ed in educations:
            s = _range_to_ymval(ed.start_date) if ed.start_date else None
            e = _range_to_ymval(ed.end_date) if ed.end_date else None
            edu_ranges.append((s, e))

    # detect lines that look like a date range (reuse DATE_RANGE_RE when possible)
    for i, line in enumerate(lines):
        # ignore if the line is likely part of education section (header/keywords nearby)
        if near_education_context(lines, i):
            continue

        # if there's a date range on the line, treat as potential experience pivot
        if DATE_RANGE_RE.search(line):
            # try to parse dates from the same line
            start, end, is_current = parse_date_range(line)

            # if this date range overlaps a detected education range, skip it
            try:
                sval = _range_to_ymval(start) if start else None
                eval_ = _range_to_ymval(end) if end else None
            except Exception:
                sval = None; eval_ = None
            overlap = False
            for es, ee in edu_ranges:
                if es is None or ee is None or sval is None or eval_ is None:
                    # if any side is None, fallback to simple year-match fallback
                    if start and end and (es is not None and ee is not None) and (es <= sval <= ee or es <= eval_ <= ee):
                        overlap = True
                        break
                    continue
                # check overlap
                if not (eval_ < es or sval > ee):
                    overlap = True
                    break
            if overlap:
                continue

            # gather candidate lines around the date for role/company detection
            candidates = []
            # prefer lines above the date (role/company often appear above)
            for j in range(max(0, i-4), min(len(lines), i+4)):
                if j == i: 
                    continue
                ln = lines[j].strip()
                if not ln:
                    continue
                candidates.append(ln)

            # Try strong composite parse from the immediate previous line first
            role, company = (None, None)
            if i-1 >= 0:
                r, c = parse_composite_role_company(lines[i-1])
                if r or c:
                    role, company = r, c

            # fallback to choosing best candidates from the local window
            if not role and not company:
                role, company = choose_role_company_from_candidates(candidates)

            # final fallback: search nearby for any known company
            if not company:
                company = find_company_nearby(lines, i)

            # avoid mistaking education institution for a company
            if company and (EDU_KEYWORDS.search(company) or re.search(r"\bfurb\b", company, re.I)):
                company = None

            # Verifica se a empresa contém múltiplas tecnologias (não é empresa válida)
            if company:
                tech_keywords = [
                    "react", "angular", "vue", "flutter", "java", "python", "go", "scala",
                    "spring", "quarkus", "aws", "azure", "gcp", "docker", "kubernetes"
                ]
                
                tech_count = 0
                for tech in tech_keywords:
                    if tech.lower() in company.lower():
                        tech_count += 1
                
                # Se contém 2+ tecnologias, não é empresa válida
                if tech_count >= 2:
                    company = None
                    
                # Se contém tecnologias separadas por "e" ou ",", não é empresa válida
                if company and re.search(r'\b(?:react|angular|vue|flutter|java|python|go|scala|spring|quarkus|aws|azure|gcp)\s*(?:,|\s+e\s+|\sand\s+)\s*(?:react|angular|vue|flutter|java|python|go|scala|spring|quarkus|aws|azure|gcp)\b', company.lower()):
                    company = None

            # sanitize company again
            if company:
                company = match_known_company(company) or sanitize_company_line(company)

            # create experience only if we have at least a role or a company or non-edu-like context
            exp_conf = 0.0
            if role: exp_conf += 0.4
            if company: exp_conf += 0.5
            if start or end: exp_conf += 0.1

            # If nothing sensible found, skip (avoid creating education-as-experience)
            if exp_conf <= 0.0:
                continue

            exps.append(Experience(
                company=company,
                role=clean_title(role) if role else None,
                employment_type=None,
                start_date=start,
                end_date=end,
                is_current=is_current,
                location=None,
                achievements=[],
                tech_stack=[],
                confidence=min(exp_conf, 1.0)
            ))

    return exps

# ===== skills, nome, etc =====
def extract_all(text: str) -> ParsedCV:
    text = normalize_text_for_parsing(text)

    emails = list(set(EMAIL_RE.findall(text)))
    phones_raw = list({p.strip() for p in PHONE_BR_RE.findall(text)})
    phones = normalize_phones(phones_raw)

    links = extract_links(text)
    name = guess_name(text)

    skills = basic_skills(text)
    languages = basic_languages(text)
    # extract education first so we can avoid mis-classifying institutions as companies
    education = extract_education_global(text)
    experiences = extract_experiences_global(text, educations=education)
    certifications = extract_certifications(text)

    return ParsedCV(
        candidate=Candidate(
            full_name=name,
            emails=emails,
            phones=phones,
            links=links
        ),
        summary=None,
        skills=skills,
        languages=languages,
        experiences=experiences,
        education=education,
        certifications=certifications,
        expected_salary=None,
        availability=None,
        meta={"raw_len": len(text)}
    )

# ===== app =====
app = FastAPI(title="CV Parser Local", version="0.9.5")

@app.get("/health")
def health():
    return {"ok": True, "source_dir": SOURCE_DIR}

class ParseAllBody(BaseModel):
    pass

class ParseSingleBody(BaseModel):
    file_path: str

def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

@app.post("/cv:parse-all", response_model=ParseAllResponse)
def parse_all(_: ParseAllBody = Body(default=None)):
    if not os.path.isdir(SOURCE_DIR):
        return ParseAllResponse(results=[], scanned_dir=SOURCE_DIR)

    pdfs = [os.path.join(SOURCE_DIR, f)
            for f in os.listdir(SOURCE_DIR)
            if f.lower().endswith(".pdf")]

    results: List[ParseItem] = []
    for p in pdfs:
        started = time.time()
        try:
            raw_text = read_pdf_text(p)
            data = extract_all(raw_text)
            conf = 0.5
            if data.candidate.full_name: conf += 0.15
            if data.candidate.emails: conf += 0.1
            if data.skills: conf += 0.05
            if data.experiences: conf += 0.1
            if data.education: conf += 0.05
            if data.certifications: conf += 0.02
            conf = min(conf, 0.95)

            results.append(ParseItem(
                file=os.path.basename(p),
                hash=text_sha256(raw_text),
                data=data,
                confidence_overall=conf,
                processing_ms=int((time.time()-started)*1000)
            ))
        except Exception:
            results.append(ParseItem(
                file=os.path.basename(p),
                hash="",
                data=ParsedCV(),
                confidence_overall=0.0,
                processing_ms=0
            ))

    import json, os as _os
    _os.makedirs("output", exist_ok=True)
    with open(_os.path.join("output","ultimo_resultado.json"), "w", encoding="utf-8") as f:
        json.dump(ParseAllResponse(results=results, scanned_dir=SOURCE_DIR).model_dump(), f, ensure_ascii=False, indent=2)

    return ParseAllResponse(results=results, scanned_dir=SOURCE_DIR)

@app.post("/cv:parse-enhanced", response_model=ParseAllResponse)
def parse_all_enhanced(_: ParseAllBody = Body(default=None)):
    """Endpoint melhorado que usa o parser aprimorado"""
    try:
        from enhanced_parser import EnhancedParser
        enhanced_parser = EnhancedParser()
    except ImportError:
        return ParseAllResponse(results=[], scanned_dir=SOURCE_DIR)

    if not os.path.isdir(SOURCE_DIR):
        return ParseAllResponse(results=[], scanned_dir=SOURCE_DIR)

    pdfs = [os.path.join(SOURCE_DIR, f)
            for f in os.listdir(SOURCE_DIR)
            if f.lower().endswith(".pdf")]

    results: List[ParseItem] = []
    for p in pdfs:
        started = time.time()
        try:
            raw_text = read_pdf_text(p)
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

            results.append(ParseItem(
                file=os.path.basename(p),
                hash=text_sha256(raw_text),
                data=data,
                confidence_overall=conf,
                processing_ms=int((time.time()-started)*1000)
            ))
        except Exception as e:
            results.append(ParseItem(
                file=os.path.basename(p),
                hash="",
                data=ParsedCV(),
                confidence_overall=0.0,
                processing_ms=0
            ))

    import json, os as _os
    _os.makedirs("output", exist_ok=True)
    with open(_os.path.join("output","ultimo_resultado_enhanced.json"), "w", encoding="utf-8") as f:
        json.dump(ParseAllResponse(results=results, scanned_dir=SOURCE_DIR).model_dump(), f, ensure_ascii=False, indent=2)

    return ParseAllResponse(results=results, scanned_dir=SOURCE_DIR)

@app.post("/cv:parse-single", response_model=ParseItem)
def parse_single(body: ParseSingleBody):
    """Parse um único arquivo PDF"""
    file_path = body.file_path
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    if not file_path.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    started = time.time()
    try:
        raw_text = read_pdf_text(file_path)
        data = extract_all(raw_text)
        
        conf = 0.5
        if data.candidate.full_name: conf += 0.15
        if data.candidate.emails: conf += 0.1
        if data.skills: conf += 0.05
        if data.experiences: conf += 0.1
        if data.education: conf += 0.05
        if data.certifications: conf += 0.02
        conf = min(conf, 0.95)
        
        return ParseItem(
            file=os.path.basename(file_path),
            hash=text_sha256(raw_text),
            data=data,
            confidence_overall=conf,
            processing_ms=int((time.time()-started)*1000)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")

@app.post("/cv:parse-single-enhanced", response_model=ParseItem)
def parse_single_enhanced(body: ParseSingleBody):
    """Parse um único arquivo PDF com o parser melhorado"""
    try:
        from enhanced_parser import EnhancedParser
        enhanced_parser = EnhancedParser()
    except ImportError:
        raise HTTPException(status_code=500, detail="Parser melhorado não disponível")
    
    file_path = body.file_path
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    if not file_path.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    started = time.time()
    try:
        raw_text = read_pdf_text(file_path)
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
        
        return ParseItem(
            file=os.path.basename(file_path),
            hash=text_sha256(raw_text),
            data=data,
            confidence_overall=conf,
            processing_ms=int((time.time()-started)*1000)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")
