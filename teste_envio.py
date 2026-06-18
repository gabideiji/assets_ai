import os
import requests
from dotenv import load_dotenv

load_dotenv()

url_snow = os.getenv("SERVICENOW_URL") + "?sysparm_display_value=true"
usuario_snow = os.getenv("SERVICENOW_USER")
senha_snow = os.getenv("SERVICENOW_PASSWORD")

nota = {
    "u_fornecedor": "Samsung Brasil",
    "u_cnpj_do_fornecedor": "11222333000144",
    "u_valor": "3500.50",
    "u_numero_da_nota": "NF-20202",
    "u_data_de_emissao": "17/06/2026",
    "u_data_de_vencimento": "17/07/2026",
    "u_centro_de_custo": "TI",
    "u_categoria_da_despesa": "Hardware",
    "u_descricao_resumida": "Compra de monitores para o setor",
    "u_nivel_de_confianca_da_ia": 95,
    "u_status_da_classificacao": "Sucesso na Extração",
    "u_status_da_aprovacao": "Aprovação da Gerência",
    "u_status_do_pagamento": "Aberto"
}

print(f"Enviando para {url_snow} com usuário {usuario_snow}")
resposta = requests.post(
    url_snow,
    auth=(usuario_snow, senha_snow),
    json=nota,
    headers={"Accept": "application/json"}
)

print(f"Status Code: {resposta.status_code}")
if resposta.status_code in [200, 201]:
    print("Sucesso! Resposta do ServiceNow:")
    print(resposta.json())
else:
    print("Erro! Detalhes:")
    print(resposta.text)
