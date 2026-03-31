# Vagas Regulatório Agro

Alerta diário de vagas executivas em regulatório de agrotóxicos, fertilizantes e bioinsumos.

## Estrutura

```
scripts/
  alerta_vagas_regulatorio.py   # Ponto de entrada — executado diariamente às 8h BRT
  monitor_vagas_regulatorio.py  # Coleta e filtragem de vagas (LinkedIn, etc.)
  template_email_vagas.py       # Template HTML aprovado
  gerar_email_vagas.py          # Geração do email HTML
  enviar_email_html.py          # Envio SMTP
data/
  vagas_seen.json               # Histórico de vagas já alertadas
```

## Regras

- Um único envio diário às **8h de Brasília (11h UTC)**
- Marcador Gmail: **Empregos**
- Filtros: Gerente, Diretor, VP, Head, Chief | Agrotóxicos, Fertilizantes, Biológicos,
  Controle de Pragas, Sanitizantes | Regra 4: cargo executivo + empresa agro = relevante
- Apenas vagas NOVAS (não repetir o que já foi enviado)

## Template aprovado

Cabeçalho "INTELLICORE MONITOR · Vagas Regulatório Agro", cards por vaga com badges
de nível, fonte, "NOVA", data, título, empresa, localização, descrição e botão "Ver vaga".

## Execução manual

```bash
cd scripts
python3 alerta_vagas_regulatorio.py
```
