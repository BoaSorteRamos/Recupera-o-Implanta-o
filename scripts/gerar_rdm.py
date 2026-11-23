"""Gera a Ficha Simplificada de Registro de Mudança (RDM) em PDF (1 página).

Uso:
  python scripts/gerar_rdm.py --responsavel "Seu Nome"                # pré-implantação
  python scripts/gerar_rdm.py --responsavel "Seu Nome" --docker-ok     # após validar_implantacao.sh OK
  Opções: --data "23/11/2026 08:00"  --saida docs/RDM_EstuLanches.pdf
"""
import argparse
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

VERDE = colors.HexColor("#1f7a4d")
VERDE_CLARO = colors.HexColor("#e7f4ec")
AMARELO = colors.HexColor("#fff4e5")
CINZA = colors.HexColor("#dfe3e8")

ap = argparse.ArgumentParser()
ap.add_argument("--responsavel", default="[Nome do Técnico de Implantação]")
ap.add_argument("--data", default=datetime.now().strftime("%d/%m/%Y %H:%M"))
ap.add_argument("--docker-ok", action="store_true", help="docker compose ps/logs validados sem erros")
ap.add_argument("--saida", default="docs/RDM_EstuLanches.pdf")
a = ap.parse_args()

base = ParagraphStyle("b", fontName="Helvetica", fontSize=8.6, leading=10.6)
neg = ParagraphStyle("n", parent=base, fontName="Helvetica-Bold")
tit = ParagraphStyle("t", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=VERDE)
sec = ParagraphStyle("s", parent=base, fontName="Helvetica-Bold", fontSize=9.5, textColor=colors.white)
P = lambda t, s=base: Paragraph(t, s)
W = A4[0] - 30 * mm


def secao(nome):
    t = Table([[P(nome, sec)]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), VERDE), ("TOPPADDING", (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def tabela(linhas, larguras, cabecalho=False, destaques=()):
    t = Table([[P(c, neg if (cabecalho and i == 0) else base) if isinstance(c, str) else c for c in l]
               for i, l in enumerate(linhas)], colWidths=larguras)
    est = [("GRID", (0, 0), (-1, -1), 0.4, CINZA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2)]
    if cabecalho:
        est.append(("BACKGROUND", (0, 0), (-1, 0), VERDE_CLARO))
    for linha, cor in destaques:
        est.append(("BACKGROUND", (-1, linha), (-1, linha), cor))
    t.setStyle(TableStyle(est))
    return t


docker = "<b>OK</b>" if a.docker_ok else "<b>A CONFIRMAR</b> no servidor"
status_final = ("<b>IMPLANTADA COM SUCESSO</b> — sistema liberado para uso em produção."
                if a.docker_ok else
                "<b>APROVADA — AGUARDANDO VALIDAÇÃO DOCKER</b>: código e testes aprovados; "
                "concluir após executar scripts/validar_implantacao.sh no servidor.")

story = [
    P("Ficha Simplificada de Registro de Mudança (RDM)", tit),
    P("Sistema <b>EstuLanches</b> — gestão de cardápio e pedidos da cantina escolar"),
    Spacer(1, 5),
    secao("1. Identificação"),
    tabela([
        ["<b>Nº da RDM</b>", "RDM-2026-001", "<b>Tipo de mudança</b>", "Normal — implantação inicial"],
        ["<b>Versão implantada</b>", "1.0.0 (imagem estulanches:1.0.0)", "<b>Data / horário</b>", a.data],
        ["<b>Responsável</b>", a.responsavel, "<b>Ambiente</b>", "Produção (Docker Compose)"],
        ["<b>Janela</b>", "Fora do horário de intervalo", "<b>Impacto</b>", "Baixo — sistema novo, sem legado"],
    ], [W * .17, W * .33, W * .17, W * .33]),
    Spacer(1, 4),
    secao("2. Descrição da mudança"),
    tabela([[P("Implantação do EstuLanches em containers: <b>app</b> (Python 3.12 + Flask + Gunicorn, 3 workers), "
               "<b>db</b> (PostgreSQL 16, volume persistente pgdata) e <b>redis</b> (Redis 7, contador de "
               "rate limit). Imagem multi-stage, usuário não-root, healthchecks em todos os serviços.")]], [W]),
    Spacer(1, 4),
    secao("3. Parâmetros alterados / configurados"),
    tabela([
        ["Parâmetro", "Valor em produção", "Observação"],
        ["APP_ENV", "production", "Bloqueia início com SECRET_KEY padrão"],
        ["DATABASE_URL", "postgresql+psycopg2://...@db:5432/estulanches", "Credenciais no .env (fora do Git)"],
        ["SECRET_KEY / ADMIN_PASSWORD", "valores aleatórios (.env)", "Assinatura JWT / acesso da cantina"],
        ["JWT_EXPIRES_MINUTES", "60", "Expiração da sessão da cantina"],
        ["RATELIMIT_STORAGE_URI", "redis://redis:6379/0", "Login: 5 req/min · Pedidos: 20 req/min"],
        ["Portas", "app 8000:8000 · db e redis sem porta pública", "Banco isolado na rede interna backend"],
        ["Recursos (app)", "1 CPU · 512 MB · read_only · no-new-privileges", "Limites do container"],
    ], [W * .27, W * .40, W * .33], cabecalho=True),
    Spacer(1, 4),
    secao("4. Resultado dos testes de validação"),
    tabela([
        ["Verificação", "Comando / evidência", "Resultado"],
        ["Testes unitários", "pytest tests/unit (regras de negócio e segurança)", "<b>38/38 aprovados</b>"],
        ["Testes de integração", "pytest tests/integration (API + PostgreSQL 16)", "<b>16/16 aprovados</b>"],
        ["Cobertura de código", "pytest --cov=app", "<b>96%</b>"],
        ["Health check app + banco", "GET /health → {status: ok, banco: ok}", "<b>OK</b>"],
        ["Smoke test funcional", "Cardápio (7 itens), pedido criado, status alterado", "<b>OK</b>"],
        ["Segurança", "Rota sem token → 401 · 6º login/min → 429", "<b>OK</b>"],
        ["Estado dos serviços", "docker compose ps (db, redis, app = healthy)", docker],
        ["Auditoria de logs", "docker compose logs — sem FATAL/ERROR/Traceback", docker],
    ], [W * .25, W * .52, W * .23], cabecalho=True,
        destaques=[(i, VERDE_CLARO) for i in range(1, 7)] +
                  [(i, VERDE_CLARO if a.docker_ok else AMARELO) for i in (7, 8)]),
    Spacer(1, 4),
    secao("5. Plano de retorno (rollback)"),
    tabela([[P("Em caso de falha: <b>docker compose down</b> (o volume pgdata é preservado) → restaurar a tag "
               "anterior da imagem → <b>docker compose up -d</b>. Backup prévio: <b>docker compose exec db "
               "pg_dump -U estulanches estulanches &gt; backup.sql</b>.")]], [W]),
    Spacer(1, 4),
    secao("6. Status final da implantação"),
    tabela([[P(status_final)]], [W], destaques=[(0, VERDE_CLARO if a.docker_ok else AMARELO)]),
    Spacer(1, 12),
    tabela([["Responsável técnico: ________________________________",
             "Aprovação: ________________________________"]], [W / 2, W / 2]),
]

doc = SimpleDocTemplate(a.saida, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                        topMargin=12 * mm, bottomMargin=10 * mm, title="RDM EstuLanches v1.0.0")
doc.build(story)
print("Gerado:", a.saida)
