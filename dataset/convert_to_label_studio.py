import pandas as pd
import json

# Carrega o CSV
df = pd.read_csv("tcern_decisoes_2024_completo.csv")

# Coluna com o texto que será rotulado
TEXT_COLUMN = "texto_acordao"  # ou "conclusao", dependendo do seu CSV

# Lista para armazenar as tarefas
tasks = []

for _, row in df.iterrows():
    text = row[TEXT_COLUMN]
    if pd.notna(text):
        tasks.append({
            "data": {
                "text": text.strip()
            }
        })

# Salva como lista JSON
with open("tcern_decisoes_2024_labelstudio.json", "w", encoding="utf-8") as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

