#!/usr/bin/env bash
# Validação pós-implantação do EstuLanches.
# Executa: estado dos serviços, auditoria de logs, health check e smoke test.
# Uso: ./scripts/validar_implantacao.sh   (com os containers já no ar)
set -u
URL="http://localhost:${APP_PORT:-8000}"
FALHAS=0
ok()   { echo "  [OK]    $1"; }
erro() { echo "  [FALHA] $1"; FALHAS=$((FALHAS+1)); }

echo "== 1. Estado dos serviços e portas (docker compose ps)"
docker compose ps
for s in db redis app; do
  estado=$(docker inspect -f '{{.State.Health.Status}}' "estulanches-$s" 2>/dev/null || echo "ausente")
  [ "$estado" = "healthy" ] && ok "$s está healthy" || erro "$s está '$estado'"
done

echo; echo "== 2. Auditoria de logs de inicialização (docker compose logs)"
docker compose logs --no-color db  > /tmp/log_db.txt
docker compose logs --no-color app > /tmp/log_app.txt
grep -q "database system is ready to accept connections" /tmp/log_db.txt \
  && ok "PostgreSQL pronto para conexões" || erro "PostgreSQL não reportou prontidão"
grep -q "EstuLanches v" /tmp/log_app.txt \
  && ok "Aplicação iniciada: $(grep -o 'EstuLanches v[0-9.]*' /tmp/log_app.txt | head -1)" || erro "Mensagem de início da aplicação não encontrada"
grep -q "Booting worker" /tmp/log_app.txt && ok "Workers do Gunicorn iniciados" || erro "Workers não iniciados"
CRITICOS=$(grep -iE "(FATAL|PANIC|CRITICAL|Traceback|ERROR)" /tmp/log_app.txt /tmp/log_db.txt | grep -v "GET /health" || true)
[ -z "$CRITICOS" ] && ok "Nenhum erro crítico nos logs" || { erro "Erros encontrados nos logs:"; echo "$CRITICOS"; }

echo; echo "== 3. Health check da aplicação + banco"
SAUDE=$(curl -s "$URL/health")
echo "  $SAUDE"
echo "$SAUDE" | grep -q '"banco":"ok"' && ok "/health retornou banco ok" || erro "/health falhou"

echo; echo "== 4. Smoke test funcional"
N=$(curl -s "$URL/api/produtos" | grep -o '"id"' | wc -l)
[ "$N" -gt 0 ] && ok "Cardápio retornou $N produtos" || erro "Cardápio vazio"
COD=$(curl -s -o /dev/null -w '%{http_code}' "$URL/api/pedidos")
[ "$COD" = "401" ] && ok "Rota protegida exige autenticação (401)" || erro "Rota protegida retornou $COD"

echo
[ "$FALHAS" -eq 0 ] && echo "RESULTADO: IMPLANTAÇÃO VALIDADA" || echo "RESULTADO: $FALHAS FALHA(S) — verificar antes de liberar"
exit "$FALHAS"
