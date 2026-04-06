"""
apps.users.services.cognito_service
────────────────────────────────────
Integração com Amazon Cognito para autenticação e gerenciamento de usuários.
"""
import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class CognitoService:
    """Wrapper do Amazon Cognito para operações de usuário."""

    def __init__(self):
        self.client = boto3.client(
            "cognito-idp",
            region_name=settings.COGNITO_REGION,
        )
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self.app_client_id = settings.COGNITO_APP_CLIENT_ID

    def create_user(self, email: str, temp_password: str, full_name: str) -> Optional[dict]:
        """Cria usuário no Cognito User Pool."""
        try:
            response = self.client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "name", "Value": full_name},
                ],
                TemporaryPassword=temp_password,
                MessageAction="SUPPRESS",  # Não enviar email automático do Cognito
            )
            return response.get("User")
        except ClientError as e:
            logger.error(f"Erro ao criar usuário no Cognito: {e}")
            raise

    def disable_user(self, email: str) -> bool:
        """Desabilita usuário no Cognito."""
        try:
            self.client.admin_disable_user(
                UserPoolId=self.user_pool_id,
                Username=email,
            )
            return True
        except ClientError as e:
            logger.error(f"Erro ao desabilitar usuário no Cognito: {e}")
            return False

    def delete_user(self, email: str) -> bool:
        """Remove usuário do Cognito."""
        try:
            self.client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=email,
            )
            return True
        except ClientError as e:
            logger.error(f"Erro ao remover usuário do Cognito: {e}")
            return False

    def reset_password(self, email: str) -> bool:
        """Inicia fluxo de reset de senha."""
        try:
            self.client.admin_reset_user_password(
                UserPoolId=self.user_pool_id,
                Username=email,
            )
            return True
        except ClientError as e:
            logger.error(f"Erro ao resetar senha no Cognito: {e}")
            return False

    def add_user_to_group(self, email: str, group_name: str) -> bool:
        """Adiciona usuário a um grupo Cognito."""
        try:
            self.client.admin_add_user_to_group(
                UserPoolId=self.user_pool_id,
                Username=email,
                GroupName=group_name,
            )
            return True
        except ClientError as e:
            logger.error(f"Erro ao adicionar usuário ao grupo Cognito: {e}")
            return False

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verifica JWT do Cognito.
        Na prática, usa PyJWT com JWKs públicos do Cognito.
        """
        import urllib.request
        import json
        from jose import jwk, jwt
        from jose.utils import base64url_decode

        keys_url = (
            f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/"
            f"{self.user_pool_id}/.well-known/jwks.json"
        )

        try:
            with urllib.request.urlopen(keys_url) as response:
                keys = json.loads(response.read())["keys"]

            header = jwt.get_unverified_header(token)
            key = next((k for k in keys if k["kid"] == header["kid"]), None)
            if not key:
                return None

            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.app_client_id,
            )
            return claims

        except Exception as e:
            logger.warning(f"Token Cognito inválido: {e}")
            return None

    def create_user_pool_group(self, tenant_slug: str, role: str) -> bool:
        """Cria grupo no Cognito para um tenant/role."""
        group_name = f"{tenant_slug}_{role}"
        try:
            self.client.create_group(
                GroupName=group_name,
                UserPoolId=self.user_pool_id,
                Description=f"Grupo {role} do tenant {tenant_slug}",
            )
            return True
        except self.client.exceptions.GroupExistsException:
            return True  # Grupo já existe
        except ClientError as e:
            logger.error(f"Erro ao criar grupo Cognito: {e}")
            return False
