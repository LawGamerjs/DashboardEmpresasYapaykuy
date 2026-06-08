import pandas as pd
import urllib.request
import urllib.error
import io
import streamlit as st

class InclusiónETL:
    def __init__(self):
        self.pub_token = "2PACX-1vQg11ARQRQzhifajGDtbWDe37uqN_VGQu7eCIoRorMxWC-V18qC6YmudtzLAtVru9DJ9IIIra-qqslU"
        self.url_entrevistas = f"https://docs.google.com/spreadsheets/d/e/{self.pub_token}/pub?gid=0&output=csv"
        self.url_checklist = f"https://docs.google.com/spreadsheets/d/e/{self.pub_token}/pub?gid=111429532&output=csv"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def log_diagnostico(self, titulo: str, mensaje: str, tipo: str = "info"):
        log_msg = f"[LOG - ETL] {titulo}: {mensaje}"
        print(log_msg)
        if tipo == "error":
            st.error(log_msg)
        elif tipo == "warning":
            st.warning(log_msg)
        else:
            st.info(log_msg)

    def descargar_csv_con_autenticacion(self, url: str, nombre_hoja: str) -> pd.DataFrame:
        self.log_diagnostico(f"Iniciando descarga", f"Intentando conectar a {nombre_hoja}")
        self.log_diagnostico(f"URL Solicitada", url)
        
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                self.log_diagnostico(f"Respuesta Google ({nombre_hoja})", f"Status: {response.status} OK")
                data_bytes = response.read()
                return pd.read_csv(io.StringIO(data_bytes.decode('utf-8')))
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore') if hasattr(e, 'read') else "No cuerpo"
            self.log_diagnostico(
                f"HTTPError detectado en {nombre_hoja}", 
                f"Código: {e.code} | Razón: {e.reason} | Cuerpo: {error_body}", 
                tipo="error"
            )
            raise e
        except Exception as e:
            self.log_diagnostico(f"Fallo crítico inesperado en {nombre_hoja}", str(e), tipo="error")
            raise e

    def limpiar_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [str(col).strip() for col in df.columns]
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        if 'ID' in df.columns:
            df['ID'] = df['ID'].astype(str).str.split('.').str[0].str.zfill(5)
        return df

    def ejecutar_pipeline_en_vivo(self) -> pd.DataFrame:
        self.log_diagnostico("Pipeline", "Ejecutando integración en memoria...")
        
        df_e = self.descargar_csv_con_autenticacion(self.url_entrevistas, "Entrevistas (gid=0)")
        df_c = self.descargar_csv_con_autenticacion(self.url_checklist, "Checklist (gid=111429532)")

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

        self.log_diagnostico("Pipeline", f"Sincronización completa. Filas consolidadas: {len(df_final)}")
        return df_final