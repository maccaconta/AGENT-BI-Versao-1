# Bedrock Agent Runtime Setup (Real AWS)

Este documento provisiona e conecta um Bedrock Agent real ao backend do Agent-BI.

## 1. Pre-requisitos

- AWS CLI v2 instalado e autenticado.
- Permissoes IAM para:
  - `bedrock-agent:create-agent`
  - `bedrock-agent:prepare-agent`
  - `bedrock-agent:create-agent-alias`
  - `bedrock-agent:get-agent`
  - `bedrock-agent:list-agent-aliases`
  - `bedrock-agent-runtime:invoke-agent`
  - (opcional RAG) `bedrock-agent-runtime:retrieve`
- Role IAM para o agente (`AgentResourceRoleArn`) com acesso ao modelo e KB.

## 2. Criar Agent + Alias

```powershell
powershell -ExecutionPolicy Bypass -File scripts/aws/create_bedrock_agent_and_alias.ps1 `
  -AgentName "agent-bi-prod" `
  -AgentResourceRoleArn "arn:aws:iam::<ACCOUNT_ID>:role/bedrock-agent-bi-role" `
  -Region "us-east-1"
```

O script retorna:
- `BEDROCK_AGENT_ID`
- `BEDROCK_AGENT_ALIAS_ID`

## 3. Configurar backend

Defina no ambiente (ou `.env`):

```text
USE_BEDROCK_LLM=True
USE_BEDROCK_AGENT_RUNTIME=True
BEDROCK_REGION=us-east-1
BEDROCK_AGENT_ID=<agent-id>
BEDROCK_AGENT_ALIAS_ID=<agent-alias-id>
BEDROCK_KB_ID=<opcional>
BEDROCK_KB_MAX_RESULTS=5
```

Observacao:
- Quando `USE_BEDROCK_AGENT_RUNTIME=True` e `BEDROCK_AGENT_ID/BEDROCK_AGENT_ALIAS_ID` existem, o backend usa `invoke_agent`.
- Caso contrario, continua usando `invoke_model`.

## 4. Smoke test no Agent Runtime (AWS CLI)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/aws/smoke_test_bedrock_agent.ps1 `
  -AgentId "<agent-id>" `
  -AliasId "<alias-id>" `
  -Region "us-east-1"
```

Nota:
- algumas versoes do AWS CLI ainda nao expõem `bedrock-agent-runtime invoke-agent`;
- o script usa boto3 internamente para garantir o teste real de runtime.

## 5. Smoke test via API Agent-BI

Com backend em execucao:

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/copilot/generate" `
  -H "Content-Type: application/json" `
  -d "{`"currentUserPrompt`":`"Gerar resumo executivo e distribuicao por dimensao.`",`"datasets`":[]}"
```

## 6. Uso da Knowledge Base para template HTML corporativo

- Publique na KB um documento com:
  - layout HTML padrao;
  - padroes de cor;
  - guideline de componentes.
- Envie `knowledgeBasePromptHints` no payload para reforcar a busca.
- O backend inclui esse contexto em `ragRetrievedContext`.

## 7. SQL com fontes aleatorias

- Datasets ingeridos no modo local sao materializados em SQLite analitico separado:
  - `LOCAL_ANALYTICS_SQLITE_PATH`
- Isso evita mistura com tabelas administrativas.
- O NL2SQL usa schema/relacionamentos recebidos, sem inventar tabelas/colunas.
