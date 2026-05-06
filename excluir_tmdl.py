import json
import os
import re
from collections import defaultdict
from dotenv import load_dotenv

# carrega o .env
load_dotenv()

# acessa as variáveis
nome_projeto = os.getenv("NOME_PROJETO")

# ==========================
# CONFIG
# ==========================
INPUT_JSON = "./output/usados.json"
TABLES_PATH = f"./{nome_projeto}.SemanticModel/definition/tables"
OUTPUT_FILE = "./output/queries.json"

class PrettyJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        result = super().encode(obj)
        return result.replace("\\n", "\n")

# ==========================
# LOAD COLUNAS
# ==========================
def load_columns():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    tables = defaultdict(list)

    for full_name in data:
        if "." not in full_name:
            continue

        table, column = full_name.split(".", 1)
        tables[table].append(column)

    for table in tables:
        tables[table] = sorted(set(tables[table]))

    return tables

# ==========================
# EXTRAIR M DO TMDL
# ==========================
def extract_m_from_tmdl(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # pega o bloco da query M
    match = re.search(
        r'source\s*=\s*(let.*?in\s+[^\r\n]+)',
        content,
        re.DOTALL
    )

    if not match:
        return None

    # remove escapes do JSON
    m_code = match.group(1).encode().decode("unicode_escape")

    print(m_code)

    return m_code

# ==========================
# INJETAR SELECTCOLUMNS
# ==========================
def inject_select_columns(m_code, columns):

    if "__AutoSelectColumns" in m_code:
        return m_code  # já tratado

    colunas_formatadas = ", ".join([f'"{c}"' for c in columns])

    # pega o último step (in ...)
    match = re.search(r'in\s+([^\r\n]+)', m_code, re.IGNORECASE)

    if not match:
        return m_code

    final_step = match.group(1).strip()

    # remove o "in ..."
    m_sem_in = re.sub(
        r'in\s+[^\r\n]+',
        '',
        m_code,
        flags=re.IGNORECASE
    ).rstrip()

    # adiciona novo step
    new_m = f"""
{m_sem_in},
    #"__AutoSelectColumns" = Table.SelectColumns(
        {final_step},
        {{{colunas_formatadas}}}
    )
in
    #"__AutoSelectColumns"
"""

    return new_m.strip()

# ==========================
# PROCESSAR TABELAS
# ==========================
def process_tables():

    tables = load_columns()
    output = {}

    for file in os.listdir(TABLES_PATH):
        if not file.endswith(".tmdl"):
            continue

        table_name = file.replace(".tmdl", "")

        if table_name not in tables:
            continue

        file_path = os.path.join(TABLES_PATH, file)

        m_code = extract_m_from_tmdl(file_path)

        if not m_code:
            print(f"[WARN] Sem M: {table_name}")
            continue

        new_m = inject_select_columns(m_code, tables[table_name])
        new_m = new_m.replace("\t", "    ")

        output[table_name] = {
            "query": new_m
        }

        print(f"[OK] {table_name}")

    return output

# ==========================
# EXECUÇÃO
# ==========================
def main():

    result = process_tables()

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=4, ensure_ascii=False, cls=PrettyJSONEncoder))

    print(f"\n[OK] JSON gerado: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()