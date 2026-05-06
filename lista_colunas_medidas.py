import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

# carrega o .env
load_dotenv()

# acessa as variáveis
nome_projeto = os.getenv("NOME_PROJETO")

# =========================
# CONFIG
# =========================
BASE_PATH_SEMANTICMODEL = f"./{nome_projeto}.SemanticModel/definition"
BASE_PATH_REPORT = f"./{nome_projeto}.Report/definition"
TABLES_PATH = os.path.join(BASE_PATH_SEMANTICMODEL, "tables")
RELATIONSHIP_PATH = os.path.join(BASE_PATH_SEMANTICMODEL, "relationships.tmdl")
VISUAIS_PATH = os.path.join(BASE_PATH_REPORT, "pages")


# =========================
# FUNÇÃO 1: TABELAS
# =========================
def extrair_colunas_medidas(caminho_tabelas):
    campos = set()

    for arquivo in os.listdir(caminho_tabelas):
        if arquivo.endswith(".tmdl"):
            tabela_nome = arquivo.replace(".tmdl", "")
            caminho_arquivo = os.path.join(caminho_tabelas, arquivo)

            if "DateTable" in tabela_nome:
                continue

            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                conteudo = f.read()

            colunas = re.findall(
                r'^\s*column\s+(?:\'([^\']+)\'|"([^"]+)"|([^\s]+))',
                conteudo,
                re.MULTILINE
            )
            colunas = [c1 or c2 or c3 for c1, c2, c3 in colunas]

            medidas = re.findall(
                r'^\s*measure\s+(?:\'([^\']+)\'|"([^"]+)"|([^\s=]+))',
                conteudo,
                re.MULTILINE
            )
            medidas = [m1 or m2 or m3 for m1, m2, m3 in medidas]

            for col in colunas:
                campos.add(f"{tabela_nome}.{col.strip()}")

            for med in medidas:
                campos.add(f"{tabela_nome}.{med.strip()}")

    return sorted(campos)


# =========================
# FUNÇÃO 2: RELACIONAMENTOS
# =========================
def extrair_colunas_relacionamento(caminho_relationship):
    colunas_total = []

    if not os.path.exists(caminho_relationship):
        print("⚠️ relationships.tmdl não encontrado.")
        return []

    with open(caminho_relationship, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    for linha in linhas:
        colunas = re.findall(
            r'^\s*(?:fromColumn|toColumn):\s+(.+)',
            linha
        )

        for col in colunas:
            # remove espaços extras + aspas externas
            col_limpa = col.replace("'","")
            colunas_total.append(col_limpa)

    return sorted(list(set(colunas_total)))


# =========================
# FUNÇÃO 3: VISUAIS
# =========================
def extrair_uso_visuais(caminho_pages):
    campos = set()

    pattern_entity = re.compile(r'"entity"\s*:\s*"([^"]+)"', re.IGNORECASE)
    pattern_property = re.compile(r'"property"\s*:\s*"([^"]+)"', re.IGNORECASE)

    for root, dirs, files in os.walk(caminho_pages):
        for file in files:
            if file.endswith(".json"):
                caminho_arquivo = os.path.join(root, file)

                try:
                    with open(caminho_arquivo, "r", encoding="utf-8") as f:
                        conteudo = json.load(f)
                except:
                    continue

                texto = json.dumps(conteudo, ensure_ascii=False)

                entities = pattern_entity.findall(texto)
                properties = pattern_property.findall(texto)

                # Combina por posição
                for ent, prop in zip(entities, properties):
                    if ent and prop:
                        campo = f"{ent.strip()}.{prop.strip()}"
                        campo = campo.replace("'", "")
                        campos.add(campo)

    return sorted(list(campos))

# =========================
# EXTRAIR MEDIDAS USADAS EM MEDIDAS
# =========================
def extrair_dependencia_medidas(caminho_tabelas):

    arquivos = [f for f in os.listdir(caminho_tabelas) if "Medidas" in f]
    medidas_formatadas = []
    cols = []

    for arquivo in arquivos:

        caminho_arquivo = os.path.join(caminho_tabelas, arquivo)

        if not os.path.exists(caminho_arquivo):
            continue

        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            conteudo = f.read()

        # =========================
        # CAPTURA MEDIDAS
        # =========================
        matches = re.findall(
            r'^\s*measure\s+((?:\'[^\']+\'|\"[^\"]+\"|[^\s=]+))\s*=\s*(.*?)(?=^\s*(measure|column)|\Z)',
            conteudo,
            re.MULTILINE | re.DOTALL
        )

        for nome, dax, _ in matches:
            
            # colunas
            colunas = re.findall(r"(?:'([^']+)'|(\w+))\[([^\]]+)\]", dax)

            columns_final = []

            for t1, t2, coluna in colunas:
                tabela = t1 or t2
                columns_final.append((tabela, coluna))
            

            for tabela, coluna in columns_final:
                coluna_formatada = f"{tabela}.{coluna}"
                cols.append(coluna_formatada)

            # medidas
            medidas = re.findall(r'(?<!\w)\[([^\]]+)\]', dax)


            for item in medidas:
                medida_formatada = arquivo + "." + item
                medidas_formatadas.append(medida_formatada)

    result = cols + medidas_formatadas
    result = sorted(set(result))

    return result

def extract_sortby_columns(tables_path):

    used_columns = set()

    for file in Path(tables_path).rglob("*.tmdl"):

        table_name = file.stem

        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

        # pega colunas com sortByColumn
        pattern = r"sortByColumn:\s*'?([^'\n\r]+)'?"

        matches = re.findall(pattern, content, re.S)

        for sort_col in matches:
            # coluna usada como ordenação
            used_columns.add(f"{table_name}.{sort_col}")

    return used_columns

def extrair_dependencia_colunas_calculadas(caminho_tabelas):
    usados = set()

    for arquivo in os.listdir(caminho_tabelas):
        if not arquivo.endswith(".tmdl"):
            continue

        tabela = arquivo.replace(".tmdl", "")
        caminho_arquivo = os.path.join(caminho_tabelas, arquivo)

        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            conteudo = f.read()

        # pega colunas com expressão DAX
        matches = re.findall(
            r'^\s*column\s+(?:\'[^\']+\'|"[^"]+"|[^\s]+)\s*=\s*(.*?)(?=^\s*(column|measure)|\Z)',
            conteudo,
            re.MULTILINE | re.DOTALL
        )

        for dax, _ in matches:

            # dependência de colunas
            for tabela_ref, coluna in re.findall(r'(\w+)\[([^\]]+)\]', dax):
                usados.add(f"{tabela_ref}.{coluna}")

            # dependência de medidas
            for medida in re.findall(r'(?<!\w)\[([^\]]+)\]', dax):
                usados.add(f"{tabela}.{medida}")

    return usados

# =========================
# SALVAR JSON
# =========================
def salvar_json(dados, nome_arquivo):
    def converter(obj):
        if isinstance(obj, set):
            return sorted(obj)  # 👈 melhor que list
        return obj

    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False, default=converter)


