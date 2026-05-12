#!/usr/bin/env python3
"""
Gerador de Email — Alerta de Vagas Regulatórias Agro
=====================================================

Executa a busca de vagas, filtra as novas e salva o conteúdo do email
em /tmp/vagas_email_payload.json para ser enviado pelo Manus via MCP.

Retorna exit code:
  0 — email gerado com sucesso (enviar)
  2 — sem vagas novas (enviar mesmo assim — email de status)
  1 — erro crítico

Uso:
    python3 gerar_email_vagas.py [--no-enrich]
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
logger = logging.getLogger("gerar_email_vagas")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_SCRIPT_DIR, "data")

RECIPIENT = os.getenv("MONITOR_RECIPIENT", "huddsonviana@gmail.com")
SEEN_PATH = os.path.join(_DATA_DIR, "vagas_regulatorio_seen.json")
LOG_PATH  = os.path.join(_DATA_DIR, "vagas_regulatorio_log.json")
OUTPUT_PATH = "/tmp/vagas_email_payload.json"
HTML_OUTPUT_PATH = "/tmp/vagas_email_body.html"

if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


def load_seen(path: str) -> Dict:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_seen(seen: Dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def registrar_log(data, total_nac, total_int, email_enviado, erros, path):
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
        "total_nacionais": total_nac,
        "total_internacionais": total_int,
        "email_enviado": email_enviado,
        "erros": erros[:5],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    log = log[-90:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def main() -> int:
    import warnings
    warnings.filterwarnings("ignore")

    no_enrich = "--no-enrich" in sys.argv
    today = date.today()
    logger.info(f"Gerando email de vagas regulatórias — {today.isoformat()}")

    try:
        from monitor_vagas_regulatorio import (
            buscar_vagas,
            filtrar_novas_vagas,
            formatar_email_vagas,
        )
    except ImportError as e:
        logger.error(f"Erro ao importar monitor: {e}")
        return 1

    # Buscar vagas
    logger.info("Buscando vagas em todas as fontes...")
    try:
        nacionais, internacionais, erros = buscar_vagas(
            enriquecer_detalhes=not no_enrich,
            max_enriquecimento=60,
        )
    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        return 1

    logger.info(f"Encontradas: {len(nacionais)} nacionais, {len(internacionais)} internacionais")

    # Filtrar novas
    seen = load_seen(SEEN_PATH)
    logger.info(f"Histórico: {len(seen)} vagas já alertadas")

    novas_nac, novas_int, seen_novo = filtrar_novas_vagas(nacionais, internacionais, seen)
    total_novas = len(novas_nac) + len(novas_int)
    logger.info(f"Vagas NOVAS: {total_novas} ({len(novas_nac)} nac, {len(novas_int)} int)")

    # Salvar histórico
    save_seen(seen_novo, SEEN_PATH)

    # Gerar corpo do email
    corpo = formatar_email_vagas(novas_nac, novas_int, erros)

    # Definir assunto
    hoje_fmt = today.strftime("%d/%m/%Y")
    if total_novas > 0:
        assunto = f"[Vagas Regulatório Agro] {total_novas} nova(s) vaga(s) — {hoje_fmt}"
    else:
        assunto = f"[Vagas Regulatório Agro] Nenhuma vaga nova — {hoje_fmt}"

    # Salvar HTML separado para envio direto via Gmail API
    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(corpo)
    logger.info(f"HTML salvo em {HTML_OUTPUT_PATH}")

    # Salvar payload para envio pelo Manus via MCP
    payload = {
        "subject": assunto,
        "to": RECIPIENT,
        "body": corpo,
        "html_path": HTML_OUTPUT_PATH,
        "total_novas": total_novas,
        "data": today.isoformat(),
        "erros": erros[:5],
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(f"Payload salvo em {OUTPUT_PATH}")

    # Registrar log (email_enviado será atualizado pelo Manus após envio)
    registrar_log(
        data=today.isoformat(),
        total_nac=len(novas_nac),
        total_int=len(novas_int),
        email_enviado=False,  # será atualizado após envio
        erros=erros,
        path=LOG_PATH,
    )

    return 0  # sempre retorna 0 (sucesso) — Manus decide se envia


if __name__ == "__main__":
    sys.exit(main())
