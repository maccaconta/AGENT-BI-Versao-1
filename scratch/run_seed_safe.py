import os
import django
import sys

# Garante que o diretório raiz está no path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local_fast')
django.setup()

from django.core.management import call_command

def run_seed():
    print("Iniciando seed de prompts via script direto...")
    try:
        call_command('seed_agent_prompts')
        print("Seed finalizado com sucesso!")
    except Exception as e:
        print(f"Erro ao executar seed: {e}")

if __name__ == "__main__":
    run_seed()
