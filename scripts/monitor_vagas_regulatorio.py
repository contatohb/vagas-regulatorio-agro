#!/usr/bin/env python3
"""
Monitor de Vagas Regulatórias — Executivo Sênior LATAM
========================================================================

Busca vagas de Gerente / Diretor / Head / VP de Assuntos Regulatórios
(e variantes) nos setores de Agrotóxicos, Defensivos Agrícolas,
Fertilizantes, Bioinsumos, Controle de Pragas/Vetores e Sanitizantes,
em múltiplas fontes nacionais, LATAM e internacionais.

Perfil-alvo: Executivo sênior LATAM (+20 anos em multinacionais),
Médico Veterinário, fluente em PT/EN/ES, disponível para relocação.

Critérios de inclusão:
  - Cargo: Gerente, Diretor, Head, VP, Manager, Director, Lead, General Manager
    de Assuntos Regulatórios / Regulatory Affairs / Registro
    (Analista, Coordenador e Assistente são excluídos)
  - Setor: Agrotóxicos, Defensivos, Fertilizantes, Bioinsumos,
    Controle de Pragas/Vetores, Sanitizantes, Agroquímicos, Crop Protection
  - Combinação especial: Assuntos Regulatórios + Medicina Veterinária

Para vagas internacionais: todas são exibidas (candidato disponível para
relocação). Informações de visto/patrocínio são indicadas quando disponíveis.

Fontes ativas (testadas):
  - LinkedIn Jobs (endpoint público — sem autenticação)
  - Vagas.com
  - Agro2Business
  - AgCareers.com (internacional)
  - Gupy Portal (via Playwright headless)
  - Portais corporativos: Syngenta, Corteva, Bayer, BASF, UPL,
    Ourofino Agrociência, FMC, Adama, Nufarm, Koppert, Yara, Mosaic

Fontes bloqueadas (403/404 sem autenticação):
  - Indeed (403 em IPs de datacenter)
  - Catho (404 em todos os endpoints)
  - Glassdoor (403)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("monitor_vagas_regulatorio")

# ─────────────────────────────────────────────────────────────────────────────
# Configurações gerais
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
TIMEOUT = 15
SLEEP_BETWEEN = 1.0

# ─────────────────────────────────────────────────────────────────────────────
# Critérios de filtragem
# ─────────────────────────────────────────────────────────────────────────────

# Cargos-alvo: apenas níveis seniores compatíveis com o perfil do candidato
# (Executivo LATAM com +20 anos em multinacionais — Syngenta, Bayer, ENVU)
# Analista, Coordenador e Assistente são excluídos intencionalmente.
CARGOS_ALVO = [
    # Nível executivo / diretivo
    "gerente", "diretor", "diretora", "head", "vice-presidente", "vp",
    "chief", "executive", "general manager",
    # Manager e variantes
    "senior manager", "sr. manager", "sr manager", "manager", "director",
    "executive manager", "latam manager", "latam lead",
    # Lead / Líder
    "líder", "lider", "lead",
    # Supervisor sênior
    "supervisor sênior", "supervisor senior",
]

TERMOS_REGULATORIO = [
    "regulatório", "regulatoria", "regulatorio", "regulatory",
    "assuntos regulatórios", "assuntos regulatorios", "regulatory affairs",
    "registro", "registros", "licenciamento", "compliance regulatório",
    "regulatory compliance", "registrations", "product registration",
    "registro de produtos", "registro de agrotóxicos", "registro de defensivos",
    "reg affairs", "assuntos regulat",
]

TERMOS_SETOR = [
    # Agrotóxicos / Defensivos
    "agrotóxico", "agrotoxicos", "agrotóxicos", "agrochemical", "agrochemicals",
    "defensivo agrícola", "defensivos agrícolas", "defensivo agricola",
    "crop protection", "pesticid", "herbicid", "fungicid", "insecticid",
    # Fertilizantes
    "fertilizante", "fertilizantes", "fertilizer", "fertilizers",
    # Biológicos / Bioinsumos
    "bioinsumo", "bioinsumos", "bioinput", "bioinputs", "biodefensivo",
    "bioestimulante", "bioestimulantes", "biostimulant",
    "biologicals", "biological", "biológico", "biologico",
    "semiochemical", "semioquímico", "semioquimico",
    # Controle de pragas e vetores (Bayer Environmental Science / ENVU)
    "controle de pragas", "pest control", "vector control", "controle vetorial",
    "environmental science", "urban pest", "pragas urbanas",
    "envu", "bayer environmental",
    # Sanitizantes
    "sanitizante", "sanitizantes", "sanitizer", "sanitizers",
    "desinfetante", "desinfetantes", "disinfectant",
    # Agroquímicos / Agrociência
    "agroquímico", "agroquimico", "agroquímicos",
    "agrociência", "agrociencia", "agroscience",
    "agribusiness", "agronegócio", "agronegocio",
    # Empresas do setor (nacionais e internacionais)
    "syngenta", "corteva", "bayer cropscience", "basf agro", "upl",
    "ourofino", "fmc", "adama", "nufarm", "sumitomo chemical",
    "koppert", "lavoro", "heringer", "mosaic", "yara", "compo expert",
    "nutrien", "icl", "arysta", "dow agrosciences", "dupont",
    "pi industries", "rallis", "gharda", "dhanuka", "arysta lifecience",
    "rotam", "sipcam", "albaugh", "cheminova", "makhteshim",
    # Órgãos reguladores e contexto
    "mapa", "ministério da agricultura",
    # Termos agrícolas específicos (evitar genéricos como 'agri' ou 'agricultural')
    "plant science", "plant health", "crop science",
    "seed", "seeds", "semente", "sementes",
    "precision agriculture", "agricultura de precisão",
]

# Termos que indicam setores FORA do escopo (exclusão)
# Se qualquer um desses termos aparecer no título, a vaga é descartada
TERMOS_EXCLUSAO_SETOR = [
    # Água e tratamento
    "stormwater", "storm water", "wastewater", "waste water",
    "pool", "swimming pool", "hot tub", "piscina",
    "water treatment", "tratamento de água",
    # Farmacêutico / Médico
    "pharmaceutical", "pharma", "farmacêutico", "farmaceutico",
    "medical device", "dispositivo médico",
    "drug", "medicine", "medicamento",
    # Cosmético
    "cosmetic", "cosmético", "cosmetico",
    # Alimentos (exceto quando combinado com agro)
    "food safety", "food regulatory",
    # Automotivo / Transporte
    "automotive", "automotivo", "vehicle", "veículo",
    # Financeiro
    "financial", "fintech", "banking", "banco",
    # Telecom
    "telecom", "telecommunication",
    # Mineração / Energia
    "mining", "mineração",
    "oil and gas", "petróleo",
    "nuclear",
    # Aviação
    "aviation", "aerospace",
]

TERMOS_VETERINARIA = [
    "medicina veterinária", "medicina veterinaria", "veterinário", "veterinaria",
    "veterinary", "médico veterinário", "medico veterinario",
    "mv ", "m.v.", "crmv",
]

PAISES_BRASIL = [
    "brasil", "brazil", "br,", "(br)", "são paulo", "sao paulo",
    "rio de janeiro", "belo horizonte", "curitiba", "porto alegre",
    "campinas", "piracicaba", "ribeirão preto", "ribeirao preto",
    "goiânia", "goiania", "brasília", "brasilia", "recife", "fortaleza",
    "manaus", "belém", "belem", "salvador", "florianópolis", "florianopolis",
    "uberlândia", "uberlandia", "londrina", "joinville", "natal",
    "são josé dos campos", "sao jose dos campos", "sorocaba", "sp,", "rj,",
    "mg,", "pr,", "rs,", "sc,", "go,", "df,", "ba,", "pe,",
    "sp -", "rj -", "mg -", "pr -", "rs -", "sc -",
    "interior de sp", "interior de mg",
]

# Queries LinkedIn — otimizadas para cobertura e velocidade
# Cada tupla: (keywords, location)
# Location "Brazil" filtra resultados nacionais; string vazia = global
LINKEDIN_QUERIES = [
    # ── Nacionais: queries em português com localização Brasil ──────────────
    ("gerente assuntos regulatorios agrotoxicos", "Brazil"),
    ("gerente regulatorio defensivos agricolas", "Brazil"),
    ("diretor assuntos regulatorios agroquimicos", "Brazil"),
    ("gerente registro agrotoxicos fertilizantes", "Brazil"),
    ("regulatory affairs manager crop protection", "Brazil"),
    ("head regulatory affairs agriculture", "Brazil"),
    ("assuntos regulatorios defensivos", "Brazil"),
    ("gerente regulatorio controle pragas", "Brazil"),
    ("regulatory affairs manager pest control", "Brazil"),
    # ── Nacionais: queries com empresas do setor ─────────────────────────
    ("regulatory affairs syngenta", "Brazil"),
    ("regulatory affairs corteva", "Brazil"),
    ("regulatory affairs bayer", "Brazil"),
    ("regulatory affairs ourofino", "Brazil"),
    ("regulatory affairs upl", "Brazil"),
    ("regulatory affairs basf agro", "Brazil"),
    ("regulatory affairs envu", "Brazil"),
    # ── LATAM: vagas regionais com escopo LATAM ──────────────────────────
    ("LATAM regulatory affairs manager agrochemical", ""),
    ("LATAM regulatory affairs director", ""),
    ("regulatory affairs lead LATAM crop protection", ""),
    ("head regulatory affairs LATAM agriculture", ""),
    ("regulatory affairs manager Latin America", ""),
    # ── Internacionais: crop protection global ────────────────────────────
    ("director regulatory affairs crop protection", ""),
    ("regulatory affairs director agrochemical", ""),
    ("senior manager regulatory affairs agriculture", ""),
    ("head regulatory affairs agrochemical", ""),
    ("VP regulatory affairs agrochemical", ""),
    ("chief regulatory officer agriculture", ""),
    ("director regulatory affairs pest control", ""),
    ("regulatory affairs manager environmental science", ""),
]


def _normalizar(texto: str) -> str:
    return texto.lower().strip()


def _gerar_id(vaga: Dict) -> str:
    chave = f"{vaga.get('titulo', '')}{vaga.get('empresa', '')}{vaga.get('link', '')}"
    return hashlib.md5(chave.encode("utf-8")).hexdigest()


def _eh_cargo_alvo(titulo: str, descricao: str = "") -> bool:
    texto = _normalizar(f"{titulo} {descricao[:500]}")
    tem_cargo = any(c in texto for c in CARGOS_ALVO)
    if not tem_cargo:
        return False
    tem_reg = any(r in texto for r in TERMOS_REGULATORIO)
    return tem_reg


def _eh_setor_alvo(titulo: str, descricao: str = "", empresa: str = "") -> bool:
    texto = _normalizar(f"{titulo} {descricao[:1000]} {empresa}")
    return any(s in texto for s in TERMOS_SETOR)


def _eh_combinacao_veterinaria(titulo: str, descricao: str = "") -> bool:
    texto = _normalizar(f"{titulo} {descricao[:1000]}")
    tem_reg = any(r in texto for r in TERMOS_REGULATORIO)
    tem_vet = any(v in texto for v in TERMOS_VETERINARIA)
    return tem_reg and tem_vet


# Portais especializados em agronegócio: cargo regulatório é suficiente
# (setor agro é implícito pela especialização do portal)
PORTAIS_AGRO_ESPECIALIZADOS = {
    "agrobase", "agro2business", "agcareers", "gupy",
}


def _eh_vaga_relevante(vaga: Dict) -> bool:
    titulo = vaga.get("titulo", "")
    descricao = vaga.get("descricao", "")
    empresa = vaga.get("empresa", "")
    fonte = vaga.get("fonte", "").lower()
    titulo_lower = _normalizar(titulo)
    # Verificar exclusão no título + empresa + primeiros 300 chars da descrição
    texto_exclusao = _normalizar(f"{titulo} {empresa} {descricao[:300]}")

    # Exclusão imediata: setor claramente fora do escopo
    if any(t in texto_exclusao for t in TERMOS_EXCLUSAO_SETOR):
        return False

    # Regra 1: cargo regulatório + setor agro
    if _eh_cargo_alvo(titulo, descricao) and _eh_setor_alvo(titulo, descricao, empresa):
        return True

    # Regra 2: cargo regulatório + combinação veterinária
    if _eh_cargo_alvo(titulo, descricao) and _eh_combinacao_veterinaria(titulo, descricao):
        return True

    # Regra 3: portais especializados em agronegócio — cargo regulatório é suficiente
    # (o setor agro é implícito pela especialização do portal)
    if any(p in fonte for p in PORTAIS_AGRO_ESPECIALIZADOS):
        if _eh_cargo_alvo(titulo, descricao):
            return True

    # Regra 4: cargo executivo de alto nível (Director, VP, Head, Chief) + setor agro
    # Mesmo sem 'regulatory' no título, vagas executivas em empresas agro são relevantes
    CARGOS_EXECUTIVOS = ["director", "diretor", "diretora", "head", "vice-presidente", "vp", "chief", "general manager"]
    titulo_norm = _normalizar(titulo)
    tem_cargo_exec = any(c in titulo_norm for c in CARGOS_EXECUTIVOS)
    if tem_cargo_exec and _eh_setor_alvo(titulo, descricao, empresa):
        return True

    return False


def _eh_internacional(vaga: Dict) -> bool:
    localizacao = _normalizar(vaga.get("localizacao", ""))
    if not localizacao or localizacao in ["", "não informado", "remoto", "remote"]:
        return False
    return not any(p in localizacao for p in PAISES_BRASIL)


def _investigar_vaga_internacional(vaga: Dict) -> Dict:
    descricao = _normalizar(vaga.get("descricao", ""))
    titulo = _normalizar(vaga.get("titulo", ""))
    texto = f"{titulo} {descricao}"

    termos_sponsorship = [
        "visa sponsorship", "sponsorship available", "will sponsor",
        "visa support", "relocation support", "relocation package",
    ]
    termos_sem_sponsorship = [
        "no visa sponsorship", "not provide visa", "not sponsor",
        "must be authorized", "must have authorization", "must have work permit",
        "authorization to work", "eligible to work", "right to work",
    ]

    if any(t in texto for t in termos_sem_sponsorship):
        vaga["aceita_sem_visto"] = False
    elif any(t in texto for t in termos_sponsorship):
        vaga["aceita_sem_visto"] = True
    else:
        vaga["aceita_sem_visto"] = None

    if not vaga.get("modalidade_trabalho"):
        termos_remoto = ["remote", "remoto", "work from home", "home office",
                         "fully remote", "100% remote", "anywhere"]
        termos_hibrido = ["hybrid", "híbrido", "hibrido", "flexible"]
        termos_presencial = ["on-site", "onsite", "in-office", "presencial"]

        if any(t in texto for t in termos_remoto):
            vaga["modalidade_trabalho"] = "Remoto"
        elif any(t in texto for t in termos_hibrido):
            vaga["modalidade_trabalho"] = "Híbrido"
        elif any(t in texto for t in termos_presencial):
            vaga["modalidade_trabalho"] = "Presencial"
        else:
            vaga["modalidade_trabalho"] = None

    return vaga


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários HTTP
# ─────────────────────────────────────────────────────────────────────────────

def _get_html(url: str, session: requests.Session, extra_headers: dict = None) -> Optional[str]:
    try:
        hdrs = dict(HEADERS)
        if extra_headers:
            hdrs.update(extra_headers)
        r = session.get(url, timeout=TIMEOUT, headers=hdrs)
        if r.status_code in [200, 301, 302]:
            return r.text
        logger.debug(f"HTTP {r.status_code}: {url[:80]}")
        return None
    except Exception as exc:
        logger.debug(f"GET {url[:80]}: {exc}")
        return None


def _base_url(url: str) -> str:
    from urllib.parse import urlparse
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _normalizar_data(texto: str) -> str:
    """
    Normaliza qualquer representação de data para o formato dd/mm/aaaa.

    Entradas aceitas:
      - ISO 8601: "2026-03-18" ou "2026-03-18T10:00:00Z"
      - Brasileiro: "18/03/2026" ou "18-03-2026"
      - Relativo EN: "2 days ago", "1 day ago", "3 hours ago", "just now"
      - Relativo PT: "há 2 dias", "há 1 dia", "há 3 horas", "agora"
      - Texto livre: "March 18, 2026", "18 de março de 2026"
      - Vazio / não reconhecido: retorna string original sem modificação
    """
    if not texto:
        return ""
    texto = str(texto).strip()

    hoje = date.today()

    # ── Já está no formato dd/mm/aaaa ──────────────────────────────────────
    if re.match(r"^\d{2}/\d{2}/\d{4}$", texto):
        return texto

    # ── ISO 8601: 2026-03-18 ou 2026-03-18T... ────────────────────────────
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto)
    if m:
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return d.strftime("%d/%m/%Y")
        except ValueError:
            pass

    # ── Formato dd-mm-aaaa ────────────────────────────────────────────────
    m = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", texto)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return d.strftime("%d/%m/%Y")
        except ValueError:
            pass

    # ── Relativo em inglês: "X days ago", "X hours ago", "just now" ───────
    t_lower = texto.lower()
    m = re.match(r"(\d+)\s+day[s]?\s+ago", t_lower)
    if m:
        delta = date.fromordinal(hoje.toordinal() - int(m.group(1)))
        return delta.strftime("%d/%m/%Y")
    m = re.match(r"(\d+)\s+hour[s]?\s+ago", t_lower)
    if m:
        return hoje.strftime("%d/%m/%Y")  # mesmo dia
    m = re.match(r"(\d+)\s+minute[s]?\s+ago", t_lower)
    if m:
        return hoje.strftime("%d/%m/%Y")
    if t_lower in ("just now", "agora", "hoje", "today"):
        return hoje.strftime("%d/%m/%Y")

    # ── Relativo em português: "há X dias", "há X horas" ─────────────────
    m = re.match(r"h[áa]\s+(\d+)\s+dia[s]?", t_lower)
    if m:
        delta = date.fromordinal(hoje.toordinal() - int(m.group(1)))
        return delta.strftime("%d/%m/%Y")
    m = re.match(r"h[áa]\s+(\d+)\s+hora[s]?", t_lower)
    if m:
        return hoje.strftime("%d/%m/%Y")
    m = re.match(r"h[áa]\s+(\d+)\s+semana[s]?", t_lower)
    if m:
        delta = date.fromordinal(hoje.toordinal() - int(m.group(1)) * 7)
        return delta.strftime("%d/%m/%Y")

    # ── Meses por extenso em inglês: "March 18, 2026" ─────────────────────
    _MESES_EN = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m = re.search(r"([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", t_lower)
    if m and m.group(1) in _MESES_EN:
        try:
            d = date(int(m.group(3)), _MESES_EN[m.group(1)], int(m.group(2)))
            return d.strftime("%d/%m/%Y")
        except (ValueError, KeyError):
            pass
    # "18 March 2026"
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", t_lower)
    if m and m.group(2) in _MESES_EN:
        try:
            d = date(int(m.group(3)), _MESES_EN[m.group(2)], int(m.group(1)))
            return d.strftime("%d/%m/%Y")
        except (ValueError, KeyError):
            pass

    # ── Meses por extenso em português: "18 de março de 2026" ────────────
    _MESES_PT = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    }
    for nome, num in _MESES_PT.items():
        m = re.search(rf"(\d{{1,2}})\s+de\s+{nome}\s+de\s+(\d{{4}})", t_lower)
        if m:
            try:
                d = date(int(m.group(2)), num, int(m.group(1)))
                return d.strftime("%d/%m/%Y")
            except ValueError:
                pass

    # ── Não reconhecido: retorna o texto original ─────────────────────────
    return texto


def _make_vaga(titulo: str, empresa: str, localizacao: str, link: str,
               fonte: str, descricao: str = "", salario: str = "",
               tipo_contrato: str = "", data_pub: str = "") -> Dict:
    vaga_id = _gerar_id({"titulo": titulo, "empresa": empresa, "link": link})
    return {
        "id": vaga_id,
        "titulo": titulo,
        "empresa": empresa,
        "localizacao": localizacao,
        "link": link,
        "data_publicacao": _normalizar_data(data_pub),
        "fonte": fonte,
        "descricao": descricao,
        "requisitos": "",
        "tipo_contrato": tipo_contrato,
        "salario": salario,
        "modalidade_trabalho": "",
        "aceita_sem_visto": None,
        "data_coleta": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Fonte 1: LinkedIn Jobs (endpoint público)
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_serpapi_google_jobs(api_key: str) -> List[Dict]:
    """
    Busca vagas no Google Jobs via SerpAPI.
    Alternativa robusta ao LinkedIn jobs-guest quando rodando em IPs de datacenter.
    Requer SERPAPI_KEY configurada como secret no GitHub Actions.
    """
    if not api_key:
        return []

    queries = [
        "gerente assuntos regulatorios agrotoxicos",
        "regulatory affairs manager crop protection Brazil",
        "diretor assuntos regulatorios defensivos agricolas",
        "LATAM regulatory affairs manager agrochemical",
        "director regulatory affairs crop protection",
        "head regulatory affairs agriculture Brazil",
    ]

    vagas: List[Dict] = []
    seen_ids: set = set()

    for query in queries:
        try:
            params = {
                "engine": "google_jobs",
                "q": query,
                "api_key": api_key,
                "hl": "pt",
                "gl": "br",
                "chips": "date_posted:week",  # últimos 7 dias
            }
            r = requests.get("https://serpapi.com/search", params=params, timeout=20)
            if r.status_code != 200:
                logger.debug(f"SerpAPI [{query}]: HTTP {r.status_code}")
                continue
            data = r.json()
            for job in data.get("jobs_results", []):
                titulo = job.get("title", "").strip()
                empresa = job.get("company_name", "").strip()
                localizacao = job.get("location", "").strip()
                link = ""
                # Prefer direct apply link
                for ext in job.get("detected_extensions", {}).keys():
                    pass
                apply_options = job.get("apply_options", [])
                if apply_options:
                    link = apply_options[0].get("link", "")
                if not link:
                    link = job.get("share_link", f"https://www.google.com/search?q={quote_plus(titulo + ' ' + empresa)}")

                vaga_id = _gerar_id({"titulo": titulo, "empresa": empresa, "link": link})
                if vaga_id in seen_ids:
                    continue
                seen_ids.add(vaga_id)

                descricao = job.get("description", "")[:400]
                data_pub = job.get("detected_extensions", {}).get("posted_at", "")

                vagas.append(_make_vaga(
                    titulo=titulo,
                    empresa=empresa,
                    localizacao=localizacao,
                    link=link,
                    descricao=descricao,
                    data_pub=data_pub,
                    fonte="SerpAPI/Google Jobs",
                ))
            time.sleep(SLEEP_BETWEEN)
        except Exception as exc:
            logger.debug(f"SerpAPI [{query}]: {exc}")
            continue

    return vagas


def _buscar_linkedin(session: requests.Session) -> List[Dict]:
    """
    Busca vagas no LinkedIn via endpoint jobs-guest (sem autenticação).
    Usa múltiplas queries. O filtro de relevância posterior descarta os
    resultados não-agro (farmacêutico, financeiro, etc.).

    Endpoint funcional verificado em 18/03/2026:
      https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
    """
    vagas = []
    seen_ids: set = set()

    for keyword, location in LINKEDIN_QUERIES:
        params = {
            "keywords": keyword,
            "start": 0,
            "count": 25,
            "sortBy": "DD",
        }
        if location:
            params["location"] = location

        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        try:
            r = session.get(url, params=params, timeout=TIMEOUT, headers=HEADERS)
            if r.status_code != 200 or len(r.text) < 100:
                logger.debug(f"LinkedIn jobs-guest: HTTP {r.status_code} para '{keyword}'")
                time.sleep(SLEEP_BETWEEN)
                continue
            html = r.text
        except Exception as exc:
            logger.debug(f"LinkedIn jobs-guest: {exc}")
            time.sleep(SLEEP_BETWEEN)
            continue

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("li")

        for card in cards:
            try:
                h3 = card.find("h3", class_="base-search-card__title") or card.find("h3")
                titulo = h3.get_text(strip=True) if h3 else ""

                h4 = card.find("h4", class_="base-search-card__subtitle") or card.find("h4")
                empresa = h4.get_text(strip=True) if h4 else ""

                span_loc = card.find("span", class_="job-search-card__location")
                localizacao = span_loc.get_text(strip=True) if span_loc else ""

                link_el = card.find("a", class_="base-card__full-link") or card.find("a", href=re.compile(r"/jobs/view/"))
                link = ""
                if link_el:
                    href = link_el.get("href", "")
                    link = href.split("?")[0] if href else ""
                # Fallback: se link direto não foi extraído, usar URL de busca do LinkedIn
                # (link funcional que leva à página de resultados com a mesma query)
                if not link and keyword:
                    _kw = quote_plus(keyword)
                    _loc = quote_plus(location) if location else ""
                    link = (f"https://www.linkedin.com/jobs/search/?keywords={_kw}"
                            + (f"&location={_loc}" if _loc else ""))

                if not titulo:
                    continue

                vaga_id = _gerar_id({"titulo": titulo, "empresa": empresa, "link": link})
                if vaga_id in seen_ids:
                    continue
                seen_ids.add(vaga_id)

                time_el = card.find("time")
                data_pub = ""
                if time_el:
                    data_pub = time_el.get("datetime", time_el.get_text(strip=True))

                vagas.append(_make_vaga(titulo, empresa, localizacao, link,
                                        "LinkedIn", data_pub=data_pub))

            except Exception as exc:
                logger.debug(f"LinkedIn card: {exc}")

        time.sleep(SLEEP_BETWEEN)

    logger.info(f"LinkedIn: {len(vagas)} vagas coletadas")
    return vagas


# ─────────────────────────────────────────────────────────────────────────────
# Fonte 2: Vagas.com
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_vagascom(session: requests.Session) -> List[Dict]:
    """
    Vagas.com — DESABILITADO: site redireciona todo tráfego requests via JavaScript
    para site.vagas.com.br/GoHome.asp — scraping por requests é impossível.
    Mantido como stub para não quebrar o pipeline.
    """
    logger.warning(
        "Vagas.com: DESABILITADO — site usa redirecionamento JS (GoHome.asp) "
        "que impede scraping por requests. Retornando lista vazia."
    )
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Fonte 3: Agro2Business
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_agro2business(session: requests.Session) -> List[Dict]:
    """
    Agro2Business — DESABILITADO: certificado SSL inválido (hostname mismatch).
    Mantido como stub para não quebrar o pipeline.
    """
    logger.warning(
        "Agro2Business: DESABILITADO — erro de certificado SSL (hostname mismatch). "
        "Retornando lista vazia."
    )
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Fonte 4: Agrobase (portal especializado em agronegócio)
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_agrobase(session: requests.Session) -> List[Dict]:
    """
    Agrobase.com.br — portal especializado em agronegócio com API WordPress.
    Usa a API WP REST para buscar vagas de assuntos regulatórios no setor agro.
    Verificado funcional em 18/03/2026.
    """
    vagas = []
    seen_ids: set = set()

    queries = [
        "regulatorio",
        "regulatory",
        "registro",
        "assuntos regulatorios",
        "defensivos",
        "agrotoxicos",
    ]

    for q in queries:
        url = f"https://www.agrobase.com.br/wp-json/wp/v2/posts?per_page=20&search={quote_plus(q)}"
        try:
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code != 200:
                logger.debug(f"Agrobase: HTTP {r.status_code} para '{q}'")
                time.sleep(SLEEP_BETWEEN)
                continue
            posts = r.json()
            if not isinstance(posts, list):
                continue
        except Exception as exc:
            logger.debug(f"Agrobase: {exc}")
            time.sleep(SLEEP_BETWEEN)
            continue

        for post in posts:
            try:
                titulo_raw = post.get("title", {}).get("rendered", "")
                # Remover tags HTML do título
                titulo = BeautifulSoup(titulo_raw, "html.parser").get_text(strip=True)

                link = post.get("link", "")

                # Extrair localização do título (padrão: "Cargo – Cidade/UF")
                localizacao = ""
                loc_match = re.search(r"[–\-] ?([A-Z][a-z].{3,30})$", titulo)
                if loc_match:
                    localizacao = loc_match.group(1).strip()

                # Descrição do excerpt
                excerpt_raw = post.get("excerpt", {}).get("rendered", "")
                descricao = BeautifulSoup(excerpt_raw, "html.parser").get_text(strip=True)[:500]

                # Data de publicação
                data_pub = post.get("date", "")[:10]  # ISO 8601: YYYY-MM-DD

                if not titulo or len(titulo) < 5:
                    continue

                vaga_id = _gerar_id({"titulo": titulo, "empresa": "", "link": link})
                if vaga_id in seen_ids:
                    continue
                seen_ids.add(vaga_id)

                vagas.append(_make_vaga(
                    titulo=titulo,
                    empresa="",  # Agrobase não expoe empresa na API pública
                    localizacao=localizacao,
                    link=link,
                    fonte="Agrobase",
                    descricao=descricao,
                    data_pub=data_pub,
                ))

            except Exception as exc:
                logger.debug(f"Agrobase post: {exc}")

        time.sleep(SLEEP_BETWEEN)

    logger.info(f"Agrobase: {len(vagas)} vagas coletadas")
    return vagas


# ─────────────────────────────────────────────────────────────────────────────
# Fonte 5: AgCareers (internacional)
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_agcareers(session: requests.Session) -> List[Dict]:
    """
    AgCareers.com — portal especializado em agronegócio internacional.
    """
    vagas = []
    seen_ids: set = set()

    queries = [
        "regulatory affairs manager",
        "regulatory affairs director",
        "head regulatory affairs",
        "regulatory affairs agriculture",
        "regulatory affairs agrochemical",
        "regulatory affairs crop protection",
    ]

    for query in queries:
        url = f"https://www.agcareers.com/results.cfm?keywords={quote_plus(query)}&OrderBy=IsNull(r.Rank%2C+0)+DESC%2C+LastUpdated+Desc&headerSearchform=yes"
        html = _get_html(url, session)
        if not html:
            time.sleep(SLEEP_BETWEEN)
            continue

        soup = BeautifulSoup(html, "html.parser")

        # AgCareers usa diferentes estruturas de card
        cards = soup.find_all(["div", "li", "article"],
                               class_=re.compile(r"job|listing|result|position", re.I))

        for card in cards:
            try:
                titulo_el = card.find(["h2", "h3", "a"],
                                       class_=re.compile(r"title|job|position", re.I))
                titulo = titulo_el.get_text(strip=True) if titulo_el else ""

                empresa_el = card.find(["span", "div"],
                                        class_=re.compile(r"company|employer|org", re.I))
                empresa = empresa_el.get_text(strip=True) if empresa_el else ""

                loc_el = card.find(["span", "div"],
                                    class_=re.compile(r"location|city|place", re.I))
                localizacao = loc_el.get_text(strip=True) if loc_el else ""

                link_el = card.find("a", href=True)
                link = ""
                if link_el:
                    href = link_el.get("href", "")
                    link = href if href.startswith("http") else f"https://www.agcareers.com{href}"

                if not titulo or len(titulo) < 5:
                    continue

                vaga_id = _gerar_id({"titulo": titulo, "empresa": empresa, "link": link})
                if vaga_id in seen_ids:
                    continue
                seen_ids.add(vaga_id)

                vagas.append(_make_vaga(titulo, empresa, localizacao, link or url,
                                        "AgCareers (Internacional)"))

            except Exception as exc:
                logger.debug(f"AgCareers card: {exc}")

        time.sleep(SLEEP_BETWEEN)

    logger.info(f"AgCareers: {len(vagas)} vagas")
    return vagas


# ─────────────────────────────────────────────────────────────────────────────
# Fonte 5: Gupy Portal (via Playwright)
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_gupy_playwright() -> List[Dict]:
    """
    Gupy Portal — usa React/Next.js, requer Playwright para renderização.
    Busca vagas regulatórias no portal de vagas do Gupy.
    """
    vagas = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.debug("Playwright não disponível para Gupy")
        return vagas

    exe = "/home/ubuntu/.cache/ms-playwright/chromium_headless_shell-1187/chrome-linux/headless_shell"
    if not os.path.exists(exe):
        logger.debug("Playwright headless shell não encontrado")
        return vagas

    queries = [
        "regulatory affairs",
        "assuntos regulatorios",
        "gerente regulatorio",
        "registro agrotoxicos",
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=exe,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            ctx = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="pt-BR",
            )
            page = ctx.new_page()
            seen_ids: set = set()

            for query in queries:
                try:
                    url = f"https://portal.gupy.io/job-search/term={quote_plus(query)}"
                    page.goto(url, timeout=25000, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)

                    # Aguardar cards carregarem
                    try:
                        page.wait_for_selector("[data-testid='job-card'], article, li[class*='job']",
                                               timeout=8000)
                    except Exception:
                        pass

                    # Extrair cards
                    cards = page.query_selector_all(
                        "[data-testid='job-card'], article[class*='job'], "
                        "li[class*='job'], div[class*='job-card']"
                    )

                    for card in cards:
                        try:
                            txt = card.inner_text()
                            linhas = [l.strip() for l in txt.split("\n") if l.strip()]
                            titulo = linhas[0] if linhas else ""
                            empresa = linhas[1] if len(linhas) > 1 else ""
                            localizacao = linhas[2] if len(linhas) > 2 else ""

                            # Pegar link
                            link_el = card.query_selector("a[href]")
                            link = ""
                            if link_el:
                                href = link_el.get_attribute("href") or ""
                                link = href if href.startswith("http") else f"https://portal.gupy.io{href}"

                            if not titulo or len(titulo) < 5:
                                continue

                            vaga_id = _gerar_id({"titulo": titulo, "empresa": empresa, "link": link})
                            if vaga_id in seen_ids:
                                continue
                            seen_ids.add(vaga_id)

                            vagas.append(_make_vaga(titulo, empresa, localizacao, link or url,
                                                    "Gupy Portal"))
                        except Exception:
                            pass

                    time.sleep(SLEEP_BETWEEN)

                except Exception as exc:
                    logger.debug(f"Gupy query '{query}': {exc}")

            ctx.close()
            browser.close()

    except Exception as exc:
        logger.debug(f"Gupy Playwright: {exc}")

    logger.info(f"Gupy: {len(vagas)} vagas")
    return vagas


# ─────────────────────────────────────────────────────────────────────────────
# Fonte 6: Portais corporativos
# ──────────────────────────────────────────────────────────────────────────────
# Fonte 6b: Gupy Company Subdomains (via __NEXT_DATA__ SSR)
# ──────────────────────────────────────────────────────────────────────────────

# Empresas do setor agro/fitossanitário com portais Gupy ativos (verificados)
GUPY_SUBDOMAINS = [
    {"subdomain": "ourofinoagro",  "empresa": "Ourofino Agrociência"},
    {"subdomain": "ihara",          "empresa": "IHARA"},
    {"subdomain": "adama",          "empresa": "ADAMA Brasil"},
    {"subdomain": "nortox",         "empresa": "Nortox"},
    {"subdomain": "heringer",       "empresa": "Heringer"},
    {"subdomain": "coopercitrus",   "empresa": "Coopercitrus"},
    {"subdomain": "ourofino",       "empresa": "Ourofino Saúde Animal"},
    {"subdomain": "terra",          "empresa": "Terra Agro"},
]


def _buscar_gupy_subdomains(session: requests.Session) -> List[Dict]:
    """
    Portais Gupy de empresas do agronegócio — usa __NEXT_DATA__ (Next.js SSR).
    Cada portal exporta a lista de vagas abertas no HTML inicial sem JS.
    Filtra por palavras-chave regulatórias após coleta.
    Verificado funcional em 2026-05.
    """
    vagas = []
    seen_ids: set = set()

    TERMOS_BUSCA = [
        "regulat", "regulatory", "registro", "assuntos reg",
        "fitossanit", "agrotoxico", "agrotóxico", "defensivo",
        "rastreab", "compliance", "licenciamento", "ambiental",
        "estudos oficiais", "registro de produto", "aprovação de produto",
        "product registration", "label", "rotulagem",
    ]

    for portal in GUPY_SUBDOMAINS:
        subdomain = portal["subdomain"]
        empresa = portal["empresa"]
        url = f"https://{subdomain}.gupy.io/"
        try:
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code != 200:
                logger.debug(f"Gupy/{subdomain}: HTTP {r.status_code}")
                time.sleep(SLEEP_BETWEEN)
                continue

            # Extrair __NEXT_DATA__ do SSR
            nd_match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                r.text, re.DOTALL
            )
            if not nd_match:
                logger.debug(f"Gupy/{subdomain}: __NEXT_DATA__ não encontrado")
                time.sleep(SLEEP_BETWEEN)
                continue

            import json as _json
            data = _json.loads(nd_match.group(1))
            jobs = data.get("props", {}).get("pageProps", {}).get("jobs", [])

            for job in jobs:
                try:
                    titulo = job.get("title", "") or ""
                    if not titulo or len(titulo) < 5:
                        continue

                    job_id = job.get("id", "")
                    workplace = job.get("workplace", {}) or {}
                    addr = workplace.get("address", {}) or {}
                    city = addr.get("city", "")
                    state = addr.get("stateShortName", "")
                    localizacao = f"{city}/{state}".strip("/") if city or state else ""

                    link = f"https://{subdomain}.gupy.io/job/{job_id}" if job_id else url
                    descricao = job.get("description", "") or ""

                    # Filtrar por relevância regulatória
                    texto_check = (titulo + " " + descricao).lower()
                    if not any(t in texto_check for t in TERMOS_BUSCA):
                        continue

                    vaga_id = _gerar_id({"titulo": titulo, "empresa": empresa, "link": link})
                    if vaga_id in seen_ids:
                        continue
                    seen_ids.add(vaga_id)

                    vagas.append(_make_vaga(
                        titulo=titulo,
                        empresa=empresa,
                        localizacao=localizacao,
                        link=link,
                        fonte="Gupy",
                        descricao=descricao,
                    ))
                except Exception as exc:
                    logger.debug(f"Gupy/{subdomain} job: {exc}")

        except Exception as exc:
            logger.debug(f"Gupy/{subdomain}: {exc}")

        time.sleep(SLEEP_BETWEEN)

    logger.info(f"Gupy subdomains: {len(vagas)} vagas regulatórias encontradas")
    return vagas


# ─────────────────────────────────────────────────────────────────────────────

PORTAIS_CORPORATIVOS = [
    {
        "empresa": "Syngenta",
        "urls": [
            "https://www.syngenta.com/en/careers/job-search?query=regulatory+affairs&country=BR",
            "https://www.syngenta.com/en/careers/job-search?query=regulatory",
        ],
    },
    {
        "empresa": "Corteva",
        "urls": [
            "https://careers.corteva.com/search-jobs?q=regulatory+affairs&l=Brazil",
        ],
    },
    {
        "empresa": "Bayer",
        "urls": [
            "https://career.bayer.com/en/jobs?q=regulatory+affairs&country=Brazil",
        ],
    },
    {
        "empresa": "BASF",
        "urls": [
            "https://www.basf.com/global/en/careers/job-search.html?q=regulatory&country=BR",
        ],
    },
    {
        "empresa": "UPL",
        "urls": [
            "https://www.upl-ltd.com/careers?search=regulatory",
        ],
    },
    {
        "empresa": "FMC",
        "urls": [
            "https://fmc.wd1.myworkdayjobs.com/en-US/FMC_Careers?q=regulatory",
        ],
    },
    {
        "empresa": "Adama",
        "urls": [
            "https://www.adama.com/global/en/careers.html",
        ],
    },
    {
        "empresa": "Nufarm",
        "urls": [
            "https://www.nufarm.com/global/careers/",
        ],
    },
    {
        "empresa": "Koppert",
        "urls": [
            "https://www.koppert.com/careers/",
        ],
    },
    {
        "empresa": "Yara",
        "urls": [
            "https://www.yara.com/careers/open-positions/?q=regulatory",
        ],
    },
    {
        "empresa": "Mosaic",
        "urls": [
            "https://www.mosaicco.com/careers",
        ],
    },
]  # FIM_PORTAIS_CORPORATIVOS


def _carregar_portais_descobertos() -> None:
    """
    Carrega portais corporativos descobertos automaticamente pelo módulo
    autodescoberta_fontes.py e os adiciona à lista PORTAIS_CORPORATIVOS.
    """
    global PORTAIS_CORPORATIVOS
    try:
        from autodescoberta_fontes import get_empresas_ativas
        empresas_descobertas = get_empresas_ativas()
        empresas_existentes = {p["empresa"].lower() for p in PORTAIS_CORPORATIVOS}
        adicionadas = 0
        for emp in empresas_descobertas:
            if emp["empresa"].lower() not in empresas_existentes and emp.get("urls"):
                PORTAIS_CORPORATIVOS.append(emp)
                empresas_existentes.add(emp["empresa"].lower())
                adicionadas += 1
        if adicionadas > 0:
            logger.info(f"Autodescoberta: {adicionadas} empresa(s) adicionada(s) dinamicamente")
    except ImportError:
        pass  # Módulo de autodescoberta não disponível
    except Exception as e:
        logger.debug(f"Autodescoberta: {e}")


def _buscar_portal_corporativo(portal: Dict, session: requests.Session) -> List[Dict]:
    vagas = []
    empresa = portal["empresa"]

    for url in portal["urls"]:
        html = _get_html(url, session)
        if not html:
            time.sleep(SLEEP_BETWEEN * 0.5)
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Estratégia 1: links com "regulatory" no texto
        for link_el in soup.find_all("a", href=True):
            txt = link_el.get_text(strip=True)
            if re.search(r"regulat|registro|Regulat|regulatory", txt, re.I) and len(txt) > 5:
                href = link_el.get("href", "")
                link = href if href.startswith("http") else f"{_base_url(url)}{href}"
                vagas.append(_make_vaga(txt, empresa, "", link,
                                        f"Portal Corporativo ({empresa})"))

        # Estratégia 2: seletores genéricos de cards de vagas
        for seletor in [
            "li.search-results-list-item",
            "div.job-card",
            "article.job",
            "div.job-listing",
            "li.job-item",
            "div[class*='job']",
            "div[class*='vacancy']",
            "div[class*='position']",
            "li[class*='job']",
        ]:
            cards = soup.select(seletor)
            if not cards:
                continue
            for card in cards:
                try:
                    titulo_el = card.find(["h2", "h3", "h4", "a"])
                    titulo = titulo_el.get_text(strip=True) if titulo_el else ""
                    if not titulo or len(titulo) < 5:
                        continue
                    loc_el = card.find(["span", "div"],
                                        class_=re.compile(r"location|city|local", re.I))
                    localizacao = loc_el.get_text(strip=True) if loc_el else ""
                    link_el = card.find("a", href=True)
                    link = ""
                    if link_el:
                        href = link_el.get("href", "")
                        link = href if href.startswith("http") else f"{_base_url(url)}{href}"
                    vagas.append(_make_vaga(titulo, empresa, localizacao, link or url,
                                            f"Portal Corporativo ({empresa})"))
                except Exception as exc:
                    logger.debug(f"{empresa} card: {exc}")
            break

        time.sleep(SLEEP_BETWEEN * 0.5)

    logger.debug(f"{empresa}: {len(vagas)} vagas")
    return vagas


# ─────────────────────────────────────────────────────────────────────────────
# Enriquecimento de detalhes
# ─────────────────────────────────────────────────────────────────────────────

def _enriquecer_vaga(vaga: Dict, session: requests.Session) -> Dict:
    """Acessa a página individual da vaga para extrair detalhes completos."""
    link = vaga.get("link", "")
    if not link or "linkedin.com/jobs/search" in link or not link.startswith("http"):
        return vaga

    html = _get_html(link, session)
    if not html:
        return vaga

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Descrição
    descricao = vaga.get("descricao", "")
    if not descricao or len(descricao) < 100:
        for seletor in [
            "div.description", "div.job-description", "div.jobDescriptionContent",
            "section.description", "div[data-testid='job-description']",
            "div.show-more-less-html__markup", "div#job-details",
            "div.vacancy-description", "div.job-details",
            "div.content", "main article", "main",
        ]:
            el = soup.select_one(seletor)
            if el:
                txt = el.get_text(separator="\n", strip=True)
                if len(txt) > 100:
                    descricao = txt
                    break
        if descricao:
            vaga["descricao"] = descricao[:3000]

    texto = soup.get_text()
    texto_lower = texto.lower()

    # Salário
    if not vaga.get("salario"):
        sal_match = re.search(
            r"(R\$\s*[\d.,]+(?:\s*[-–]\s*R\$\s*[\d.,]+)?|\$\s*[\d.,]+(?:\s*[-–]\s*\$\s*[\d.,]+)?)",
            texto, re.IGNORECASE
        )
        if sal_match:
            vaga["salario"] = sal_match.group(0).strip()

    # Tipo de contrato
    if not vaga.get("tipo_contrato"):
        if "clt" in texto_lower:
            vaga["tipo_contrato"] = "CLT"
        elif "pessoa jurídica" in texto_lower or " pj " in texto_lower:
            vaga["tipo_contrato"] = "PJ"
        elif "full-time" in texto_lower or "tempo integral" in texto_lower:
            vaga["tipo_contrato"] = "Tempo integral"

    # Modalidade
    if not vaga.get("modalidade_trabalho"):
        if "100% remoto" in texto_lower or "fully remote" in texto_lower:
            vaga["modalidade_trabalho"] = "Remoto"
        elif "híbrido" in texto_lower or "hybrid" in texto_lower:
            vaga["modalidade_trabalho"] = "Híbrido"
        elif "presencial" in texto_lower or "on-site" in texto_lower:
            vaga["modalidade_trabalho"] = "Presencial"
        elif "remoto" in texto_lower or "remote" in texto_lower or "home office" in texto_lower:
            vaga["modalidade_trabalho"] = "Remoto"

    # Data de publicação
    if not vaga.get("data_publicacao"):
        data_el = soup.find("time")
        if data_el:
            vaga["data_publicacao"] = _normalizar_data(
                data_el.get("datetime", data_el.get_text(strip=True))
            )

    return vaga


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI Web Search
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_via_openai() -> List[Dict]:
    """
    Usa o OpenAI Web Search para buscar vagas regulatórias agro.
    Acessa LinkedIn autenticado, portais corporativos e outras fontes
    que bloqueiam scraping direto.
    """
    try:
        from openai import OpenAI
        client = OpenAI()
    except ImportError:
        logger.warning("OpenAI não disponível")
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY não configurada")
        return []

    hoje = date.today().strftime("%d/%m/%Y")
    prompt = f"""Hoje é {hoje}. Busque vagas de emprego ABERTAS publicadas nos últimos 7 dias para o seguinte perfil:

