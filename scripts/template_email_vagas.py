#!/usr/bin/env python3
"""
Template HTML Premium — Alerta de Vagas Regulatórias Agro
==========================================================

Design system:
  - Paleta: azul escuro #0D1B2A (header), verde agro #2E7D32 (nacional),
    azul profissional #1565C0 (internacional), cinza #F8F9FA (fundo)
  - Tipografia: Inter (Google Fonts), fallback Arial/sans-serif
  - Cards com sombra suave, badges coloridos, botão CTA destacado
  - Compatível com Gmail, Outlook, Apple Mail (tabelas HTML + inline CSS)
  - Responsivo: max-width 600px, adaptável a mobile

Uso:
    from template_email_vagas import formatar_email_html
    html = formatar_email_html(nacionais, internacionais, erros)
"""
from __future__ import annotations

import html as html_lib
from datetime import date
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Design System — Tokens de cor e estilo
# ─────────────────────────────────────────────────────────────────────────────

COLORS = {
    "bg_page":        "#EAECEF",
    "bg_card":        "#FFFFFF",
    "bg_header":      "#0D1B2A",
    "bg_header_sub":  "#1A2E45",
    "bg_footer":      "#0D1B2A",
    "bg_status_ok":   "#F0FBF0",
    "bg_status_none": "#F5F7FA",
    "accent_green":   "#2E7D32",   # Nacional
    "accent_blue":    "#1565C0",   # Internacional
    "accent_gold":    "#C8860A",   # Destaque / especial
    "accent_teal":    "#00695C",   # Combinação Vet
    "text_primary":   "#0D1B2A",
    "text_secondary": "#4A5568",
    "text_muted":     "#718096",
    "text_white":     "#FFFFFF",
    "text_green":     "#1B5E20",
    "text_blue":      "#0D47A1",
    "border":         "#E2E8F0",
    "border_green":   "#A5D6A7",
    "border_blue":    "#90CAF9",
    "badge_green_bg": "#E8F5E9",
    "badge_blue_bg":  "#E3F2FD",
    "badge_gold_bg":  "#FFF8E1",
    "badge_teal_bg":  "#E0F2F1",
    "visto_yes_bg":   "#E8F5E9",
    "visto_no_bg":    "#FFEBEE",
    "visto_unk_bg":   "#FFF8E1",
    "remoto_yes_bg":  "#E8F5E9",
    "remoto_no_bg":   "#FFEBEE",
    "remoto_unk_bg":  "#FFF8E1",
}


def _esc(text: str) -> str:
    """Escapa HTML para uso seguro em atributos e conteúdo."""
    if not text:
        return ""
    return html_lib.escape(str(text), quote=True)


def _truncar(texto: str, max_chars: int = 1200) -> str:
    if not texto:
        return ""
    if len(texto) > max_chars:
        return texto[:max_chars].rstrip() + "…"
    return texto


def _badge(texto: str, bg: str, cor: str, border: str = "") -> str:
    border_style = f"border: 1px solid {border};" if border else ""
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;'
        f'background:{bg};color:{cor};font-size:11px;font-weight:700;'
        f'letter-spacing:0.5px;text-transform:uppercase;{border_style}">'
        f'{_esc(texto)}</span>'
    )


def _pill_info(icone: str, texto: str, bg: str = "#F0F4F8", cor: str = "#4A5568") -> str:
    return (
        f'<span style="display:inline-block;padding:4px 10px;border-radius:8px;'
        f'background:{bg};color:{cor};font-size:12px;margin:2px 4px 2px 0;">'
        f'{icone}&nbsp;{_esc(texto)}</span>'
    )


def _indicador_visto(aceita: Optional[bool]) -> str:
    if aceita is True:
        return _pill_info("✅", "Patrocínio de visto: SIM", COLORS["visto_yes_bg"], COLORS["text_green"])
    elif aceita is False:
        return _pill_info("❌", "Patrocínio de visto: NÃO", COLORS["visto_no_bg"], "#B71C1C")
    else:
        return _pill_info("❓", "Patrocínio de visto: verificar", COLORS["visto_unk_bg"], "#5D4037")


