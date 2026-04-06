"""
apps.ai_engine.agents.infra_agent
───────────────────────────────────
Infra Agent: gera Terraform completo para provisionamento de infraestrutura AWS.
"""
import logging
import time
from dataclasses import dataclass, field

from apps.ai_engine.services.bedrock_service import BedrockService, BedrockInvocationError

logger = logging.getLogger(__name__)

INFRA_SYSTEM_PROMPT = """Você é um especialista em AWS e Terraform, chamado Agent-BI Infra Agent.

Sua tarefa é gerar código Terraform completo e production-ready para provisionar
a infraestrutura necessária para um projeto no Agent-BI.

## Serviços AWS a Provisionar
- Amazon S3: buckets raw, processed e dashboards com políticas IAM corretas
- AWS Glue: database, tabelas e crawlers
- Amazon Athena: workgroup com output no S3
- AWS IAM: roles e policies para Glue, Lambda e Athena
- Amazon CloudFront: distribuição para dashboards públicos (opcional)

## Regras Obrigatórias

### Segurança
- Nunca expor credenciais hardcoded
- Usar KMS para criptografia S3 (aws:kms)
- Bloquear acesso público nos buckets de dados
- Usar princípio do menor privilégio nas policies IAM

### Nomenclatura
- Prefixo: agent-bi-{tenant_slug}-{project_slug}
- Tags obrigatórias: Project, Tenant, Environment, ManagedBy

### Terraform
- Version >= 1.6
- AWS Provider >= 5.0
- Usar variáveis para todos os valores configuráveis
- Outputs para todos os recursos criados
- Backend S3 configurável

## Formato de Saída (JSON)
{
  "files": {
    "main.tf": "...",
    "variables.tf": "...",
    "outputs.tf": "...",
    "versions.tf": "..."
  },
  "estimated_resources": 10,
  "notes": "...",
  "apply_order": ["aws_s3_bucket", "aws_glue_catalog_database", ...]
}
"""


@dataclass
class InfraAgentResult:
    """Resultado do Infra Agent."""
    files: dict = field(default_factory=dict)
    estimated_resources: int = 0
    notes: str = ""
    apply_order: list = field(default_factory=list)
    execution_time_seconds: float = 0.0
    raw_response: dict = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return "main.tf" in self.files and "variables.tf" in self.files


class InfraAgentError(Exception):
    pass