PERFIL DO CANDIDATO:
Executivo sênior LATAM com +20 anos em Regulatory Affairs em multinacionais (Syngenta, Bayer, ENVU).
Fluente em português, inglês e espanhol. Disponível para relocação internacional.
Médico Veterinário com pós em Crop Protection, Toxicologia e Regulatory Science.

CARGOS-ALVO (apenas níveis gerenciais/diretivos):
- Gerente / Diretor / Head / VP de Assuntos Regulatórios
- Gerente / Diretor de Registro de Agrotóxicos
- Regulatory Affairs Manager / Director / Head / VP
- Senior Manager Regulatory Affairs
- LATAM Regulatory Affairs Manager / Director / Lead
- General Manager Regulatory Affairs
- Chief Regulatory Officer
- Executive Regulatory Affairs Manager
NAO incluir: Analista, Coordenador, Assistente, Estágio

SETORES-ALVO:
- Agrotóxicos / Defensivos Agrícolas / Crop Protection / Agrochemicals
- Fertilizantes / Plant Nutrition
- Bioinsumos / Biologicals / Biostimulants
- Controle de Pragas e Vetores / Pest Control / Environmental Science
- Sanitizantes / Sanitizers
- Agronegócio / Agribusiness

COMBINAÇÃO ESPECIAL: qualquer cargo de Assuntos Regulatórios + Medicina Veterinária

