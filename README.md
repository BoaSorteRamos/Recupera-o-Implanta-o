# 🥪 EstuLanches — Cardápio e Pedidos da Cantina Escolar

Sistema web para a cantina da escola: o **aluno** vê o cardápio do dia, monta o pedido e acompanha o status pelo código; a **cantina** gerencia produtos e estoque e move os pedidos pela fila (Recebido → Em preparo → Pronto → Entregue).

**Problema que resolve:** filas longas no intervalo, pedidos anotados em papel, produtos esgotados vendidos mesmo assim e falta de controle de estoque.

## Tecnologias

| Camada | Tecnologia | Por quê |
|---|---|---|
| Backend | Python 3.12 + Flask 3 | Simples, legível, ótimo para APIs REST |
| Servidor | Gunicorn (3 workers × 2 threads) | Servidor WSGI de produção |
| Banco | PostgreSQL 16 | Transações ACID e `SELECT ... FOR UPDATE` para o estoque |
| Cache/limite | Redis 7 | Contador de rate limit compartilhado entre workers |
| Auth | JWT (PyJWT) + hash de senha (Werkzeug/scrypt) | Sessão sem estado, senha nunca em texto puro |
| Frontend | HTML + JS puro servido pelo Flask | Sem build, roda em qualquer navegador |
| Testes | pytest + pytest-cov | Unitários e de integração |
| Infra | Docker + Docker Compose | Ambiente idêntico em qualquer servidor |

## Como subir em produção

```bash
git clone <seu-repo> && cd estulanches
cp .env.example .env          # edite e troque TODAS as senhas e a SECRET_KEY
docker compose up -d --build
docker compose ps             # db, redis e app devem estar "healthy"
docker compose logs app db    # auditar a inicialização
./scripts/validar_implantacao.sh   # validação automática pós-implantação
```

Acesse **http://localhost:8000** · Painel da cantina: usuário/senha definidos em `ADMIN_USER`/`ADMIN_PASSWORD`.

## Testes

```bash
pip install -r requirements-dev.txt
pytest tests/unit                                   # 38 testes — regras de negócio e segurança
TEST_DATABASE_URL=postgresql+psycopg2://user:senha@localhost:5432/estulanches_test \
  pytest tests/integration                          # 16 testes — API + PostgreSQL real
pytest --cov=app                                    # cobertura: 96%
```

- **Unitários** (`tests/unit`): validação de produto, preço com `Decimal` (sem erro de ponto flutuante), limite de itens, máquina de estados do pedido, código único, hash de senha e JWT forjado.
- **Integração** (`tests/integration`): fluxo completo aluno → cantina, baixa e devolução de estoque, estoque insuficiente (409), rotas protegidas (401), cabeçalhos de segurança, tentativa de SQL injection/XSS.

Evidências em `docs/evidencias/`.

## API

| Método | Rota | Acesso |
|---|---|---|
| GET | `/health` | público — testa app e banco |
| GET | `/api/produtos` | público |
| POST/PUT/DELETE | `/api/produtos[/id]` | cantina (JWT) |
| POST | `/api/pedidos` | público (20/min por IP) |
| GET | `/api/pedidos/<codigo>` | público |
| GET | `/api/pedidos?status=` | cantina (JWT) |
| PATCH | `/api/pedidos/<id>/status` | cantina (JWT) |
| POST | `/api/auth/login` | público (5/min por IP) |

## Segurança

- **Segredos fora do código:** tudo vem do `.env`, que está no `.gitignore`. A aplicação **se recusa a iniciar** em produção com a `SECRET_KEY` padrão.
- **Senhas com hash** (scrypt via Werkzeug); **JWT** assinado com expiração de 60 min.
- **Força bruta:** login limitado a 5 tentativas/min por IP (contador no Redis).
- **SQL injection:** só consultas parametrizadas via SQLAlchemy ORM (testado).
- **XSS:** o frontend usa `textContent` (nunca `innerHTML` com dados) e envia `Content-Security-Policy`, `X-Frame-Options: DENY`, `nosniff`.
- **Container endurecido:** usuário não-root, sistema de arquivos `read_only`, `no-new-privileges`, limites de CPU/memória, imagem multi-stage enxuta.
- **Rede:** PostgreSQL e Redis **sem porta exposta** — só a app os alcança pela rede interna `backend`.
- **Erros 500 não expõem stack trace**; exclusão de produto é lógica (preserva histórico).
- Em produção real: HTTPS com proxy reverso (Nginx/Traefik + Let's Encrypt) e backup diário do volume.

## Escalabilidade para o Brasil (conceitual)

Meta: **1 milhão de usuários, 100 mil simultâneos.** Estimativa: cada usuário ativo faz ~1 requisição a cada 10 s → **~10 mil req/s** no pico (intervalos concentram tudo em 15–20 min).

1. **App sem estado (stateless):** o JWT não guarda sessão no servidor, então basta adicionar réplicas. Sai o Compose e entra **Kubernetes** (EKS/GKE/AKS) com **HPA** escalando por CPU/latência — ex.: 40 a 150 pods.
2. **Balanceador + CDN:** Load Balancer na frente; HTML/JS/imagens servidos por CDN (CloudFront/Cloudflare) com cache nas bordas — tira a maior parte do tráfego da app.
3. **Cache do cardápio no Redis Cluster:** o cardápio muda pouco e é a rota mais lida; cache de 30–60 s reduz o banco a uma fração das leituras.
4. **Banco:** PostgreSQL gerenciado (RDS/Cloud SQL) com **réplicas de leitura**, **PgBouncer** para pool de conexões e **particionamento por escola** (`escola_id`). Em escala maior, *sharding* por região.
5. **Fila para picos:** pedidos entram numa fila (RabbitMQ/SQS/Kafka) e workers gravam no banco — o intervalo das 10h não derruba nada; o aluno recebe o código na hora.
6. **Multi-região:** São Paulo como região principal (+ uma secundária para DR); latência baixa no país todo via CDN.
7. **Observabilidade:** Prometheus + Grafana (métricas), logs centralizados (Loki/ELK), alertas e testes de carga (k6/Locust) antes de cada liberação.
8. **Multi-tenant:** cada escola é um tenant isolado por `escola_id`, com limites de taxa por escola.

## Estrutura

```
app/            código (rotas, regras de negócio, modelos, segurança, frontend)
tests/          unit/ e integration/
scripts/        validar_implantacao.sh · gerar_rdm.py
docs/           RDM_EstuLanches.pdf · ROTEIRO_VIDEO.md · evidencias/
Dockerfile · docker-compose.yml · .env.example
```