def _indicador_remoto(modalidade: Optional[str]) -> str:
    if modalidade == "Remoto":
        return _pill_info("🌐", "Remoto do Brasil: possivelmente SIM", COLORS["remoto_yes_bg"], COLORS["text_green"])
    elif modalidade == "Híbrido":
        return _pill_info("🔀", "Remoto do Brasil: parcial (híbrido)", COLORS["remoto_unk_bg"], "#5D4037")
    elif modalidade == "Presencial":
        return _pill_info("🏢", "Remoto do Brasil: NÃO (presencial)", COLORS["remoto_no_bg"], "#B71C1C")
    else:
        return _pill_info("❓", "Remoto do Brasil: verificar", COLORS["remoto_unk_bg"], "#5D4037")


def _card_vaga(vaga: Dict, numero: int, internacional: bool = False) -> str:
    titulo = vaga.get("titulo") or "Vaga sem título"
    empresa = vaga.get("empresa") or ""
    localizacao = vaga.get("localizacao") or ""
    modalidade = vaga.get("modalidade_trabalho") or ""
    contrato = vaga.get("tipo_contrato") or ""
    salario = vaga.get("salario") or ""
    data_pub = vaga.get("data_publicacao") or ""
    fonte = vaga.get("fonte") or ""
    descricao = vaga.get("descricao") or ""
    link = vaga.get("link") or ""
    aceita_visto = vaga.get("aceita_sem_visto")
    vet = vaga.get("combinacao_vet", False)

    # Cor do card baseada no tipo
    if vet:
        border_color = COLORS["accent_teal"]
        badge_tipo = _badge("Vet + Regulatório", COLORS["badge_teal_bg"], COLORS["accent_teal"])
    elif internacional:
        border_color = COLORS["accent_blue"]
        badge_tipo = _badge("Internacional", COLORS["badge_blue_bg"], COLORS["accent_blue"])
    else:
        border_color = COLORS["accent_green"]
        badge_tipo = _badge("Nacional", COLORS["badge_green_bg"], COLORS["accent_green"])

    # Pills de informações
    pills_html = ""
    if localizacao:
        pills_html += _pill_info("📍", localizacao)
    if modalidade:
        pills_html += _pill_info("💼", modalidade)
    if contrato:
        pills_html += _pill_info("📋", contrato)
    if salario:
        pills_html += _pill_info("💰", salario)
    if data_pub:
        pills_html += _pill_info("📅", f"Publicada: {data_pub}")
    if fonte:
        pills_html += _pill_info("🔗", f"Fonte: {fonte}")

    # Indicadores internacionais
    intl_html = ""
    if internacional:
        intl_html = f"""
        <tr><td style="padding:12px 0 4px 0;">
          <p style="margin:0 0 8px 0;font-size:12px;font-weight:700;
             color:{COLORS['text_secondary']};text-transform:uppercase;
             letter-spacing:0.8px;">Informações para candidatos brasileiros</p>
          {_indicador_visto(aceita_visto)}
          {_indicador_remoto(modalidade)}
        </td></tr>"""

    # Descrição
    desc_html = ""
    if descricao:
        desc_limpa = _truncar(descricao, 1200)
        # Converter quebras de linha em <br>
        desc_limpa = _esc(desc_limpa).replace("\n", "<br>")
        desc_html = f"""
        <tr><td style="padding:12px 0 0 0;border-top:1px solid {COLORS['border']};">
          <p style="margin:0 0 6px 0;font-size:11px;font-weight:700;
             color:{COLORS['text_muted']};text-transform:uppercase;
             letter-spacing:0.8px;">Descrição da vaga</p>
          <p style="margin:0;font-size:13px;line-height:1.7;
             color:{COLORS['text_secondary']};">{desc_limpa}</p>
        </td></tr>"""

    # Botão CTA
    if link:
        cta_html = f"""
        <tr><td style="padding:16px 0 0 0;text-align:center;">
          <a href="{_esc(link)}" target="_blank"
             style="display:inline-block;padding:12px 32px;
             background:{border_color};color:#FFFFFF;
             font-size:14px;font-weight:700;text-decoration:none;
             border-radius:6px;letter-spacing:0.3px;">
             Candidatar-se agora &rarr;
          </a>
        </td></tr>"""
    else:
        cta_html = f"""
        <tr><td style="padding:16px 0 0 0;">
          <p style="margin:0;font-size:12px;color:{COLORS['text_muted']};
             font-style:italic;">Link de candidatura não disponível.</p>
        </td></tr>"""

    return f"""
    <!-- CARD VAGA {numero} -->
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:{COLORS['bg_card']};border-radius:10px;
           border-left:4px solid {border_color};
           box-shadow:0 2px 8px rgba(0,0,0,0.07);
           margin-bottom:20px;">
      <tr><td style="padding:20px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">

          <!-- Número + badges -->
          <tr><td style="padding-bottom:10px;">
            <span style="display:inline-block;width:26px;height:26px;
              border-radius:50%;background:{border_color};color:#FFF;
              font-size:12px;font-weight:700;text-align:center;
              line-height:26px;margin-right:8px;">{numero}</span>
            {badge_tipo}
            {"&nbsp;" + _badge("Vet + Regulatório", COLORS['badge_teal_bg'], COLORS['accent_teal']) if vet and not internacional else ""}
          </td></tr>

          <!-- Título -->
          <tr><td style="padding-bottom:6px;">
            <h2 style="margin:0;font-size:18px;font-weight:700;
               color:{COLORS['text_primary']};line-height:1.3;">
              {_esc(titulo)}
            </h2>
          </td></tr>

          <!-- Empresa -->
          {"<tr><td style='padding-bottom:10px;'><p style='margin:0;font-size:15px;font-weight:600;color:" + COLORS['text_secondary'] + ";'>" + _esc(empresa) + "</p></td></tr>" if empresa else ""}

          <!-- Pills de informações -->
          {"<tr><td style='padding-bottom:12px;'>" + pills_html + "</td></tr>" if pills_html else ""}

          <!-- Indicadores internacionais -->
          {intl_html}

          <!-- Descrição -->
          {desc_html}

          <!-- CTA -->
          {cta_html}

        </table>
      </td></tr>
    </table>"""


