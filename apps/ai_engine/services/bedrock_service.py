"""
apps.ai_engine.services.bedrock_service
Wrapper para invocacao do Amazon Bedrock.
"""
import json
import logging
import re
import time
import uuid
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class BedrockInvocationError(Exception):
    """Erro ao invocar recursos do Bedrock."""


class BedrockService:
    """
    Cliente Bedrock para:
    - invoke_model no bedrock-runtime (LLM direto)
    - invoke_agent no bedrock-agent-runtime (Agent + Alias)
    - retrieve em Knowledge Base (RAG)
    """

    MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # segundos
    READ_TIMEOUT = 120  # Aumentado para lidar com inferências complexas do Nova

    def __init__(self):
        region = getattr(settings, "BEDROCK_REGION", "") or getattr(settings, "AWS_REGION", "us-east-1")
        self.region = region
        
        # Configura timeout para evitar que o sistema fique "travado" esperando a LLM
        config = Config(
            read_timeout=self.READ_TIMEOUT,
            connect_timeout=15,
            retries={'max_attempts': self.MAX_RETRIES}
        )
        
        self.client = boto3.client("bedrock-runtime", region_name=region, config=config)
        self.model_id = settings.BEDROCK_MODEL_ID or self.MODEL_ID
        self.max_tokens = settings.BEDROCK_MAX_TOKENS
        self._agent_runtime_client = None
        self._kb_client = None
        self.last_invoke_metadata = {}

    def invoke(
        self,
        system_prompt: str,
        user_message: Optional[str] = None,
        messages: Optional[list] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[list] = None,
    ) -> str:
        """
        Invoca modelo Foundation via bedrock-runtime.
        Suporta user_message unico ou lista de messages (history).
        """
        max_tokens = max_tokens or self.max_tokens

        # Se nao houver messages, cria a partir de user_message
        if not messages:
            messages = [{"role": "user", "content": user_message}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": messages,
        }

        if stop_sequences:
            body["stop_sequences"] = stop_sequences

        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(body),
                )
                response_body = json.loads(response["body"].read())
                elapsed = time.time() - start_time

                content = response_body.get("content", [])
                if not content:
                    raise BedrockInvocationError("Resposta vazia do modelo.")

                text = content[0].get("text", "")
                usage = response_body.get("usage", {})
                logger.info(
                    "Bedrock invoke_model: model=%s, input_tokens=%s, output_tokens=%s, elapsed=%.2fs",
                    self.model_id,
                    usage.get("input_tokens", 0),
                    usage.get("output_tokens", 0),
                    elapsed,
                )
                return text

            except self.client.exceptions.ThrottlingException:
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_DELAY * (2**attempt)
                    logger.warning(
                        "Bedrock throttling. aguardando %ss (tentativa %s/%s)",
                        wait,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                    time.sleep(wait)
                else:
                    raise BedrockInvocationError("Limite de taxa do Bedrock atingido apos tentativas.")

            except ClientError as exc:
                error_code = exc.response["Error"]["Code"]
                logger.error("Bedrock ClientError (%s): %s", error_code, exc)
                raise BedrockInvocationError(str(exc)) from exc

            except Exception as exc:
                logger.error("Bedrock invocation error: %s", exc)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise BedrockInvocationError(str(exc)) from exc

    def generate_text(self, system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
        """Alias de compatibilidade para o método invoke."""
        return self.invoke(system_prompt=system_prompt, user_message=user_message, max_tokens=max_tokens)
    def invoke_converse(
        self,
        system_prompt: str,
        user_message: Optional[str] = None,
        messages: Optional[list] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Invoca modelo via API Converse (necessario para familias como Amazon Nova).
        Suporta tanto user_message unico quanto lista de messages (historico).
        """
        max_tokens = max_tokens or self.max_tokens
        
        # Constrói a lista de mensagens no formato exigido pela Converse API
        converse_messages = []
        
        if messages:
            # Converte o formato padrao (role/content) para o formato da Converse API
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Formata o conteúdo para a Converse API (espera lista de blocos)
                if isinstance(content, str):
                    formatted_content = [{"text": content}]
                else:
                    formatted_content = content # Assume que já está no formato correto
                
                converse_messages.append({
                    "role": role,
                    "content": formatted_content
                })
        elif user_message:
            converse_messages = [
                {
                    "role": "user",
                    "content": [{"text": user_message}],
                }
            ]
        else:
            raise BedrockInvocationError("user_message ou messages deve ser fornecido para invoke_converse.")

        request_kwargs = {
            "modelId": self.model_id,
            "messages": converse_messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
            },
        }
        if system_prompt:
            request_kwargs["system"] = [{"text": system_prompt}]

        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.client.converse(**request_kwargs)
                elapsed = time.time() - start_time

                content = (((response.get("output") or {}).get("message") or {}).get("content") or [])
                if not content:
                    raise BedrockInvocationError("Resposta vazia do modelo (converse).")

                text = content[0].get("text", "")
                usage = response.get("usage", {})
                logger.info(
                    "Bedrock converse: model=%s, input_tokens=%s, output_tokens=%s, elapsed=%.2fs",
                    self.model_id,
                    usage.get("inputTokens", 0),
                    usage.get("outputTokens", 0),
                    elapsed,
                )
                return text
            except self.client.exceptions.ThrottlingException:
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_DELAY * (2**attempt)
                    logger.warning(
                        "Bedrock throttling (converse). aguardando %ss (tentativa %s/%s)",
                        wait,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                    time.sleep(wait)
                else:
                    raise BedrockInvocationError("Limite de taxa do Bedrock atingido apos tentativas (converse).")
            except ClientError as exc:
                error_code = exc.response["Error"]["Code"]
                logger.error("Bedrock ClientError no converse (%s): %s", error_code, exc)
                raise BedrockInvocationError(str(exc)) from exc
            except Exception as exc:
                logger.error("Bedrock converse invocation error: %s", exc)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise BedrockInvocationError(str(exc)) from exc

    def invoke_agent(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_alias_id: Optional[str] = None,
        end_session: bool = True,
    ) -> str:
        """
        Invoca Bedrock Agent Runtime usando agentId + agentAliasId.
        """
        final_agent_id = agent_id or getattr(settings, "BEDROCK_AGENT_ID", "")
        final_alias_id = agent_alias_id or getattr(settings, "BEDROCK_AGENT_ALIAS_ID", "")
        if not final_agent_id or not final_alias_id:
            raise BedrockInvocationError(
                "BEDROCK_AGENT_ID e BEDROCK_AGENT_ALIAS_ID sao obrigatorios para invoke_agent."
            )

        if self._agent_runtime_client is None:
            self._agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name=self.region)

        final_session_id = session_id or self._build_agent_session_id()
        enable_trace = bool(getattr(settings, "BEDROCK_AGENT_ENABLE_TRACE", False))

        try:
            start_time = time.time()
            response = self._agent_runtime_client.invoke_agent(
                agentId=final_agent_id,
                agentAliasId=final_alias_id,
                sessionId=final_session_id,
                inputText=user_message,
                enableTrace=enable_trace,
                endSession=end_session,
            )
            text = self._collect_agent_completion_text(response)
            
            # Detecção de erros retornados como texto (característica de alguns comportamentos do Bedrock)
            if "Session is terminated" in text or "AccessDenied" in text:
                logger.error(f"Erro detectado no corpo da resposta do Agent: {text}")
                raise BedrockInvocationError(f"Erro no Agent Runtime: {text}")

            elapsed = time.time() - start_time
            logger.info(
                "Bedrock invoke_agent: agent_id=%s alias_id=%s session_id=%s elapsed=%.2fs",
                final_agent_id,
                final_alias_id,
                final_session_id,
                elapsed,
            )
            return text
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            logger.error("Bedrock Agent ClientError (%s): %s", error_code, exc)
            raise BedrockInvocationError(str(exc)) from exc
        except Exception as exc:
            logger.error("Bedrock Agent invocation error: %s", exc)
            raise BedrockInvocationError(str(exc)) from exc

    def invoke_with_json_output(
        self,
        system_prompt: str,
        user_message: Optional[str] = None,
        messages: Optional[list] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        Invoca Bedrock e espera saida JSON.
        Suporta histórico de mensagens para sessões stateful.
        """
        json_instruction = (
            "\n\nIMPORTANTE: responda APENAS com JSON valido, "
            "sem texto adicional antes ou depois do JSON. "
            "Nao use markdown code blocks."
        )

        current_messages = []
        if messages:
            current_messages = list(messages)
            # Adiciona a instrução JSON à última mensagem do usuário se existir
            if current_messages and current_messages[-1]["role"] == "user":
                current_messages[-1]["content"] += json_instruction
        elif user_message:
            current_messages = [{"role": "user", "content": user_message + json_instruction}]
        else:
            raise ValueError("user_message ou messages deve ser fornecido.")

        metadata = {
            "provider": "bedrock",
            "model_id": self.model_id,
            "used_agent_runtime": False,
            "used_model_runtime": False,
            "model_runtime_api": "",
            "fallback_to_model_runtime": False,
            "response_origin": "",
            "success": False,
        }
        # Extrai a última mensagem para o Agent Runtime (que espera string única)
        user_message_with_json = current_messages[-1]["content"] if current_messages else ""

        used_agent_runtime = False
        if self._should_use_agent_runtime():
            used_agent_runtime = True
            metadata["used_agent_runtime"] = True
            payload = self._build_agent_input_message(system_prompt, user_message_with_json)
            try:
                response_text = self.invoke_agent(user_message=payload, session_id=session_id, end_session=True)
            except (BedrockInvocationError, Exception) as e:
                logger.warning(f"Falha ao invocar Agent Runtime ({e}). Tentando fallback para Model Runtime.")
                response_text = "" # Força falha no parse inicial para disparar o fallback abaixo
        else:
            metadata["used_model_runtime"] = True
            runtime_api, response_text = self._invoke_model_runtime(
                system_prompt=system_prompt,
                user_message=None,
                messages=current_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            metadata["model_runtime_api"] = runtime_api

        parsed = self._parse_json_response(response_text)
        if parsed is not None:
            metadata["response_origin"] = "agent_runtime" if used_agent_runtime else "model_runtime"
            metadata["success"] = True
            self.last_invoke_metadata = metadata
            return parsed

        if used_agent_runtime:
            logger.warning(
                "Agent runtime retornou payload sem JSON valido. Fallback para invoke_model sera aplicado."
            )
            metadata["fallback_to_model_runtime"] = True
            metadata["used_model_runtime"] = True
            runtime_api, fallback_text = self._invoke_model_runtime(
                system_prompt=system_prompt,
                user_message=None,
                messages=current_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            metadata["model_runtime_api"] = runtime_api
            parsed_fallback = self._parse_json_response(fallback_text)
            if parsed_fallback is not None:
                metadata["response_origin"] = "model_runtime_fallback_after_agent_runtime"
                metadata["success"] = True
                self.last_invoke_metadata = metadata
                return parsed_fallback
            response_text = fallback_text

        self.last_invoke_metadata = metadata
        raise BedrockInvocationError("Resposta do modelo nao e JSON valido.")

    def count_tokens_estimate(self, text: str) -> int:
        """Estimativa simples de tokens."""
        return len(text) // 4

    def retrieve_kb_context(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> list:
        """
        Recupera contexto de uma Knowledge Base do Bedrock para RAG.
        Falhas nesta etapa nao quebram a geracao principal.
        """
        kb_id = knowledge_base_id or getattr(settings, "BEDROCK_KB_ID", "")
        text_query = (query or "").strip()
        if not kb_id or not text_query:
            return []

        if self._kb_client is None:
            self._kb_client = boto3.client("bedrock-agent-runtime", region_name=self.region)

        number_of_results = max_results or getattr(settings, "BEDROCK_KB_MAX_RESULTS", 5)
        number_of_results = max(1, min(int(number_of_results), 20))

        try:
            response = self._kb_client.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={"text": text_query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": number_of_results,
                    }
                },
            )
        except ClientError as exc:
            logger.warning("Bedrock KB retrieve falhou: %s", exc)
            return []
        except Exception as exc:
            logger.warning("Erro inesperado no retrieve da KB: %s", exc)
            return []

        snippets = []
        for item in response.get("retrievalResults", []) or []:
            content = item.get("content") or {}
            text = (content.get("text") or "").strip()
            if not text:
                continue
            snippets.append(
                {
                    "text": text,
                    "score": item.get("score"),
                    "source": self._extract_kb_source(item.get("location") or {}),
                }
            )
        return snippets

    def _should_use_agent_runtime(self) -> bool:
        return bool(
            getattr(settings, "USE_BEDROCK_AGENT_RUNTIME", False)
            and getattr(settings, "BEDROCK_AGENT_ID", "")
            and getattr(settings, "BEDROCK_AGENT_ALIAS_ID", "")
        )

    def _invoke_model_runtime(
        self,
        system_prompt: str,
        user_message: Optional[str] = None,
        messages: Optional[list] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, str]:
        if self._should_use_converse_api():
            return (
                "converse",
                self.invoke_converse(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            )
        return (
            "invoke_model",
            self.invoke(
                system_prompt=system_prompt,
                user_message=user_message,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
        )

    def _should_use_converse_api(self) -> bool:
        return str(self.model_id or "").strip().lower().startswith("amazon.nova")

    def _build_agent_input_message(self, system_prompt: str, user_message: str) -> str:
        return (
            "SYSTEM_CONTEXT_START\n"
            f"{system_prompt}\n"
            "SYSTEM_CONTEXT_END\n\n"
            "USER_REQUEST_START\n"
            f"{user_message}\n"
            "USER_REQUEST_END"
        )

    def _build_agent_session_id(self) -> str:
        prefix = str(getattr(settings, "BEDROCK_AGENT_SESSION_PREFIX", "agent-bi") or "agent-bi")
        safe_prefix = "".join(ch for ch in prefix if ch.isalnum() or ch in "._:-").strip("._:-")
        safe_prefix = safe_prefix or "agent-bi"
        suffix = uuid.uuid4().hex[:20]
        return f"{safe_prefix}-{suffix}"[:100]

    def _collect_agent_completion_text(self, response: dict) -> str:
        completion_stream = response.get("completion")
        if completion_stream is None:
            raise BedrockInvocationError("Resposta do Agent Runtime nao contem stream de completion.")

        parts = []
        for event in completion_stream:
            chunk = event.get("chunk")
            if not chunk:
                continue
            payload = chunk.get("bytes", b"")
            if isinstance(payload, str):
                parts.append(payload)
            elif isinstance(payload, (bytes, bytearray)):
                parts.append(payload.decode("utf-8", errors="ignore"))

        text = "".join(parts).strip()
        if not text:
            raise BedrockInvocationError("Resposta vazia do Bedrock Agent.")
        return text

    def _parse_json_response(self, response_text: str) -> dict | None:
        if not response_text:
            return None
            
        text = response_text.strip()
        
        # 1. Tentativa 1: JSON Direto (mais rápido)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Tentativa 2: Extrair bloco de markdown ```json ... ``` com segurança
        if "```" in text:
            # Encontra o que estiver entre os primeiros ``` e os últimos ```
            try:
                # Tenta primeiro com a tag json
                match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
                if not match:
                    # Tenta apenas os backticks
                    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
                
                if match:
                    candidate = match.group(1).strip()
                    return json.loads(candidate)
            except (json.JSONDecodeError, AttributeError, ValueError):
                pass

        # 3. Tentativa 3: Força bruta - encontrar o primeiro { e o último }
        # Esta é a técnica mais resiliente para modelos que "falam" antes do JSON
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_part = text[start:end+1]
                return json.loads(json_part)
        except (json.JSONDecodeError, ValueError):
            pass
            
        logger.error("Falha total ao processar JSON do Bedrock. response=%s", (response_text or "")[:500])
        return None

    def _extract_kb_source(self, location: dict) -> str:
        """
        Extrai referencia textual amigavel de origem de um resultado da KB.
        """
        if not isinstance(location, dict):
            return ""

        s3_uri = (location.get("s3Location") or {}).get("uri")
        if s3_uri:
            return s3_uri

        web_url = (location.get("webLocation") or {}).get("url")
        if web_url:
            return web_url

        sql_info = location.get("sqlLocation") or {}
        query = sql_info.get("query")
        if query:
            return query

        document = location.get("documentLocation") or {}
        document_uri = document.get("uri")
        if document_uri:
            return document_uri

        return ""

    def generate_text(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Método wrapper para gerar texto. Usado pelos agentes Supervisor e Pandas.
        Decide automaticamente entre invoke ou invoke_converse baseado no modelo.
        """
        _, response_text = self._invoke_model_runtime(
            system_prompt=system_prompt,
            user_message=user_message,
            messages=None,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response_text
