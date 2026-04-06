from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.ai_engine.services.bedrock_service import BedrockService


class BedrockServiceRuntimeModeTests(SimpleTestCase):
    @override_settings(
        BEDROCK_REGION="us-east-1",
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0",
        BEDROCK_MAX_TOKENS=1024,
        USE_BEDROCK_AGENT_RUNTIME=True,
        BEDROCK_AGENT_ID="agent-123",
        BEDROCK_AGENT_ALIAS_ID="alias-123",
    )
    def test_invoke_with_json_output_uses_agent_runtime_when_enabled(self):
        service = BedrockService()
        with patch.object(service, "invoke_agent", return_value='{"ok": true}') as invoke_agent_mock:
            with patch.object(service, "invoke") as invoke_model_mock:
                payload = service.invoke_with_json_output(
                    system_prompt="sys",
                    user_message="user",
                    temperature=0.2,
                )

        self.assertEqual(payload["ok"], True)
        invoke_agent_mock.assert_called_once()
        invoke_model_mock.assert_not_called()

    @override_settings(
        BEDROCK_REGION="us-east-1",
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0",
        BEDROCK_MAX_TOKENS=1024,
        USE_BEDROCK_AGENT_RUNTIME=True,
        BEDROCK_AGENT_ID="agent-123",
        BEDROCK_AGENT_ALIAS_ID="alias-123",
    )
    def test_invoke_with_json_output_fallbacks_to_invoke_model_when_agent_returns_non_json(self):
        service = BedrockService()
        with patch.object(
            service,
            "invoke_agent",
            return_value="Session is terminated as endSession is true",
        ) as invoke_agent_mock:
            with patch.object(service, "invoke", return_value='{"ok": true}') as invoke_model_mock:
                payload = service.invoke_with_json_output(
                    system_prompt="sys",
                    user_message="user",
                    temperature=0.2,
                )

        self.assertEqual(payload["ok"], True)
        invoke_agent_mock.assert_called_once()
        invoke_model_mock.assert_called_once()

    @override_settings(
        BEDROCK_REGION="us-east-1",
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0",
        BEDROCK_MAX_TOKENS=1024,
        USE_BEDROCK_AGENT_RUNTIME=False,
    )
    def test_invoke_with_json_output_uses_model_runtime_when_agent_disabled(self):
        service = BedrockService()
        with patch.object(service, "invoke", return_value='{"ok": true}') as invoke_model_mock:
            with patch.object(service, "invoke_agent") as invoke_agent_mock:
                payload = service.invoke_with_json_output(
                    system_prompt="sys",
                    user_message="user",
                    temperature=0.2,
                )

        self.assertEqual(payload["ok"], True)
        invoke_model_mock.assert_called_once()
        invoke_agent_mock.assert_not_called()

    @override_settings(
        BEDROCK_REGION="us-east-1",
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0",
        BEDROCK_MAX_TOKENS=1024,
        BEDROCK_AGENT_SESSION_PREFIX="agent-bi",
    )
    def test_build_agent_session_id_keeps_safe_pattern(self):
        service = BedrockService()
        session_id = service._build_agent_session_id()

        self.assertTrue(session_id.startswith("agent-bi-"))
        self.assertLessEqual(len(session_id), 100)

    @override_settings(
        BEDROCK_REGION="us-east-1",
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0",
        BEDROCK_MAX_TOKENS=1024,
    )
    def test_collect_agent_completion_text_from_chunks(self):
        service = BedrockService()
        response = {
            "completion": [
                {"chunk": {"bytes": b"{\"a\": "}},
                {"chunk": {"bytes": b"1}"}},
            ]
        }

        text = service._collect_agent_completion_text(response)
        self.assertEqual(text, '{"a": 1}')

    @override_settings(
        BEDROCK_REGION="us-east-1",
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="amazon.nova-pro-v1:0",
        BEDROCK_MAX_TOKENS=1024,
        USE_BEDROCK_AGENT_RUNTIME=False,
    )
    def test_invoke_with_json_output_uses_converse_for_nova_models(self):
        service = BedrockService()
        with patch.object(service, "invoke_converse", return_value='{"ok": true}') as invoke_converse_mock:
            with patch.object(service, "invoke") as invoke_model_mock:
                payload = service.invoke_with_json_output(
                    system_prompt="sys",
                    user_message="user",
                    temperature=0.2,
                )

        self.assertEqual(payload["ok"], True)
        invoke_converse_mock.assert_called_once()
        invoke_model_mock.assert_not_called()
        self.assertEqual(service.last_invoke_metadata.get("model_runtime_api"), "converse")