def _secao_header(titulo: str, contagem: int, cor: str, icone: str) -> str:
    return f"""
    <!-- SEÇÃO HEADER -->
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="margin-bottom:16px;margin-top:8px;">
      <tr>
        <td style="padding:14px 20px;background:{cor};border-radius:8px;">
          <h2 style="margin:0;font-size:16px;font-weight:700;
             color:#FFFFFF;letter-spacing:0.3px;">
            {icone}&nbsp;&nbsp;{_esc(titulo)}
            <span style="font-size:13px;font-weight:400;opacity:0.85;
               margin-left:8px;">({contagem} vaga{"s" if contagem != 1 else ""})</span>
          </h2>
        </td>
      </tr>
    </table>"""


def _bloco_status_vazio(erros: List[str]) -> str:
    hoje = date.today().strftime("%d/%m/%Y")
    erros_html = ""
    if erros:
        itens = "".join(f'<li style="margin:3px 0;font-size:12px;color:{COLORS["text_muted"]};">{_esc(e)}</li>' for e in erros[:8])
        erros_html = f"""
        <p style="margin:16px 0 4px 0;font-size:12px;font-weight:700;
           color:{COLORS['text_muted']};text-transform:uppercase;letter-spacing:0.5px;">
           Fontes com falha de acesso hoje</p>
        <ul style="margin:0;padding-left:18px;">{itens}</ul>"""

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:{COLORS['bg_status_none']};border-radius:10px;
           border:1px solid {COLORS['border']};margin-bottom:20px;">
      <tr><td style="padding:28px 28px;text-align:center;">
        <div style="font-size:40px;margin-bottom:12px;">🔍</div>
        <h2 style="margin:0 0 8px 0;font-size:18px;font-weight:700;
           color:{COLORS['text_primary']};">Nenhuma vaga nova encontrada hoje</h2>
        <p style="margin:0 0 16px 0;font-size:14px;line-height:1.6;
           color:{COLORS['text_secondary']};">
          O monitoramento de {hoje} foi concluído normalmente.<br>
          Assim que surgirem vagas relevantes, você será alertado imediatamente.
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0"
               style="background:#FFFFFF;border-radius:8px;border:1px solid {COLORS['border']};">
          <tr><td style="padding:16px 20px;text-align:left;">
            <p style="margin:0 0 8px 0;font-size:12px;font-weight:700;
               color:{COLORS['text_muted']};text-transform:uppercase;letter-spacing:0.5px;">
               Fontes monitoradas</p>
            <p style="margin:0;font-size:12px;line-height:1.8;color:{COLORS['text_secondary']};">
              OpenAI Web Search (LinkedIn, portais corporativos, Indeed) &bull;
              LinkedIn Jobs &bull; Vagas.com &bull; Agro2Business &bull; AgCareers<br>
              Portais corporativos: Syngenta &bull; Corteva &bull; Bayer &bull; BASF &bull;
              UPL &bull; Ourofino &bull; FMC &bull; Adama &bull; Nufarm &bull;
              Koppert &bull; Yara &bull; Mosaic &bull; Heringer
            </p>
            {erros_html}
          </td></tr>
        </table>
      </td></tr>
    </table>"""


def _bloco_resumo(n_nac: int, n_int: int) -> str:
    total = n_nac + n_int
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="margin-bottom:24px;">
      <tr>
        <td width="33%" style="padding:0 6px 0 0;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="background:{COLORS['bg_card']};border-radius:8px;
                 border:1px solid {COLORS['border']};text-align:center;">
            <tr><td style="padding:16px 12px;">
              <p style="margin:0;font-size:28px;font-weight:800;
                 color:{COLORS['text_primary']};">{total}</p>
              <p style="margin:4px 0 0 0;font-size:11px;font-weight:600;
                 color:{COLORS['text_muted']};text-transform:uppercase;
                 letter-spacing:0.5px;">Total de vagas</p>
            </td></tr>
          </table>
        </td>
        <td width="33%" style="padding:0 3px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="background:{COLORS['badge_green_bg']};border-radius:8px;
                 border:1px solid {COLORS['border_green']};text-align:center;">
            <tr><td style="padding:16px 12px;">
              <p style="margin:0;font-size:28px;font-weight:800;
                 color:{COLORS['accent_green']};">{n_nac}</p>
              <p style="margin:4px 0 0 0;font-size:11px;font-weight:600;
                 color:{COLORS['text_green']};text-transform:uppercase;
                 letter-spacing:0.5px;">Nacionais</p>
            </td></tr>
          </table>
        </td>
        <td width="33%" style="padding:0 0 0 6px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="background:{COLORS['badge_blue_bg']};border-radius:8px;
                 border:1px solid {COLORS['border_blue']};text-align:center;">
            <tr><td style="padding:16px 12px;">
              <p style="margin:0;font-size:28px;font-weight:800;
                 color:{COLORS['accent_blue']};">{n_int}</p>
              <p style="margin:4px 0 0 0;font-size:11px;font-weight:600;
                 color:{COLORS['text_blue']};text-transform:uppercase;
                 letter-spacing:0.5px;">Internacionais</p>
            </td></tr>
          </table>
        </td>
      </tr>
    </table>"""


