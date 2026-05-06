import os
import json
import re
from dotenv import load_dotenv

# carrega o .env
load_dotenv()

# acessa as variáveis
nome_projeto = os.getenv("NOME_PROJETO")

# =========================
# CONFIG
# =========================
TABELAS_PATH = f"./{nome_projeto}.SemanticModel/definition/tables"
NAO_USADOS_JSON = "./output/nao_usados.json"

# =========================
# LOAD JSON
# =========================
with open(NAO_USADOS_JSON, "r", encoding="utf-8") as f:
    nao_usados = json.load(f)

# =========================
# ORGANIZAR POR TABELA
# =========================
por_tabela = {}

for item in nao_usados:
    if "." not in item:
        continue

    tabela, campo = item.split(".", 1)

    tabela = tabela.strip()
    campo = campo.strip().replace("'", "").replace('"', '')

    if tabela not in por_tabela:
        por_tabela[tabela] = {"columns": [], "measures": []}

    if tabela.lower() == "_medidas":
        por_tabela[tabela]["measures"].append(campo)
    else:
        por_tabela[tabela]["columns"].append(campo)

# =========================
# REMOÇÃO EM BLOCO
# =========================
def remover_blocos(conteudo, colunas, medidas):
    
    # 🔹 Remove colunas
    for col in colunas:
        pattern_col = re.compile(
            rf"\bcolumn\s+(?:'{re.escape(col)}'|\"{re.escape(col)}\"|{re.escape(col)})\s*(?:=|\r?\n).*?(?=\n\s*(column|measure|partition)\s+|\Z)",
            re.DOTALL | re.IGNORECASE
        )
        conteudo = pattern_col.sub("", conteudo)
        #print(re.escape(col))
        #print(conteudo)


    # 🔹 Remove medidas
    for med in medidas:
        pattern_med = re.compile(
            rf'\bmeasure\s+{re.escape(med)}\b.*?(?=\n\s*measure\s+|\Z)',
            re.DOTALL | re.IGNORECASE
        )
        conteudo = pattern_med.sub("", conteudo)

    return conteudo

# =========================
# PROCESSAR TABELAS
# =========================
for tabela, tipos in por_tabela.items():
    caminho_arquivo = os.path.join(TABELAS_PATH, f"{tabela}.tmdl")

    if not os.path.exists(caminho_arquivo):
        print(f"⚠️ Arquivo não encontrado: {tabela}.tmdl")
        continue

    # 🔥 Lê UMA VEZ
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        conteudo = f.read()

    conteudo_original = conteudo

    # 🔥 Remove tudo em memória
    conteudo = remover_blocos(
        conteudo,
        tipos["columns"],
        tipos["measures"]
    )


    with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo)
    
    print(f"✅ Atualizado: {tabela}.tmdl")