#!/usr/bin/env python3
"""
Alerta Diário de Vagas Regulatórias — Agrotóxicos, Fertilizantes e Bioinsumos
===============================================================================

Executa o monitor_vagas_regulatorio.py, filtra apenas vagas NOVAS
(não alertadas antes) e envia email detalhado via Mailgun (server-side).

Critérios de alerta:
  - Cargo gerencial/diretivo em Assuntos Regulatórios no setor agro
  - Ou combinação Assuntos Regulatórios + formação em Medicina Veterinária
  - Vagas nacionais e internacionais separadas
  - Para internacionais: informa sobre visto e trabalho remoto do Brasil

Destinatário: huddsong@gmail.com
Horário: 08:00 Brasília (11:00 UTC) — agendado via pg_cron Supabase

Uso:
    python3 alerta_vagas_regulatorio.py [--force-send] [--no-enrich] [--test]

Variáveis de ambiente (obrigatórias para envio via Mailgun):
    MAILGUN_API_KEY   — chave da API do Mailgun
    MAILGUN_DOMAIN    — domínio verificado (ex: hb-advisory.com.br)
    FROM_EMAIL        — remetente (ex: Intellicore Vagas <noreply@hb-advisory.com.br>)
    MONITOR_RECIPIENT — destinatário (padrão: huddsong@gmail.com)

Variáveis opcionais (fallback SMTP):
    GMAIL_SMTP_USER     — conta Gmail
    GMAIL_APP_PASSWORD  — App Password de 16 caracteres
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("alerta_vagas_regulatorio")

# ─────────────────────────────────────────────────────────────────────────────
# Configurações
# ─────────────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "data")

RECIPIENT = os.getenv("MONITOR_RECIPIENT", "huddsong@gmail.com")
SEEN_PATH = os.path.join(_DATA_DIR, "vagas_regulatorio_seen.json")
LOG_PATH = os.path.join(_DATA_DIR, "vagas_regulatorio_log.json")

# Mailgun (sistema principal — server-side, sem dependências locais)
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "").strip()
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN", "hb-advisory.com.br").strip()
MAILGUN_BASE_URL = os.getenv("MAILGUN_BASE_URL", "https://api.mailgun.net").rstrip("/")
if not MAILGUN_BASE_URL.endswith("/v3"):
    MAILGUN_BASE_URL = MAILGUN_BASE_URL + "/v3"
FROM_EMAIL = os.getenv("FROM_EMAIL", "Intellicore Vagas <noreply@hb-advisory.com.br>")

# Adicionar diretório ao path para importar o monitor
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Histórico de vagas já alertadas
# ─────────────────────────────────────────────────────────────────────────────

def load_seen(path: str) -> Dict:
    """Carrega o histórico de vagas já alertadas."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar histórico: {e}. Iniciando vazio.")
    return {}