def formatar_email_html(
    nacionais: List[Dict],
    internacionais: List[Dict],
    erros: List[str],
) -> str:
    """
    Gera o corpo HTML completo do email de alerta de vagas.
    Retorna string HTML pronta para envio.
    """
    hoje = date.today()
    hoje_fmt = hoje.strftime("%d/%m/%Y")
    dia_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira",
                  "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"][hoje.weekday()]

    total = len(nacionais) + len(internacionais)

    # ── Conteúdo principal ──────────────────────────────────────────────────
    if total == 0:
        conteudo_html = _bloco_status_vazio(erros)
    else:
        conteudo_html = _bloco_resumo(len(nacionais), len(internacionais))

        if nacionais:
            conteudo_html += _secao_header(
                "Vagas Nacionais", len(nacionais), COLORS["accent_green"], "🇧🇷"
            )
            for i, vaga in enumerate(nacionais, 1):
                conteudo_html += _card_vaga(vaga, i, internacional=False)

        if internacionais:
            conteudo_html += _secao_header(
                "Vagas Internacionais", len(internacionais), COLORS["accent_blue"], "🌎"
            )
            conteudo_html += f"""
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="background:{COLORS['badge_blue_bg']};border-radius:8px;
                   border:1px solid {COLORS['border_blue']};margin-bottom:16px;">
              <tr><td style="padding:12px 16px;">
                <p style="margin:0;font-size:12px;line-height:1.6;
                   color:{COLORS['text_blue']};">
                  <strong>Nota:</strong> Para vagas internacionais, são indicadas
                  (quando disponíveis) informações sobre patrocínio de visto e
                  possibilidade de trabalho remoto a partir do Brasil.
                  Confirme sempre diretamente com o empregador.
                </p>
              </td></tr>
            </table>"""
            for i, vaga in enumerate(internacionais, 1):
                conteudo_html += _card_vaga(vaga, i, internacional=True)

        # Erros de fonte
        if erros:
            itens = "".join(
                f'<li style="margin:3px 0;font-size:12px;color:{COLORS["text_muted"]};">{_esc(e)}</li>'
                for e in erros[:8]
            )
            conteudo_html += f"""
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="background:#FFFBF0;border-radius:8px;
                   border:1px solid #FFE082;margin-top:8px;margin-bottom:20px;">
              <tr><td style="padding:14px 18px;">
                <p style="margin:0 0 6px 0;font-size:12px;font-weight:700;
                   color:#5D4037;text-transform:uppercase;letter-spacing:0.5px;">
                   ⚠ Fontes com falha de acesso ({len(erros)})</p>
                <ul style="margin:0;padding-left:18px;">{itens}</ul>
              </td></tr>
            </table>"""

    # ── Template HTML completo ───────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>Alerta de Vagas Regulatório Agro — {hoje_fmt}</title>