class InfraAgent:
    """
    Infra Agent: gera Terraform para provisionamento automático de infraestrutura AWS.

    Gera módulos para:
    - S3 (raw, processed, dashboards)
    - Glue (database, crawlers)
    - Athena (workgroup)
    - IAM (roles e policies)
    - CloudFront (opcional)
    """

    def __init__(self):
        self.bedrock = BedrockService()

    def generate_infra(
        self,
        tenant_slug: str,
        project_name: str,
        project_id: str,
        datasets: list,
        aws_region: str = "us-east-1",
        include_cloudfront: bool = True,
    ) -> InfraAgentResult:
        """
        Gera código Terraform para um projeto.

        Args:
            tenant_slug: Slug do tenant
            project_name: Nome do projeto
            project_id: UUID do projeto
            datasets: Lista de datasets com schemas
            aws_region: Região AWS
            include_cloudfront: Incluir CloudFront para dashboards

        Returns:
            InfraAgentResult com arquivos Terraform
        """
        start_time = time.time()
        logger.info(f"Infra Agent: gerando terraform para projeto '{project_name}'")

        prompt = self._build_prompt(
            tenant_slug=tenant_slug,
            project_name=project_name,
            project_id=project_id,
            datasets=datasets,
            aws_region=aws_region,
            include_cloudfront=include_cloudfront,
        )

        try:
            response_data = self.bedrock.invoke_with_json_output(
                system_prompt=INFRA_SYSTEM_PROMPT,
                user_message=prompt,
                temperature=0.1,  # Muito determinístico para IaC
                max_tokens=8192,
            )
        except BedrockInvocationError as e:
            raise InfraAgentError(f"Erro ao gerar Terraform: {e}") from e

        result = InfraAgentResult(
            files=response_data.get("files", {}),
            estimated_resources=response_data.get("estimated_resources", 0),
            notes=response_data.get("notes", ""),
            apply_order=response_data.get("apply_order", []),
            execution_time_seconds=time.time() - start_time,
            raw_response=response_data,
        )

        if not result.is_valid:
            # Fallback: gerar template básico
            result = self._generate_basic_template(
                tenant_slug, project_name, project_id, datasets, aws_region
            )

        logger.info(
            f"Infra Agent: {result.estimated_resources} recursos gerados "
            f"em {result.execution_time_seconds:.2f}s"
        )

        return result

    def _build_prompt(self, **kwargs) -> str:
        """Constrói prompt contextual para o Infra Agent."""
        datasets_desc = ""
        for ds in kwargs.get("datasets", []):
            datasets_desc += f"\n- **{ds.get('name')}**: {ds.get('row_count', 0)} linhas, "
            datasets_desc += f"schema: {ds.get('schema_json', {}).get('column_count', 0)} colunas"

        return f"""# Geração de Infraestrutura Terraform

## Contexto do Projeto
- **Tenant:** {kwargs['tenant_slug']}
- **Projeto:** {kwargs['project_name']}
- **Project ID:** {kwargs['project_id']}
- **Região AWS:** {kwargs['aws_region']}
- **Incluir CloudFront:** {'Sim' if kwargs['include_cloudfront'] else 'Não'}

## Datasets do Projeto
{datasets_desc}

## Tarefa
Gere o código Terraform completo para provisionar:

1. **S3 Buckets:**
   - `agent-bi-{kwargs['tenant_slug']}-raw` → dados brutos
   - `agent-bi-{kwargs['tenant_slug']}-processed` → Parquet
   - `agent-bi-{kwargs['tenant_slug']}-dashboards` → HTML publicado

2. **Glue:**
   - Database: `agentbi_{kwargs['tenant_slug'].replace('-', '_')}`
   - Crawler para o bucket processed

3. **Athena:**
   - Workgroup: `agent-bi-{kwargs['tenant_slug']}-wg`
   - Output: sub-pasta em results bucket

4. **IAM:**
   - Role para Glue Crawler com acesso S3
   - Role para Lambda com acesso Athena, S3, Glue, Bedrock

5. **CloudFront** (se solicitado):
   - Distribution apontando para bucket de dashboards
   - OAC (Origin Access Control)

Use variáveis Terraform para region, account_id, tenant_slug, project_id.
Adicione outputs para todos os ARNs e URLs importantes.
"""

    def _generate_basic_template(
        self, tenant_slug: str, project_name: str, project_id: str,
        datasets: list, aws_region: str
    ) -> InfraAgentResult:
        """Template Terraform básico como fallback."""
        project_slug = project_name.lower().replace(" ", "-")[:30]
        prefix = f"agent-bi-{tenant_slug}-{project_slug}"

        main_tf = f'''# Generated by Agent-BI Infra Agent
# Project: {project_name} ({project_id})
# Tenant: {tenant_slug}

data "aws_caller_identity" "current" {{}}

# ─── S3 Buckets ───────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "raw" {{
  bucket = "{prefix}-raw-${{data.aws_caller_identity.current.account_id}}"
  tags   = local.common_tags
}}

resource "aws_s3_bucket" "processed" {{
  bucket = "{prefix}-processed-${{data.aws_caller_identity.current.account_id}}"
  tags   = local.common_tags
}}

resource "aws_s3_bucket" "dashboards" {{
  bucket = "{prefix}-dashboards-${{data.aws_caller_identity.current.account_id}}"
  tags   = local.common_tags
}}

resource "aws_s3_bucket_public_access_block" "raw" {{
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}

resource "aws_s3_bucket_public_access_block" "processed" {{
  bucket                  = aws_s3_bucket.processed.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}

# ─── Glue ─────────────────────────────────────────────────────────────────────

resource "aws_glue_catalog_database" "main" {{
  name        = "agentbi_{tenant_slug.replace('-', '_')}_{project_slug.replace('-', '_')}"
  description = "Agent-BI: {project_name}"
}}

resource "aws_glue_crawler" "processed" {{
  name          = "{prefix}-crawler"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.main.name

  s3_target {{
    path = "s3://${{aws_s3_bucket.processed.bucket}}/processed/"
  }}

  recrawl_policy {{
    recrawl_behavior = "CRAWL_EVERYTHING"
  }}

  tags = local.common_tags
}}

# ─── Athena ───────────────────────────────────────────────────────────────────

resource "aws_athena_workgroup" "main" {{
  name = "{prefix}-wg"

  configuration {{
    enforce_workgroup_configuration = true
    result_configuration {{
      output_location = "s3://agent-bi-athena-results-${{data.aws_caller_identity.current.account_id}}/{tenant_slug}/"
    }}
  }}

  tags = local.common_tags
}}

# ─── IAM ──────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "glue" {{
  name = "{prefix}-glue-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = {{ Service = "glue.amazonaws.com" }}
    }}]
  }})
  tags = local.common_tags
}}

resource "aws_iam_role_policy_attachment" "glue_service" {{
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}}

resource "aws_iam_role_policy" "glue_s3" {{
  name = "{prefix}-glue-s3"
  role = aws_iam_role.glue.id
  policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.raw.arn,
        "${{aws_s3_bucket.raw.arn}}/*",
        aws_s3_bucket.processed.arn,
        "${{aws_s3_bucket.processed.arn}}/*",
      ]
    }}]
  }})
}}

# ─── Locals ───────────────────────────────────────────────────────────────────

locals {{
  common_tags = {{
    Project     = "{project_name}"
    Tenant      = "{tenant_slug}"
    ProjectID   = "{project_id}"
    Environment = var.environment
    ManagedBy   = "agent-bi-infra-agent"
  }}
}}
'''

        variables_tf = f'''variable "aws_region" {{
  description = "Região AWS"
  type        = string
  default     = "{aws_region}"
}}

variable "environment" {{
  description = "Ambiente (prod, staging, dev)"
  type        = string
  default     = "prod"
}}

variable "tenant_slug" {{
  description = "Slug do tenant"
  type        = string
  default     = "{tenant_slug}"
}}
'''

        outputs_tf = '''output "s3_raw_bucket" {
  value = aws_s3_bucket.raw.bucket
}

output "s3_processed_bucket" {
  value = aws_s3_bucket.processed.bucket
}

output "s3_dashboards_bucket" {
  value = aws_s3_bucket.dashboards.bucket
}

output "glue_database" {
  value = aws_glue_catalog_database.main.name
}

output "athena_workgroup" {
  value = aws_athena_workgroup.main.name
}

output "glue_role_arn" {
  value = aws_iam_role.glue.arn
}
'''

        versions_tf = '''terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
'''

        return InfraAgentResult(
            files={
                "main.tf": main_tf,
                "variables.tf": variables_tf,
                "outputs.tf": outputs_tf,
                "versions.tf": versions_tf,
            },
            estimated_resources=12,
            notes="Template básico gerado como fallback. Revise antes de aplicar.",
        )
