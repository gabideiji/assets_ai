import os
import json
import shutil
import requests
import PyPDF2
from PIL import Image
from google import genai
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Security, UploadFile, File
from fastapi.security.api_key import APIKeyHeader
import tempfile

load_dotenv()

url_snow = os.getenv("SERVICENOW_URL")
usuario_snow = os.getenv("SERVICENOW_USER")
senha_snow = os.getenv("SERVICENOW_PASSWORD")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
API_KEY = os.getenv("API_KEY_SECRETA", "chave-super-segura-123")

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

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

async def verificar_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    return api_key

@app.post("/api/v1/processar-nota")
async def processar_nota(arquivo: UploadFile = File(...), api_key: str = Depends(verificar_api_key)):
    extensao = os.path.splitext(arquivo.filename)[1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as tmp:
        conteudo = await arquivo.read()
        tmp.write(conteudo)
        caminho_arquivo = tmp.name

    json_ia = None
    try:
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
            raise HTTPException(status_code=400, detail="Formato de arquivo não suportado")

        if not json_ia:
            raise HTTPException(status_code=500, detail="IA não retornou dados úteis")

        json_limpo = json_ia.replace('```json', '').replace('```', '').strip()
        dados_nota = json.loads(json_limpo)
        lista_notas = dados_nota if isinstance(dados_nota, list) else [dados_nota]
        
        resultados = []
        for nota in lista_notas:
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
            
            if resposta.status_code == 201:
                resultados.append({"nota": nota, "status": "criado", "snow_response": resposta.json()})
            else:
                resultados.append({"nota": nota, "status": "erro", "detalhe": resposta.text})
                
        return {"status": "sucesso", "arquivo": arquivo.filename, "resultados": resultados}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