<!--[if mso]>
<noscript><xml><o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings></xml></noscript>
<![endif]-->
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  body {{ margin:0; padding:0; background:{COLORS['bg_page']}; }}
  * {{ box-sizing:border-box; }}
  a {{ color:{COLORS['accent_blue']}; }}
  @media only screen and (max-width:620px) {{
    .email-wrapper {{ padding:12px !important; }}
    .email-body {{ padding:20px 16px !important; }}
    .stats-cell {{ display:block !important; width:100% !important;
                   padding:0 0 8px 0 !important; }}
  }}
  @media print {{
    body {{ background:#ffffff !important; font-size:11pt; }}
    table {{ max-width:100% !important; }}
    .email-wrapper {{ padding:0 !important; }}
    a[href]:after {{ content:" (" attr(href) ")"; font-size:9pt; color:#475569; }}
    tr, td {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:{COLORS['bg_page']};
     font-family:'Inter',Arial,Helvetica,sans-serif;">

<!-- Preheader (oculto, aparece no preview do Gmail) -->
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">
  {"Alerta Regulatório Agro — " + str(total) + " vaga(s) nova(s) encontrada(s) hoje." if total > 0 else "Alerta Regulatório Agro — Nenhuma vaga nova hoje. Monitoramento ativo."}
  &zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;
</div>

<!-- Wrapper -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:{COLORS['bg_page']};padding:24px 16px;"
       class="email-wrapper">
<tr><td align="center">

<!-- Container principal -->
<table width="600" cellpadding="0" cellspacing="0" border="0"
       style="max-width:600px;width:100%;">

  <!-- ═══ HEADER ═══ -->
  <tr><td>
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:{COLORS['bg_header']};border-radius:12px 12px 0 0;">
      <tr><td style="padding:28px 32px 20px 32px;">

        <!-- Logo / Marca -->
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td>
              <p style="margin:0;font-size:11px;font-weight:600;
                 color:rgba(255,255,255,0.5);text-transform:uppercase;
                 letter-spacing:1.5px;">HB Advisory · Intellicore</p>
              <h1 style="margin:6px 0 0 0;font-size:22px;font-weight:800;
                 color:{COLORS['text_white']};line-height:1.2;">
                Alerta de Vagas<br>
                <span style="color:#7EC8E3;">Regulatório Agro</span>
              </h1>
            </td>
            <td align="right" valign="top">
              <div style="background:rgba(255,255,255,0.08);border-radius:8px;
                   padding:10px 14px;text-align:center;">
                <p style="margin:0;font-size:20px;">🌱</p>
                <p style="margin:4px 0 0 0;font-size:10px;font-weight:600;
                   color:rgba(255,255,255,0.6);text-transform:uppercase;
                   letter-spacing:0.5px;">Agro</p>
              </div>
            </td>
          </tr>
        </table>

      </td></tr>

      <!-- Sub-header com data e critérios -->
      <tr><td style="padding:0 32px 24px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0"
               style="background:{COLORS['bg_header_sub']};border-radius:8px;">
          <tr><td style="padding:14px 18px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td>
                  <p style="margin:0;font-size:13px;font-weight:600;
                     color:rgba(255,255,255,0.9);">
                    📅&nbsp; {dia_semana}, {hoje_fmt}
                  </p>
                  <p style="margin:6px 0 0 0;font-size:11px;line-height:1.6;
                     color:rgba(255,255,255,0.55);">
                    Gerente · Diretor · Head · Manager · Director<br>
                    Assuntos Regulatórios · Registro · Regulatory Affairs<br>
                    Agrotóxicos · Fertilizantes · Bioinsumos · Defensivos Agrícolas
                  </p>
                </td>
                <td align="right" valign="middle" style="padding-left:12px;">
                  {"<div style='background:#2E7D32;border-radius:20px;padding:8px 14px;text-align:center;'><p style='margin:0;font-size:22px;font-weight:800;color:#FFF;line-height:1;'>" + str(total) + "</p><p style='margin:2px 0 0 0;font-size:10px;font-weight:600;color:rgba(255,255,255,0.8);text-transform:uppercase;letter-spacing:0.5px;'>nova(s)</p></div>" if total > 0 else "<div style='background:rgba(255,255,255,0.08);border-radius:20px;padding:8px 14px;text-align:center;'><p style='margin:0;font-size:13px;font-weight:700;color:rgba(255,255,255,0.6);'>—</p><p style='margin:2px 0 0 0;font-size:10px;font-weight:600;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.5px;'>sem novas</p></div>"}
                </td>
              </tr>
            </table>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </td></tr>

  <!-- ═══ BODY ═══ -->
  <tr><td>
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:{COLORS['bg_card']};padding:28px 32px;"
           class="email-body">
      <tr><td>
        {conteudo_html}
      </td></tr>
    </table>
  </td></tr>

  <!-- ═══ FOOTER ═══ -->
  <tr><td>
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:{COLORS['bg_footer']};border-radius:0 0 12px 12px;">
      <tr><td style="padding:20px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td>
              <p style="margin:0;font-size:12px;font-weight:700;
                 color:rgba(255,255,255,0.9);">HB Advisory · Intellicore</p>
              <p style="margin:4px 0 0 0;font-size:11px;line-height:1.6;
                 color:rgba(255,255,255,0.45);">
                Sistema automatizado de monitoramento de vagas regulatórias.<br>
                Critérios: Gerente/Diretor de Assuntos Regulatórios em Agrotóxicos,
                Defensivos Agrícolas, Fertilizantes ou Bioinsumos; ou combinação
                Assuntos Regulatórios + Medicina Veterinária.
              </p>
            </td>
            <td align="right" valign="top" style="padding-left:16px;">
              <p style="margin:0;font-size:10px;color:rgba(255,255,255,0.3);
                 text-align:right;">Envio diário · 08:00</p>
            </td>
          </tr>
        </table>
      </td></tr>
    </table>
  </td></tr>

</table>
<!-- /Container principal -->

</td></tr>
</table>
<!-- /Wrapper -->

</body>
</html>"""
