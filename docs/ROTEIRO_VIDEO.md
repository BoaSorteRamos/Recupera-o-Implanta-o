# Roteiro do vídeo — EstuLanches (alvo: 4 min 30 s)

Prepare antes de gravar: containers no ar (`docker compose up -d --build`), navegador em `localhost:8000`, VS Code aberto, terminal limpo e o PDF da RDM aberto.

| Tempo | O que mostrar na tela | O que falar (resumo) |
|---|---|---|
| **0:00–0:25** Apresentação | Rosto/slide com nome e o sistema | "Sou [nome], Técnico de Implantação. O EstuLanches resolve as filas do intervalo, os pedidos em papel e a venda de produto esgotado: o aluno pede pelo celular e acompanha por um código; a cantina controla cardápio, estoque e a fila de preparo." |
| **0:25–1:10** Dockerfile | `Dockerfile` | "É multi-stage: o primeiro estágio instala as dependências, o segundo leva só o necessário — imagem menor e com menos superfície de ataque. Roda com usuário **não-root**, tem **HEALTHCHECK** chamando `/health`, que testa até o banco, e usa **Gunicorn**, servidor de produção, com 3 workers." |
| **1:10–1:55** docker-compose | `docker-compose.yml` | "Três serviços: **app**, **db** com PostgreSQL 16 e **redis**. O banco tem **volume** para não perder dados e **não tem porta pública** — só a app o acessa pela rede interna. O `depends_on` com `service_healthy` faz a app esperar o banco ficar pronto. Senhas vêm do `.env`, fora do Git. A app roda `read_only`, com `no-new-privileges` e limite de CPU e memória." |
| **1:55–2:20** Validação | Terminal: `docker compose ps`, `docker compose logs app db`, `./scripts/validar_implantacao.sh` | "Todos os serviços estão *healthy*, as portas estão certas e os logs não têm erro crítico. O script automatiza essa auditoria." |
| **2:20–2:55** Testes | `pytest -v` rodando + abrir `tests/unit` e `tests/integration` | "São 38 testes unitários — validam regras isoladas: preço em Decimal, limite de itens, máquina de estados do pedido, hash de senha e JWT forjado. E 16 de integração, com a API e um PostgreSQL real: fluxo completo do pedido, baixa e devolução de estoque, rota sem token dando 401 e tentativa de SQL injection. Cobertura de 96%." |
| **2:55–3:20** Código | `app/services.py` (`criar_pedido`, `TRANSICOES`) | "As regras ficam no `services.py`, separadas das rotas. Aqui o `with_for_update` trava a linha do produto, então dois alunos não compram o último item ao mesmo tempo." |
| **3:20–3:50** Sistema | Navegador: montar pedido → código → painel da cantina → Iniciar preparo → Pronto → consultar pelo código | Demonstrar ao vivo, narrando cada passo. |
| **3:50–4:05** Segurança | README, seção Segurança (ou tentar 6 logins errados → 429) | "Senha com hash, JWT com expiração, limite de 5 logins por minuto contra força bruta, consultas parametrizadas, cabeçalhos CSP e a app não sobe em produção com chave padrão." |
| **4:05–4:15** RDM | `docs/RDM_EstuLanches.pdf` | "Esta é a RDM: versão 1.0.0, data, parâmetros alterados, resultado dos testes e status final." |
| **4:15–4:45** Escalabilidade | README, seção Escalabilidade (ou um desenho simples) | "Para 1 milhão de usuários e 100 mil simultâneos — cerca de 10 mil requisições por segundo no intervalo: como a app é sem estado, vai para Kubernetes com autoescala; CDN para os arquivos estáticos; cardápio em cache no Redis; PostgreSQL gerenciado com réplicas de leitura, PgBouncer e particionamento por escola; e uma fila para absorver o pico dos pedidos." |
| **4:45–4:55** Encerramento | Link do GitHub | "O código, o Dockerfile, o compose e a RDM estão no GitHub. Obrigado!" |

Dica: grave em blocos e junte depois; se passar de 5 min, encurte a demonstração do código.
