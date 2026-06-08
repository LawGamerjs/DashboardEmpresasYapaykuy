import pandas as pd

class InclusiónETL:
    def __init__(self):
        self.pub_token = "2PACX-1vQg11ARQRQzhifajGDtbWDe37uqN_VGQu7eCIoRorMxWC-V18qC6YmudtzLAtVru9DJ9IIIra-qqslU"
        self.url_entrevistas = f"https://docs.google.com/spreadsheets/d/e/{self.pub_token}/pub?gid=0&output=csv"
        self.url_checklist = f"https://docs.google.com/spreadsheets/d/e/{self.pub_token}/pub?gid=111429532&output=csv"

    def limpiar_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [str(col).strip() for col in df.columns]
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        if 'ID' in df.columns:
            df['ID'] = df['ID'].astype(str).str.split('.').str[0].str.zfill(5)
        return df

    def ejecutar_pipeline_en_vivo(self) -> pd.DataFrame:
        df_e = pd.read_csv(self.url_entrevistas)
        df_c = pd.read_csv(self.url_checklist)

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