# =========================
# MAIN
# =========================
if __name__ == "__main__":

    print("🔄 Lendo tabelas...")
    dados_tabelas = extrair_colunas_medidas(TABLES_PATH)
    qtd_dados_tabelas = len(set(dados_tabelas))

    print("🔄 Lendo relacionamentos...")
    colunas_relacionamento = extrair_colunas_relacionamento(RELATIONSHIP_PATH)
    qtd_colunas_relacionamento = len(set(colunas_relacionamento))

    print("🔄 Lendo Visuais...")
    dados_visuais = extrair_uso_visuais(VISUAIS_PATH)
    qtd_dados_visuais = len(set(dados_visuais))

    print("🔄 Lendo medidas...")
    dados_medidas = extrair_dependencia_medidas(TABLES_PATH)
    qtd_dados_medidas = len(set(dados_medidas))

    print("🔄 Lendo colunas usadas em sort by...")
    sort_columns = extract_sortby_columns(TABLES_PATH)
    qtd_sort_columns = len(set(sort_columns))

    print("🔄 Lendo colunas usadas em colunas calculadas...")
    calculated_columns = extrair_dependencia_colunas_calculadas(TABLES_PATH)
    qtd_calculated_columns =  len(set(calculated_columns))

    set_modelo = set(dados_tabelas)
    set_rel = set(colunas_relacionamento)
    set_visuais = set(dados_visuais)
    set_medidas = set(dados_medidas)
    set_sort = set(sort_columns)

    usados = set_rel.union(set_visuais).union(set_medidas).union(set_sort).union(calculated_columns)

    # mapa lowercase → original
    map_modelo = {c.lower(): c for c in set_modelo}
    map_usados = {c.lower(): c for c in usados}

    nao_usados_keys = set(map_modelo.keys()) - set(map_usados.keys())

    # recupera nomes originais
    nao_usados = [map_modelo[k] for k in nao_usados_keys]
    qtd_nao_usados = len(set(nao_usados))

    salvar_json(dados_tabelas, "./output/colunas_modelo.json")
    salvar_json(colunas_relacionamento, "./output/colunas_relacionadas.json")
    salvar_json(dados_visuais, "./output/colunas_visuais.json")
    salvar_json(dados_medidas, "./output/medidas_medidas.json")
    salvar_json(sort_columns, "./output/sort_columns.json")
    salvar_json(calculated_columns, "./output/calculated_columns.json")
    salvar_json(nao_usados, "./output/nao_usados.json")
    salvar_json(usados, "./output/usados.json")

    # =========================
    # PRINT DEBUG
    # =========================
    print("\n📊 RESUMO")
    print(f"Total colunas no modelo: {qtd_dados_tabelas}")
    print(f"Colunas em relacionamento: {qtd_colunas_relacionamento}")
    print(f"Colunas em visuais: {qtd_dados_visuais}")
    print(f"Medidas usadas em medidas: {qtd_dados_medidas}")
    print(f"Medidas usadas em sort by: {qtd_sort_columns}")
    print(f"Colunas usadas em colunas calculadas: {qtd_calculated_columns}")
    print(f"Colunas não usadas: {qtd_nao_usados}")
