# ============================================================
# EstuLanches - imagem de produção
# Multi-stage: o estágio "builder" compila as dependências e o
# estágio final leva só o necessário (imagem menor e mais segura).
# ============================================================

# ---------- Estágio 1: instalar dependências ----------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt .
# Instala num diretório isolado que será copiado para a imagem final
RUN pip install --prefix=/install -r requirements.txt


# ---------- Estágio 2: imagem final ----------
FROM python:3.12-slim

LABEL org.opencontainers.image.title="EstuLanches" \
      org.opencontainers.image.description="Gestão de cardápio e pedidos da cantina escolar" \
      org.opencontainers.image.version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000

# Usuário sem privilégios: se a aplicação for comprometida, o invasor não é root
RUN groupadd --system app && useradd --system --gid app --home /app app

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=app:app app/ ./app/
COPY --chown=app:app wsgi.py .

USER app

EXPOSE 8000

# O Docker marca o container como "unhealthy" se /health falhar (inclui teste do banco)
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# Gunicorn: servidor WSGI de produção (o servidor do Flask é só para desenvolvimento)
# --preload cria as tabelas uma única vez antes de criar os workers
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", \
     "--preload", "--no-control-socket", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
