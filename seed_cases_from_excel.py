import pandas as pd
import json
import re
from core.database import supabase

# Mapeo de nombres de hojas a números de zona (int)
ZONE_MAPPING = {
    "hospital": 1,
    "internet": 2,
    "colegio": 3,
    "hogar": 4,
    "barrio": 5
}

def parse_rubric_text(text):
    """
    Parser inteligente para convertir bloques de texto en JSON de rúbrica.
    Ejemplo entrada: 'A. Texto de la opción (5 puntos) B. Texto... (3 puntos)'
    """
    if pd.isna(text): return []
    
    # Expresión regular para separar opciones A, B y C
    # Busca 'X. [texto] ([numero] puntos)'
    pattern = r'([A-C])\.\s*(.*?)\s*\((\d+)\s*puntos\)'
    matches = re.findall(pattern, text, re.DOTALL)
    
    rubric = []
    for letter, content, points in matches:
        rubric.append({
            "id": letter,
            "text": content.strip(),
            "points": int(points)
        })
    return rubric

def seed_from_excel(file_path):
    print(f"🚀 Iniciando carga desde: {file_path}")
    
    try:
        excel_data = pd.ExcelFile(file_path)
        all_cases = []

        for sheet_name in excel_data.sheet_names:
            normalized_name = sheet_name.lower().strip()
            if normalized_name not in ZONE_MAPPING:
                print(f"⚠️ Saltando hoja desconocida: {sheet_name}")
                continue
            
            zone_id = ZONE_MAPPING[normalized_name]
            print(f"📦 Procesando hoja '{sheet_name}' (Zona {zone_id})...")
            
            # Leer la hoja actual
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Usar los nombres de columna reales del usuario
            for _, row in df.iterrows():
                # Obtener descripción y el bloque de texto de la rúbrica
                desc = row.get('CASO', '')
                rubric_raw = row.get('RESPUESTA PUNTAJE', '')
                
                if pd.isna(desc) or desc == '': continue
                
                # Parsear el bloque de texto a JSON
                rubric = parse_rubric_text(rubric_raw)
                
                if not rubric:
                    print(f"   ⚠️ No se pudo extraer rúbrica para el caso en hoja {sheet_name}")
                    continue
                
                case_entry = {
                    "zone": zone_id,
                    "description": str(desc).strip(),
                    "rubric": rubric
                }
                all_cases.append(case_entry)

        # Inserción masiva en Supabase
        if all_cases:
            print(f"📤 Subiendo {len(all_cases)} casos a Supabase...")
            # Limpiar tabla opcional (Cuidado: esto borra todo)
            # supabase.table("cases").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            
            res = supabase.table("cases").insert(all_cases).execute()
            if res.data:
                print(f"✅ ¡Éxito! Se han cargado {len(res.data)} casos correctamente.")
            else:
                print(f"❌ Error al insertar en Supabase.")
        else:
            print("⚠️ No se encontraron casos válidos.")

    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    file_name = "cases.xlsx"
    seed_from_excel(file_name)
