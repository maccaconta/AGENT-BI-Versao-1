import os
import boto3
from decouple import config

def test_kb_connection():
    region = config("BEDROCK_REGION", default="us-east-1")
    kb_id = config("BEDROCK_KB_ID", default="")
    
    print(f"Testando conexao RAG na regiao: {region}")
    print(f"Knowledge Base ID alvo: {kb_id}")
    
    if not kb_id:
        print("Erro: BEDROCK_KB_ID esta vazio no .env")
        return
        
    try:
        # Tenta inicializar o cliente do agent-runtime
        client = boto3.client('bedrock-agent-runtime', region_name=region)
        
        # Faz uma chamada simples de retrieve
        print("Enviando query teste ('governance rules') para a base de conhecimento...")
        response = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={'text': 'governance rules'},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 1,
                }
            }
        )
        
        results = response.get("retrievalResults", [])
        if results:
            print("SUCESSO! O RAG funcionou e retornou fragmentos:")
            for item in results:
                print(f"-> Source: {item.get('location', {})}")
                print(f"-> Score: {item.get('score')}")
                print(f"-> Text snippet (preview): {item.get('content', {}).get('text', '')[:100]}...")
        else:
            print("SUCESSO! A conexao foi feita e o KB existe, porem retornou 0 fragmentos (Talvez o sync nao tenha terminado ou o HTML nao foi indexado direito).")
            
    except Exception as e:
        print("\n=== FALHA CAPTURADA ===")
        print(f"Tipo do Erro: {type(e).__name__}")
        print(f"Mensagem: {str(e)}")
        print("=======================")

if __name__ == "__main__":
    test_kb_connection()
