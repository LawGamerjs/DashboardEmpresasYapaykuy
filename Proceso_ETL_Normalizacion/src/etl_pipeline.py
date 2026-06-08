import pandas as pd
import io
import urllib.request
import urllib.error
import streamlit as st

class InclusiónETL:
    def __init__(self):
        # ID verificado de tu documento de Google Sheets
        self.spreadsheet_id = "12PoHZr0BMJux4IxW7A3z7d0NdeLsXUkl5AmUO2xLEok"
        
        # URL para exportar todo el libro completo en formato Excel (.xlsx)
        self.url_excel = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/export?format=xlsx"
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def limpiar_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [str(col).strip() for col in df.columns]
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        if 'ID' in df.columns:
            df['ID'] = df['ID'].astype(str).str.split('.').str[0].str.zfill(5)
        return df

    def ejecutar_pipeline_en_vivo(self) -> pd.DataFrame:
        try:
            # 1. Descargamos el archivo Excel completo en un stream de bytes
            req = urllib.request.Request(self.url_excel, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                data_bytes = response.read()
            
            # 2. Cargamos el archivo en memoria usando un buffer intermedio
            excel_file = io.BytesIO(data_bytes)
            
            # 3. Leemos cada pestaña utilizando su nombre literal exacto de tu Google Sheets
            df_e = pd.read_excel(excel_file, sheet_name="Entrevistas")
            df_c = pd.read_excel(excel_file, sheet_name="Checklist de puesto")

        except urllib.error.HTTPError as e:
            st.error(f"[ETL CRITICAL ERROR] Error HTTP {e.code}: No se pudo descargar el libro Excel de Google.")
            raise e
        except Exception as e:
            st.error(f"[ETL CRITICAL ERROR] Asegúrate de que los nombres de las pestañas sean exactamente 'Entrevistas' y 'Checklist de puesto'. Error: {str(e)}")
            raise e

        # Normalización y limpieza de estructuras
        df_e = self.limpiar_data(df_e)
        df_c = self.limpiar_data(df_c)

        df_e = df_e.loc[:, ~df_e.columns.duplicated()]
        df_c = df_c.loc[:, ~df_c.columns.duplicated()]

        columnas_comunes = [
            'Nombre del colaborador', 'Tipo de discapacidad', 'SubPer', 
            'Sede de tienda', 'Fecha de evaluación', 'Tipo de sexo', 'Puesto colaborador', 'Observaciones'
        ]
        
        # Aislamiento de métricas únicas de la segunda pestaña para evitar duplicaciones
        cols_unicas_c = ['ID'] + [col for col in df_c.columns if col not in columnas_comunes and col != 'ID']
        df_checklist_unique = df_c[cols_unicas_c]
        df_checklist_unique = df_checklist_unique.loc[:, ~df_checklist_unique.columns.duplicated()]

        # Consolidación final por ID de colaborador
        df_final = pd.merge(df_e, df_checklist_unique, on='ID', how='outer')

        if 'Fecha de evaluación' in df_final.columns:
            df_final['Fecha de evaluación'] = pd.to_datetime(df_final['Fecha de evaluación'], errors='coerce').dt.date

        return df_final