ABRANGÊNCIA GEOGRÁFICA:
1. Brasil (prioridade)
2. LATAM / América Latina (vagas regionais)
3. Global / Internacional (vagas com possibilidade de relocação)

FONTES PARA BUSCAR (acesse cada uma):
- LinkedIn Jobs Brasil: https://www.linkedin.com/jobs/search?keywords=gerente+assuntos+regulatorios+agrotoxicos&location=Brasil
- LinkedIn LATAM: https://www.linkedin.com/jobs/search?keywords=LATAM+regulatory+affairs+manager+agrochemical
- LinkedIn Global: https://www.linkedin.com/jobs/search?keywords=director+regulatory+affairs+crop+protection
- Syngenta Careers: https://www.syngenta.com/en/careers/job-search?query=regulatory
- Corteva Careers: https://jobs.corteva.com/search-jobs/regulatory
- Bayer Careers: https://career.bayer.com/en/jobs?search=regulatory+affairs
- BASF Careers: https://www.basf.com/global/en/careers/jobs.html?q=regulatory
- UPL Careers: https://www.upl-ltd.com/careers
- FMC Careers: https://jobs.fmc.com/search/?q=regulatory
- Adama Careers: https://www.adama.com/global/en/careers.html
- Nufarm Careers: https://www.nufarm.com/global/careers/
- ENVU Careers: https://www.envu.com/careers
- Ourofino Agro: https://www.ourofinoagro.com.br/trabalhe-conosco
- Vagas.com: https://www.vagas.com.br/vagas-de-gerente-regulatorio
- Indeed Brasil: https://br.indeed.com/jobs?q=gerente+assuntos+regulatorios
- Agrobase: https://www.agrobase.com.br/oportunidades/

