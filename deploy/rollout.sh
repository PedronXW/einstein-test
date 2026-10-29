#!/usr/bin/env bash
# Rollout de uma nova imagem nos serviços ECS (api + worker).
#
# Uso: ./deploy/rollout.sh <env> <image_uri>
#   env     = "prod" (define os nomes de cluster/serviços: einstein-prod-*)
#   image   = URI completo da imagem ECR (ex.: 123456.dkr.ecr.us-east-1.amazonaws.com/einstein-test-prod:prod-abc123)
#
# O script descreve o task definition vigente de cada família, cria uma nova
# revisão apontando para a imagem informada e faz update-service (rolling).
# As migrations já rodam no boot da task (docker/entrypoint.sh + alembic).

set -euo pipefail

env="${1:?uso: $0 <env> <image_uri>}"
image="${2:?uso: $0 <env> <image_uri>}"
region="${AWS_REGION:-us-east-1}"

cluster="einstein-${env}"

# Filtra os campos aceitos no register + troca a imagem do container.
# Usa jq quando disponível; senão cai no python3 (runners e dev sem jq).
render_taskdef() {
  local full="$1" out="$2"

  if command -v jq >/dev/null 2>&1; then
    jq \
      '{family, taskRoleArn, executionRoleArn, networkMode, containerDefinitions,
        volumes, placementConstraints, requiresCompatibilities, cpu, memory,
        runtimePlatform, ephemeralStorage, proxyConfiguration} |
       .containerDefinitions |= map(.image = $image) |
       del(.[] | select(. == null))' \
      --arg image "${image}" \
      "${full}" > "${out}"
    return
  fi

  python3 - "${full}" "${out}" <<'PY'
import json, sys

with open(sys.argv[1]) as f:
    td = json.load(f)

keep = ("family", "taskRoleArn", "executionRoleArn", "networkMode",
        "containerDefinitions", "volumes", "placementConstraints",
        "requiresCompatibilities", "cpu", "memory", "runtimePlatform",
        "ephemeralStorage", "proxyConfiguration")

new = {k: td[k] for k in keep if td.get(k) is not None}
for c in new["containerDefinitions"]:
    c["image"] = sys.argv[3] if len(sys.argv) > 3 else __import__("os").environ.get("ROLLOUT_IMAGE", "")

with open(sys.argv[2], "w") as f:
    json.dump(new, f)
PY
}

rollout_one() {
  local service="$1"
  local family="${service}"
  local tmp="${RUNNER_TEMP:-/tmp}/${family}-${image##*:}.json"

  echo "==> [${service}] descrevendo task definition vigente (${family})"
  aws ecs describe-task-definition \
    --task-definition "${family}" \
    --region "${region}" \
    --query 'taskDefinition' \
    > "${tmp}.full.json"

  ROLLOUT_IMAGE="${image}" render_taskdef "${tmp}.full.json" "${tmp}"

  echo "==> [${service}] registrando nova revisão do task definition"
  local td_arn
  td_arn="$(aws ecs register-task-definition \
    --cli-input-json "file://${tmp}" \
    --region "${region}" \
    --query 'taskDefinition.taskDefinitionArn' --output text)"

  echo "==> [${service}] atualizando serviço para ${td_arn}"
  aws ecs update-service \
    --cluster "${cluster}" \
    --service "${service}" \
    --task-definition "${td_arn}" \
    --force-new-deployment \
    --region "${region}" \
    --query 'service.serviceName' --output text
}

rollout_one "${cluster}-api"
rollout_one "${cluster}-worker"

echo "==> aguardando estabilização dos serviços"
aws ecs wait services-stable \
  --cluster "${cluster}" \
  --services "${cluster}-api" "${cluster}-worker" \
  --region "${region}"

echo "==> deploy concluído (env=${env}, image=${image})"