import pandas as pd
import io
import urllib.request
import urllib.error
import streamlit as st

class InclusiónETL:
    def __init__(self):
        # ID verificado del documento editable compartido
        self.spreadsheet_id = "12PoHZr0BMJux4IxW7A3z7d0NdeLsXUkl5AmUO2xLEok"
        
        # URLs de exportación directa utilizando los GIDs reales de datos
        self.url_entrevistas = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/export?format=csv&gid=0"
        self.url_checklist = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/export?format=csv&gid=111429532"
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def descargar_csv(self, url: str, nombre_hoja: str) -> pd.DataFrame:
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                data_bytes = response.read()
                df = pd.read_csv(io.StringIO(data_bytes.decode('utf-8')))
                return df
        except urllib.error.HTTPError as e:
            cuerpo_error = e.read().decode('utf-8', errors='ignore') if hasattr(e, 'read') else "Sin cuerpo"
            st.error(f"[ETL ERROR] Fallo en {nombre_hoja} (Código: {e.code}). Verifica que el acceso general esté en 'Cualquier persona con el enlace'.")
            raise e
        except Exception as e:
            st.error(f"[ETL ERROR] Fallo inesperado en {nombre_hoja}: {str(e)}")
            raise e

    def limpiar_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [str(col).strip() for col in df.columns]
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        if 'ID' in df.columns:
            df['ID'] = df['ID'].astype(str).str.split('.').str[0].str.zfill(5)
        return df

    def ejecutar_pipeline_en_vivo(self) -> pd.DataFrame:
        # Descarga de los conjuntos de datos independientes
        df_e = self.descargar_csv(self.url_entrevistas, "Entrevistas (gid=0)")
        df_c = self.descargar_csv(self.url_checklist, "Checklist (gid=111429532)")

        # Normalización y limpieza de estructuras
        df_e = self.limpiar_data(df_e)
        df_c = self.limpiar_data(df_c)

        df_e = df_e.loc[:, ~df_e.columns.duplicated()]
        df_c = df_c.loc[:, ~df_c.columns.duplicated()]

        columnas_comunes = [
            'Nombre del colaborador', 'Tipo de discapacidad', 'SubPer', 
            'Sede de tienda', 'Fecha de evaluación', 'Tipo de sexo', 'Puesto colaborador', 'Observaciones'
        ]
        
        # Aislamiento de métricas únicas de la segunda pestaña para evitar colisiones
        cols_unicas_c = ['ID'] + [col for col in df_c.columns if col not in columnas_comunes and col != 'ID']
        df_checklist_unique = df_c[cols_unicas_c]
        df_checklist_unique = df_checklist_unique.loc[:, ~df_checklist_unique.columns.duplicated()]

        # Consolidación final por ID de colaborador
        df_final = pd.merge(df_e, df_checklist_unique, on='ID', how='outer')

        if 'Fecha de evaluación' in df_final.columns:
            df_final['Fecha de evaluación'] = pd.to_datetime(df_final['Fecha de evaluación'], errors='coerce').dt.date

        return df_final