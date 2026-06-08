import pandas as pd
import io
import urllib.request
import urllib.error
import streamlit as st

class InclusiónETL:
    def __init__(self):
        self.spreadsheet_id = "12PoHZr0BMJux4IxW7A3z7d0NdeLsXUkl5AmUO2xLEok"
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
            req = urllib.request.Request(self.url_excel, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                data_bytes = response.read()
            
            excel_file = io.BytesIO(data_bytes)
            
            # Cargamos el lector de Excel para inspeccionar los nombres reales de las pestañas
            xl = pd.ExcelFile(excel_file)
            nombres_reales = xl.sheet_names
            
            # Buscamos las pestañas limpiando los espacios en blanco invisibles automáticamente
            hoja_entrevistas = next((sheet for sheet in nombres_reales if sheet.strip() == "Entrevistas"), None)
            hoja_checklist = next((sheet for sheet in nombres_reales if sheet.strip() == "Checklist de puesto"), None)
            
            if not hoja_entrevistas or not hoja_checklist:
                st.error(f"[ETL ERROR] No se encontraron las pestañas esperadas de forma exacta. Pestañas reales en tu Google Sheets: {nombres_reales}")
                raise ValueError("Estructura de pestañas inválida.")
            
            # Leemos usando el nombre exacto con el que Google Sheets lo exportó
            df_e = pd.read_excel(excel_file, sheet_name=hoja_entrevistas)
            df_c = pd.read_excel(excel_file, sheet_name=hoja_checklist)

        except urllib.error.HTTPError as e:
            st.error(f"[ETL CRITICAL ERROR] Error HTTP {e.code}: No se pudo descargar el archivo de Google.")
            raise e
        except Exception as e:
            st.error(f"[ETL CRITICAL ERROR] Fallo en lectura de datos: {str(e)}")
            raise e

        # Normalización y procesamiento de datos
        df_e = self.limpiar_data(df_e)
        df_c = self.limpiar_data(df_c)

        df_e = df_e.loc[:, ~df_e.columns.duplicated()]
        df_c = df_c.loc[:, ~df_c.columns.duplicated()]

        columnas_comunes = [
            'Nombre del colaborador', 'Tipo de discapacidad', 'SubPer', 
            'Sede de tienda', 'Fecha de evaluación', 'Tipo de sexo', 'Puesto colaborador', 'Observaciones'
        ]
        
        cols_unicas_c = ['ID'] + [col for col in df_c.columns if col not in columnas_comunes and col != 'ID']
        df_checklist_unique = df_c[cols_unicas_c]
        df_checklist_unique = df_checklist_unique.loc[:, ~df_checklist_unique.columns.duplicated()]

        df_final = pd.merge(df_e, df_checklist_unique, on='ID', how='outer')

        if 'Fecha de evaluación' in df_final.columns:
            df_final['Fecha de evaluación'] = pd.to_datetime(df_final['Fecha de evaluación'], errors='coerce').dt.date

        return df_final