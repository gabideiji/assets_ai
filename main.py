import os
import json
import shutil
import requests
import PyPDF2
from PIL import Image
from google import genai
from dotenv import load_dotenv

load_dotenv()

url_snow = os.getenv("SERVICENOW_URL")
usuario_snow = os.getenv("SERVICENOW_USER")
senha_snow = os.getenv("SERVICENOW_PASSWORD")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_REGRAS = """Aja como um Agente de Triagem Financeira.

Sua missão é ler o conteúdo de notas fiscais e extrair as informações essenciais para o sistema da empresa. Você deve classificar o Centro de Custo com base nos itens comprados usando a seguinte regra:

Se tiver computadores, mouses, teclados, monitores, licenças de software ou cabos -> TI
Se tiver papel, caneta, material de limpeza ou café -> Operações
Se tiver cursos, palestras ou onboarding -> RH

Regra de Ouro: Você deve responder ÚNICA e EXCLUSIVAMENTE com um JSON válido, sem nenhum texto antes ou depois. Sem crases, sem blocos de código Markdown. Apenas o JSON puro.

Se houver mais de uma nota fiscal no arquivo (ex: um XML com várias notas), você DEVE retornar uma LISTA de objetos JSON. Se houver apenas uma nota, você também DEVE retornar uma LISTA contendo um único objeto JSON.

Você deve incluir uma chave "nivel_confianca" analisando a clareza da nota fiscal e dando uma nota de 0 a 100.

Use as chaves exatas abaixo para cada nota:
[
  {
    "u_fornecedor": "[Nome do emitente]",
    "u_cnpj_do_fornecedor": "[CNPJ presente no documento (se houver apenas um, extraia ele), apenas números]",
    "u_valor": "[Valor total numérico com ponto, ex: 1550.80]",
    "u_numero_da_nota": "[Número da nota fiscal/fatura]",
    "u_data_de_emissao": "[Data de emissão encontrada]",
    "u_data_de_vencimento": "[Data de vencimento do pagamento]",
    "u_centro_de_custo": "[Sua classificação baseada na regra: TI, Operações ou RH]",
    "u_categoria_da_despesa": "[Tipo de item, ex: Hardware, Licenças, Material de Escritório, Treinamento]",
    "u_descricao_resumida": "[Uma frase resumindo o que foi comprado]",
    "u_nivel_de_confianca_da_ia": [Número inteiro de 0 a 100 avaliando a legibilidade do arquivo]
  }
]

Aqui está o conteúdo da Nota Fiscal que você deve analisar agora:
"""

def extrair_dados_texto(texto):
    resposta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROMPT_REGRAS + f'\n"""{texto}"""'
    )
    return resposta.text.strip()

def extrair_dados_imagem(caminho):
    with Image.open(caminho) as imagem:
        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[PROMPT_REGRAS, imagem]
        )
    return resposta.text.strip()

if __name__ == "__main__":
    pasta_entrada = os.path.join(os.path.dirname(__file__), "dados_entrada")
    pasta_processados = os.path.join(pasta_entrada, "processados")
    
    os.makedirs(pasta_entrada, exist_ok=True)
    os.makedirs(pasta_processados, exist_ok=True)

    arquivos = [f for f in os.listdir(pasta_entrada) if os.path.isfile(os.path.join(pasta_entrada, f))]

    for nome_arquivo in arquivos:
        caminho_arquivo = os.path.join(pasta_entrada, nome_arquivo)
        extensao = os.path.splitext(nome_arquivo)[1].lower()
        json_ia = None

        if extensao == ".xml":
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                conteudo_xml = f.read()
            json_ia = extrair_dados_texto(conteudo_xml)
            
        elif extensao == ".pdf":
            texto_pdf = ""
            with open(caminho_arquivo, "rb") as f:
                leitor = PyPDF2.PdfReader(f)
                for pagina in leitor.pages:
                    txt = pagina.extract_text()
                    if txt:
                        texto_pdf += txt + "\n"
            if texto_pdf.strip():
                json_ia = extrair_dados_texto(texto_pdf)
                
        elif extensao in [".png", ".jpg", ".jpeg"]:
            json_ia = extrair_dados_imagem(caminho_arquivo)
            
        else:
            continue

        if not json_ia:
            continue

        try:
            json_limpo = json_ia.replace('```json', '').replace('```', '').strip()
            dados_nota = json.loads(json_limpo)
            lista_notas = dados_nota if isinstance(dados_nota, list) else [dados_nota]
            
            sucesso_total = True
            for nota in lista_notas:
                print(f"JSON EXTRAIDO DA IA: {nota}")
                confianca = int(nota.get("u_nivel_de_confianca_da_ia", 0))
                if confianca >= 80:
                    nota["u_status_da_classificacao"] = "Classificação Automática"
                else:
                    nota["u_status_da_classificacao"] = "Revisão Manual"
                
                resposta = requests.post(
                    url_snow,
                    auth=(usuario_snow, senha_snow),
                    json=nota,
                    headers={"Accept": "application/json"}
                )
                if resposta.status_code != 201:
                    print(f"Erro no ServiceNow para {nome_arquivo}: {resposta.text}")
                    sucesso_total = False
                else:
                    print(f"ServiceNow Response: {resposta.text}")
            
            if sucesso_total:
                print(f"Arquivo {nome_arquivo} processado com sucesso!")
                destino = os.path.join(pasta_processados, nome_arquivo)
                if os.path.exists(destino):
                    os.remove(destino)
                shutil.move(caminho_arquivo, destino)
                
        except Exception as e:
            print(f"Erro ao processar JSON para {nome_arquivo}: {e}")