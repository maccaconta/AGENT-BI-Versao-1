import os
import django
import json
import sys

# Move to the root directory
os.chdir(r'c:\Users\mmaccafe\Documents\Agent-BI')
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local_fast')
django.setup()

from apps.governance.models import AgentSystemPrompt

def export_prompts():
    keys = ['supervisor_agent', 'nl2sql_agent']
    results = {}
    for key in keys:
        try:
            p = AgentSystemPrompt.objects.get(agent_key=key)
            results[key] = p.content
        except AgentSystemPrompt.DoesNotExist:
            results[key] = "NOT_FOUND"
    
    print("--- JSON_START ---")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("--- JSON_END ---")

if __name__ == "__main__":
    export_prompts()
