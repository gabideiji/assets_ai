import os
from dotenv import load_dotenv

def consultar_service_now(numero_nota: str) -> dict:
    print(f"[MOCK] Consultando ServiceNow para a nota: {numero_nota}")

    dados_fake = {
        "numero_nota": numero_nota,
        "fornecedor": "Papelaria Central Ltda.",
        "cnpj": "12.345.678/0001-99",
        "valor_total": 1250.75,
        "itens": [
            {"descricao": "Resma de papel A4", "quantidade": 50, "valor_unitario": 22.50},
            {"descricao": "Caneta esferográfica azul", "quantidade": 100, "valor_unitario": 1.25},
        ],
        "data_emissao": "2026-06-15",
        "status": "pendente_classificacao",
    }

    print(f"[MOCK] Dados da nota {numero_nota} retornados com sucesso!")
    return dados_fake

def classificar_nota(dados_nota: dict) -> dict:
    print(f"[MOCK] Classificando a nota {dados_nota['numero_nota']}...")

    classificacao = {
        "numero_nota": dados_nota["numero_nota"],
        "categoria": "Material de Escritório",
        "confianca": "100% (valor fixo — mock)",
        "justificativa": "Classificação simulada para teste. O LLM ainda não está conectado.",
    }

    print(f"[MOCK] Nota classificada como: {classificacao['categoria']}")
    return classificacao

def main():
    load_dotenv()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    servicenow_url = os.getenv("SERVICENOW_URL")

    print("AGENTE AUTÔNOMO — Classificador de Notas Fiscais")

    if gemini_api_key:
        chave_mascarada = "****" + gemini_api_key[-4:]
        print(f"GEMINI_API_KEY carregada: {chave_mascarada}")
    else:
        print("GEMINI_API_KEY não encontrada no .env!")

    if servicenow_url:
        print(f"SERVICENOW_URL carregada: {servicenow_url}")
    else:
        print("SERVICENOW_URL não encontrada no .env!")

    numero_nota_exemplo = "NF-2026-001234"
    dados_nota = consultar_service_now(numero_nota_exemplo)

    resultado = classificar_nota(dados_nota)

    print("RESULTADO FINAL")
    print(f"  Nota:           {resultado['numero_nota']}")
    print(f"  Fornecedor:     {dados_nota['fornecedor']}")
    print(f"  Valor Total:    R$ {dados_nota['valor_total']:.2f}")
    print(f"  Categoria:      {resultado['categoria']}")
    print(f"  Confiança:      {resultado['confianca']}")
    print(f"  Justificativa:  {resultado['justificativa']}")
    print("Agente finalizado com sucesso!")

if __name__ == "__main__":
    main()
