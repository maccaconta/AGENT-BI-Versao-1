import psycopg2
import os
from pathlib import Path
from decouple import config

def create_table():
    print("Iniciando criação manual da tabela de governança...")
    try:
        # Puxa credenciais do .env ou usa defaults
        conn = psycopg2.connect(
            dbname=config("DB_NAME", default="agent_bi_db"),
            user=config("DB_USER", default="agent_bi_user"),
            password=config("DB_PASSWORD", default="agent_bi_pass"),
            host=config("DB_HOST", default="localhost"),
            port=config("DB_PORT", default="5432")
        )
        cursor = conn.cursor()
        
        sql = """
        CREATE TABLE IF NOT EXISTS governance_system_prompts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL,
            persona_title varchar(255) DEFAULT 'Analista Financeiro Sênior',
            persona_description text DEFAULT 'Você é um analista financeiro sênior especializado em identificar relações ocultas em dados e gerar insights estratégicos.',
            style_guide jsonb DEFAULT '{}',
            compliance_rules text,
            language varchar(10) DEFAULT 'pt-BR',
            is_active boolean DEFAULT true,
            created_by_id int,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
        cursor.execute(sql)
        conn.commit()
        print("Tabela 'governance_system_prompts' criada com sucesso!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar tabela: {e}")

if __name__ == "__main__":
    create_table()