def save_seen(seen: Dict, path: str) -> None:
    """Salva o histórico atualizado de vagas alertadas."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def registrar_log(
    data: str,
    total_nacionais: int,
    total_internacionais: int,
    email_enviado: bool,
    erros: List[str],
    path: str
) -> None:
    """Registra log de execução."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    log = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            pass

    log.append({
        "data": data,
        "total_nacionais": total_nacionais,
        "total_internacionais": total_internacionais,
        "email_enviado": email_enviado,
        "erros": erros[:5],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Manter apenas os últimos 90 registros
    log = log[-90:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Envio de email HTML via Mailgun (sistema principal — server-side)
# ─────────────────────────────────────────────────────────────────────────────

def _send_via_mailgun(subject: str, html_body: str, recipient: str) -> bool:
    """Envia email HTML via API do Mailgun. Não requer dependências locais."""
    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
        logger.warning("Mailgun não configurado (MAILGUN_API_KEY ou MAILGUN_DOMAIN ausentes).")
        return False
    try:
        import requests as req
        url = f"{MAILGUN_BASE_URL}/{MAILGUN_DOMAIN}/messages"
        data = {
            "from": FROM_EMAIL,
            "to": [recipient],
            "subject": subject,
            "html": html_body,
            "text": " ",
        }
        resp = req.post(url, auth=("api", MAILGUN_API_KEY), data=data, timeout=30)
        if resp.status_code == 200:
            logger.info(f"Email enviado via Mailgun para {recipient} (id={resp.json().get('id','?')})")
            return True
        else:
            logger.error(f"Mailgun retornou {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as exc:
        logger.error(f"Erro ao enviar via Mailgun: {exc}")
        return False


def _send_via_smtp(subject: str, html_body: str, recipient: str) -> bool:
    """Fallback: envia email HTML via SMTP do Gmail (requer App Password local)."""
    try:
        from enviar_email_html import enviar_email_html
        ok = enviar_email_html(to=recipient, subject=subject, html_body=html_body)
        if ok:
            logger.info(f"Email enviado via SMTP para {recipient}")
        else:
            logger.error("Falha no envio via SMTP — verifique as credenciais.")
        return ok
    except Exception as exc:
        logger.error(f"Erro ao enviar via SMTP: {exc}")
        return False


def send_email(subject: str, body: str, recipient: str) -> bool:
    """
    Envia email HTML. Tenta Mailgun primeiro (server-side).
    Se não configurado, usa SMTP como fallback.
    """
    # Tentativa 1: Mailgun (preferencial — funciona em qualquer servidor)
    if MAILGUN_API_KEY and MAILGUN_DOMAIN:
        ok = _send_via_mailgun(subject, body, recipient)
        if ok:
            return True
        logger.warning("Mailgun falhou. Tentando fallback via SMTP...")

    # Tentativa 2: SMTP Gmail (fallback para execução local/GitHub Actions)
    return _send_via_smtp(subject, body, recipient)


# ─────────────────────────────────────────────────────────────────────────────
# Principal
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    import warnings
    warnings.filterwarnings("ignore")

    force_send = "--force-send" in sys.argv
    no_enrich = "--no-enrich" in sys.argv
    test_mode = "--test" in sys.argv

    today = date.today()
    logger.info(f"Alerta de Vagas Regulatórias — {today.isoformat()}")
    logger.info(f"Sistema de envio: {'Mailgun' if MAILGUN_API_KEY else 'SMTP (fallback)'}")

    # Importar módulo de monitoramento
    try:
        from monitor_vagas_regulatorio import (
            buscar_vagas,
            filtrar_novas_vagas,
            formatar_email_vagas,
        )
    except ImportError as e:
        logger.error(f"Erro ao importar monitor_vagas_regulatorio: {e}")
        return 1

    # Buscar vagas
    logger.info("Iniciando busca de vagas em todas as fontes...")
    try:
        nacionais, internacionais, erros = buscar_vagas(
            enriquecer_detalhes=not no_enrich,
            max_enriquecimento=60,
        )
    except Exception as e:
        logger.error(f"Erro na busca de vagas: {e}")
        return 1

    logger.info(
        f"Vagas encontradas: {len(nacionais)} nacionais, "
        f"{len(internacionais)} internacionais"
    )

    # Carregar histórico e filtrar novas
    seen = load_seen(SEEN_PATH)
    logger.info(f"Histórico: {len(seen)} vagas já alertadas anteriormente")

    novas_nacionais, novas_internacionais, seen_atualizado = filtrar_novas_vagas(
        nacionais, internacionais, seen
    )
    total_novas = len(novas_nacionais) + len(novas_internacionais)
    logger.info(
        f"Vagas NOVAS (não alertadas antes): {total_novas} "
        f"({len(novas_nacionais)} nacionais, {len(novas_internacionais)} internacionais)"
    )

    # Gerar corpo do email
    corpo = formatar_email_vagas(novas_nacionais, novas_internacionais, erros)

    if test_mode:
        print("\n" + "=" * 70)
        print("MODO TESTE — Email NÃO enviado, histórico NÃO atualizado")
        print("=" * 70)
        print(corpo)
        return 0

    # Salvar histórico atualizado (somente em execução real, não em modo teste)
    save_seen(seen_atualizado, SEEN_PATH)

    # Definir assunto
    hoje_fmt = today.strftime("%d/%m/%Y")
    if total_novas > 0:
        assunto = (
            f"[Empregos] Vagas Regulatório Agro — {total_novas} nova(s) vaga(s) — {hoje_fmt}"
        )
    else:
        assunto = f"[Empregos] Vagas Regulatório Agro — Nenhuma vaga nova — {hoje_fmt}"

    # Enviar email sempre (com ou sem vagas novas)
    # Isso garante que o usuário saiba que o sistema está funcionando
    email_enviado = send_email(assunto, corpo, RECIPIENT)
    if not email_enviado:
        logger.error("Falha no envio do email por todos os métodos disponíveis")

    # Registrar log
    registrar_log(
        data=today.isoformat(),
        total_nacionais=len(novas_nacionais),
        total_internacionais=len(novas_internacionais),
        email_enviado=email_enviado,
        erros=erros,
        path=LOG_PATH,
    )

    return 0 if (total_novas == 0 or email_enviado) else 1


if __name__ == "__main__":
    sys.exit(main())