Para CADA vaga encontrada, retorne um JSON com:
{{
  "titulo": "título exato do cargo",
  "empresa": "nome da empresa",
  "localizacao": "cidade, estado, país",
  "link": "URL direto para candidatura",
  "data_publicacao": "data ou 'há X dias'",
  "descricao": "descrição resumida (2-3 frases)",
  "salario": "faixa salarial se disponível ou null",
  "tipo_contrato": "CLT/PJ/Full-time/Contract etc",
  "fonte": "nome da plataforma onde encontrou",
  "internacional": true/false
}}

Retorne APENAS vagas reais e verificadas. Se não encontrar vagas, retorne uma lista vazia [].
Formato de saída: JSON array com todas as vagas encontradas."""

    try:
        response = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview", "search_context_size": "high"}],
            input=prompt,
        )
        texto = response.output_text.strip()
        logger.info(f"OpenAI Web Search: resposta recebida ({len(texto)} chars)")

        # Extrair JSON da resposta — suporta múltiplos formatos:
        # 1. Bloco markdown ```json [...] ```
        # 2. Array JSON direto [...]
        # 3. JSON embutido em texto livre (extrai o maior array encontrado)
        import re as _re
        vagas_raw = None

        # Tentativa 1: bloco markdown ```json
        md_match = _re.search(r"```(?:json)?\s*(\[.*?\])\s*```", texto, _re.DOTALL)
        if md_match:
            try:
                vagas_raw = json.loads(md_match.group(1))
            except json.JSONDecodeError:
                pass

        # Tentativa 2: encontrar todos os arrays JSON no texto e pegar o maior
        if vagas_raw is None:
            arrays = _re.findall(r"(\[\s*\{.*?\}\s*\])", texto, _re.DOTALL)
            for arr_str in sorted(arrays, key=len, reverse=True):
                try:
                    vagas_raw = json.loads(arr_str)
                    break
                except json.JSONDecodeError:
                    continue

        # Tentativa 3: array JSON simples (pode ser [])
        if vagas_raw is None:
            json_match = _re.search(r"\[.*\]", texto, _re.DOTALL)
            if json_match:
                try:
                    vagas_raw = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

        # Tentativa 4: texto inteiro como JSON
        if vagas_raw is None:
            try:
                vagas_raw = json.loads(texto)
            except json.JSONDecodeError:
                pass

        if vagas_raw is None:
            logger.warning("OpenAI retornou texto livre (sem JSON) — sem vagas estruturadas")
            return []

        vagas = []
        for v in vagas_raw:
            if not isinstance(v, dict):
                continue
            titulo = v.get("titulo", "").strip()
            if not titulo or len(titulo) < 5:
                continue
            vaga = _make_vaga(
                titulo=titulo,
                empresa=v.get("empresa", ""),
                localizacao=v.get("localizacao", ""),
                link=v.get("link", ""),
                descricao=v.get("descricao", ""),
                salario=str(v.get("salario", "") or ""),
                tipo_contrato=v.get("tipo_contrato", ""),
                data_pub=v.get("data_publicacao", ""),
                fonte=f"OpenAI/{v.get('fonte', 'Web Search')}",
            )
            vagas.append(vaga)

        logger.info(f"OpenAI Web Search: {len(vagas)} vagas extraídas")
        return vagas

    except Exception as e:
        logger.error(f"OpenAI Web Search erro: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Função principal
# ─────────────────────────────────────────────────────────────────────────────

def buscar_vagas(
    enriquecer_detalhes: bool = True,
    max_enriquecimento: int = 50,
) -> Tuple[List[Dict], List[Dict], List[str]]:
    """
    Busca vagas em todas as fontes, filtra as relevantes e enriquece detalhes.

    Returns:
        (nacionais, internacionais, erros)
    """
    # Carregar portais descobertos automaticamente
    _carregar_portais_descobertos()

    session = requests.Session()
    session.headers.update(HEADERS)

    todas_vagas: List[Dict] = []
    erros: List[str] = []

    # ── OpenAI Web Search (fonte primária — acessa LinkedIn autenticado, portais corporativos)
    try:
        vagas_openai = _buscar_via_openai()
        todas_vagas.extend(vagas_openai)
        logger.info(f"OpenAI Web Search: {len(vagas_openai)} vagas")
    except Exception as e:
        erros.append(f"OpenAI: {e}")
        logger.error(f"OpenAI: {e}")

    # ── SerpAPI Google Jobs (fallback quando LinkedIn bloqueia IPs de datacenter)
    serpapi_key = os.getenv("SERPAPI_KEY", "")
    if serpapi_key:
        try:
            vagas_serp = _buscar_serpapi_google_jobs(serpapi_key)
            todas_vagas.extend(vagas_serp)
            logger.info(f"SerpAPI Google Jobs: {len(vagas_serp)} vagas")
        except Exception as e:
            erros.append(f"SerpAPI: {e}")
            logger.warning(f"SerpAPI: {e}")
    else:
        logger.debug("SERPAPI_KEY não configurada — pulando Google Jobs")

    # ── LinkedIn (jobs-guest público — pode ser bloqueado em IPs de datacenter)
    try:
        vagas_li = _buscar_linkedin(session)
        if not vagas_li:
            logger.warning("LinkedIn jobs-guest: retornou 0 vagas — provável bloqueio de IP de datacenter (GitHub Actions/AWS). Configure SERPAPI_KEY como fallback.")
        todas_vagas.extend(vagas_li)
    except Exception as e:
        erros.append(f"LinkedIn: {e}")
        logger.error(f"LinkedIn: {e}")

    # ── Vagas.com
    try:
        todas_vagas.extend(_buscar_vagascom(session))
    except Exception as e:
        erros.append(f"Vagas.com: {e}")
        logger.error(f"Vagas.com: {e}")

    # ── Agro2Business
    try:
        todas_vagas.extend(_buscar_agro2business(session))
    except Exception as e:
        erros.append(f"Agro2Business: {e}")
        logger.error(f"Agro2Business: {e}")

    # ── Agrobase
    try:
        todas_vagas.extend(_buscar_agrobase(session))
    except Exception as e:
        erros.append(f"Agrobase: {e}")
        logger.error(f"Agrobase: {e}")

    # ── AgCareers
    try:
        todas_vagas.extend(_buscar_agcareers(session))
    except Exception as e:
        erros.append(f"AgCareers: {e}")
        logger.error(f"AgCareers: {e}")

    # ── Gupy (Playwright) — desabilitado por padrão (causa timeout)
    # Para habilitar: descomentar as linhas abaixo
    # try:
    #     todas_vagas.extend(_buscar_gupy_playwright())
    # except Exception as e:
    #     erros.append(f"Gupy: {e}")
    #     logger.error(f"Gupy: {e}")

    # ── Gupy subdomains (via __NEXT_DATA__ SSR — não requer Playwright)
    try:
        todas_vagas.extend(_buscar_gupy_subdomains(session))
    except Exception as e:
        erros.append(f"Gupy subdomains: {e}")
        logger.error(f"Gupy subdomains: {e}")

    # ── Portais corporativos
    for portal in PORTAIS_CORPORATIVOS:
        try:
            todas_vagas.extend(_buscar_portal_corporativo(portal, session))
        except Exception as e:
            erros.append(f"Portal {portal['empresa']}: {e}")
        time.sleep(SLEEP_BETWEEN * 0.3)

    logger.info(f"Total bruto: {len(todas_vagas)} vagas")

    # ── Deduplicação
    seen_ids: set = set()
    vagas_unicas: List[Dict] = []
    for v in todas_vagas:
        vid = v.get("id") or _gerar_id(v)
        if vid not in seen_ids:
            seen_ids.add(vid)
            v["id"] = vid
            vagas_unicas.append(v)

    logger.info(f"Após deduplicação: {len(vagas_unicas)} vagas")

    # ── Enriquecimento PRÉ-FILTRO: enriquecer apenas vagas com cargo regulatório
    # Isso permite filtrar pelo setor na descrição completa, não apenas no título
    if enriquecer_detalhes:
        # Primeiro: vagas já relevantes (cargo + setor identificados no título)
        ja_relevantes = [
            (i, v) for i, v in enumerate(vagas_unicas)
            if _eh_vaga_relevante(v)
        ]
        # Segundo: vagas com cargo regulatório mas setor ainda não identificado
        candidatas_enriquecimento = [
            (i, v) for i, v in enumerate(vagas_unicas)
            if _eh_cargo_alvo(v.get("titulo", ""), v.get("descricao", ""))
            and not _eh_setor_alvo(v.get("titulo", ""), v.get("descricao", ""), v.get("empresa", ""))
        ]
        # Terceiro: vagas executivas de alto nível em setor agro (sem 'regulatory' no título)
        # Ex: Director Biologicals Americas (Yara) — enriquecer para verificar se é regulatory
        CARGOS_EXEC = ["director", "diretor", "diretora", "head", "vice-presidente", "vp", "chief", "general manager"]
        candidatas_executivas = [
            (i, v) for i, v in enumerate(vagas_unicas)
            if any(c in _normalizar(v.get("titulo", "")) for c in CARGOS_EXEC)
            and _eh_setor_alvo(v.get("titulo", ""), v.get("descricao", ""), v.get("empresa", ""))
            and not _eh_cargo_alvo(v.get("titulo", ""), v.get("descricao", ""))  # ainda não tem regulatory
        ]
        # Combinar: primeiro as já relevantes, depois as candidatas
        a_enriquecer = ja_relevantes + candidatas_enriquecimento + candidatas_executivas
        enriquecidas = 0
        for i, vaga in a_enriquecer:
            if enriquecidas >= max_enriquecimento:
                break
            try:
                vagas_unicas[i] = _enriquecer_vaga(vaga, session)
                enriquecidas += 1
                time.sleep(SLEEP_BETWEEN * 0.3)
            except Exception as e:
                logger.debug(f"Enriquecimento {vaga.get('link', '')[:60]}: {e}")
        logger.info(f"Vagas enriquecidas: {enriquecidas} (de {len(a_enriquecer)} candidatas)")

    # ── Filtrar relevantes (após enriquecimento, setor pode aparecer na descrição)
    vagas_relevantes = [v for v in vagas_unicas if _eh_vaga_relevante(v)]
    logger.info(f"Vagas relevantes: {len(vagas_relevantes)}")

    # ── Separar nacionais e internacionais
    nacionais = []
    internacionais = []
    for vaga in vagas_relevantes:
        if _eh_internacional(vaga):
            vaga = _investigar_vaga_internacional(vaga)
            internacionais.append(vaga)
        else:
            nacionais.append(vaga)

    logger.info(f"Nacionais: {len(nacionais)} | Internacionais: {len(internacionais)}")
    return nacionais, internacionais, erros


# ─────────────────────────────────────────────────────────────────────────────
# Deduplicação histórica
# ─────────────────────────────────────────────────────────────────────────────

def filtrar_novas_vagas(
    nacionais: List[Dict],
    internacionais: List[Dict],
    seen: Dict,
) -> Tuple[List[Dict], List[Dict], Dict]:
    """Filtra apenas vagas que ainda não foram alertadas."""
    novas_nacionais = []
    novas_internacionais = []
    seen_atualizado = dict(seen)

    for vaga in nacionais:
        vid = vaga["id"]
        if vid not in seen_atualizado:
            novas_nacionais.append(vaga)
            seen_atualizado[vid] = {
                "titulo": vaga.get("titulo", ""),
                "empresa": vaga.get("empresa", ""),
                "data_alerta": datetime.now(timezone.utc).isoformat(),
            }

    for vaga in internacionais:
        vid = vaga["id"]
        if vid not in seen_atualizado:
            novas_internacionais.append(vaga)
            seen_atualizado[vid] = {
                "titulo": vaga.get("titulo", ""),
                "empresa": vaga.get("empresa", ""),
                "data_alerta": datetime.now(timezone.utc).isoformat(),
            }

    return novas_nacionais, novas_internacionais, seen_atualizado


# ─────────────────────────────────────────────────────────────────────────────
# Formatação do email
# ─────────────────────────────────────────────────────────────────────────────

def _formatar_vaga_email(vaga: Dict, numero: int, internacional: bool = False) -> str:
    linhas = []
    linhas.append("─" * 70)
    linhas.append(f"VAGA {numero}: {vaga.get('titulo', 'Sem título').upper()}")
    linhas.append("─" * 70)

    if vaga.get("empresa"):
        linhas.append(f"Empresa:          {vaga['empresa']}")
    if vaga.get("localizacao"):
        linhas.append(f"Localização:      {vaga['localizacao']}")
    if vaga.get("modalidade_trabalho"):
        linhas.append(f"Modalidade:       {vaga['modalidade_trabalho']}")
    if vaga.get("tipo_contrato"):
        linhas.append(f"Tipo de contrato: {vaga['tipo_contrato']}")
    if vaga.get("salario"):
        linhas.append(f"Remuneração:      {vaga['salario']}")
    if vaga.get("data_publicacao"):
        linhas.append(f"Publicada em:     {vaga['data_publicacao']}")
    if vaga.get("fonte"):
        linhas.append(f"Fonte:            {vaga['fonte']}")

    if internacional:
        linhas.append("")
        linhas.append(">> INFORMAÇÕES PARA CANDIDATOS BRASILEIROS:")
        aceita = vaga.get("aceita_sem_visto")
        if aceita is True:
            linhas.append("   Patrocínio de visto: SIM (mencionado na descrição da vaga)")
        elif aceita is False:
            linhas.append("   Patrocínio de visto: NÃO (exige autorização prévia de trabalho no país)")
        else:
            linhas.append("   Patrocínio de visto: Não informado — verificar diretamente com o empregador")

        remoto = vaga.get("modalidade_trabalho")
        if remoto == "Remoto":
            linhas.append("   Trabalho remoto do Brasil: POSSIVELMENTE SIM (vaga anunciada como remota)")
        elif remoto == "Híbrido":
            linhas.append("   Trabalho remoto do Brasil: PARCIAL (modelo híbrido — verificar com o empregador)")
        elif remoto == "Presencial":
            linhas.append("   Trabalho remoto do Brasil: NÃO (presencial no país de destino)")
        else:
            linhas.append("   Trabalho remoto do Brasil: Não informado — verificar com o empregador")

    if vaga.get("descricao"):
        linhas.append("")
        linhas.append("DESCRIÇÃO DA VAGA:")
        desc = vaga["descricao"]
        if len(desc) > 1500:
            desc = desc[:1500] + "\n[...] (descrição completa disponível no link abaixo)"
        linhas.append(desc)

    linhas.append("")
    if vaga.get("link"):
        linhas.append(f"LINK PARA CANDIDATURA: {vaga['link']}")
    else:
        linhas.append("LINK PARA CANDIDATURA: Não disponível")

    return "\n".join(linhas)


def formatar_email_vagas(
    nacionais: List[Dict],
    internacionais: List[Dict],
    erros: List[str],
) -> str:
    """
    Gera o corpo HTML do email usando o template premium.
    Retorna string HTML pronta para envio via Gmail MCP.
    """
    try:
        from template_email_vagas import formatar_email_html
        return formatar_email_html(nacionais, internacionais, erros)
    except ImportError:
        # Fallback para texto simples caso o template não esteja disponível
        logger.warning("template_email_vagas não encontrado — usando formato texto simples")
        return _formatar_email_texto(nacionais, internacionais, erros)


def _formatar_email_texto(
    nacionais: List[Dict],
    internacionais: List[Dict],
    erros: List[str],
) -> str:
    """Fallback: formato texto simples (usado se o template HTML não estiver disponível)."""
    hoje = date.today().strftime("%d/%m/%Y")
    linhas = []

    linhas.append("=" * 70)
    linhas.append("ALERTA DE VAGAS — REGULATÓRIO AGRO")
    linhas.append("Gerente / Diretor de Assuntos Regulatórios")
    linhas.append("Agrotóxicos | Fertilizantes | Bioinsumos | Defensivos Agrícolas")
    linhas.append(f"Data: {hoje}")
    linhas.append("=" * 70)
    linhas.append("")

    total = len(nacionais) + len(internacionais)
    if total == 0:
        linhas.append("Nenhuma vaga nova encontrada hoje nas fontes monitoradas.")
        linhas.append("")
        linhas.append("O sistema de monitoramento funcionou normalmente.")
        linhas.append("Vagas novas serão alertadas assim que surgirem.")
    else:
        linhas.append(f"Total de vagas novas encontradas: {total}")
        linhas.append(f"  Nacionais:       {len(nacionais)}")
        linhas.append(f"  Internacionais:  {len(internacionais)}")
        linhas.append("")

        if nacionais:
            linhas.append("=" * 70)
            linhas.append(f"VAGAS NACIONAIS ({len(nacionais)} encontradas)")
            linhas.append("=" * 70)
            for i, vaga in enumerate(nacionais, 1):
                linhas.append(_formatar_vaga_email(vaga, i, internacional=False))
                linhas.append("")

        if internacionais:
            linhas.append("=" * 70)
            linhas.append(f"VAGAS INTERNACIONAIS ({len(internacionais)} encontradas)")
            linhas.append("=" * 70)
            for i, vaga in enumerate(internacionais, 1):
                linhas.append(_formatar_vaga_email(vaga, i, internacional=True))
                linhas.append("")

    if erros:
        linhas.append(f"Fontes com falha ({len(erros)}):")
        for e in erros[:10]:
            linhas.append(f"  - {e}")

    linhas.append("=" * 70)
    linhas.append("HB Advisory · Intellicore — Envio diário 08:00")
    linhas.append("=" * 70)

    return "\n".join(linhas)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="vagas_regulatorio.json")
    parser.add_argument("--no-enrich", action="store_true")
    args = parser.parse_args()

    nacionais, internacionais, erros = buscar_vagas(
        enriquecer_detalhes=not args.no_enrich,
        max_enriquecimento=50,
    )
    resultado = {
        "data_coleta": datetime.now(timezone.utc).isoformat(),
        "total_nacionais": len(nacionais),
        "total_internacionais": len(internacionais),
        "nacionais": nacionais,
        "internacionais": internacionais,
        "erros": erros,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(formatar_email_vagas(nacionais, internacionais, erros))
    print(f"\nResultado salvo em: {args.output}")
