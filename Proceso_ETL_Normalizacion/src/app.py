import streamlit as st
import pandas as pd
import plotly.express as px
from etl_pipeline import InclusiónETL

st.set_page_config(
    page_title="Dashboard de Inclusión y Control Operativo",
    layout="wide"
)

@st.cache_data(ttl=60)
def cargar_datos_en_vivo():
    pipeline = InclusiónETL()
    return pipeline.ejecutar_pipeline_en_vivo()

try:
    df_base = cargar_datos_en_vivo()
except Exception as e:
    st.error(f"Error al conectar o descargar datos en tiempo real desde Google Sheets: {e}")
    st.stop()

st.sidebar.header("Filtros Globales")

if st.sidebar.button("🔄 Sincronizar Google Sheets en Vivo"):
    st.cache_data.clear()
    df_base = cargar_datos_en_vivo()
    st.rerun()

sedes = sorted(df_base['Sede de tienda'].dropna().unique().tolist()) if 'Sede de tienda' in df_base.columns else []
sedes_sel = st.sidebar.multiselect("Sede de Tienda", options=sedes)

discapacidades = sorted(df_base['Tipo de discapacidad'].dropna().unique().tolist()) if 'Tipo de discapacidad' in df_base.columns else []
disc_sel = st.sidebar.multiselect("Tipo de Discapacidad", options=discapacidades)

puestos = sorted(df_base['Puesto colaborador'].dropna().unique().tolist()) if 'Puesto colaborador' in df_base.columns else []
puestos_sel = st.sidebar.multiselect("Puesto Colaborador", options=puestos)

mask = pd.Series(True, index=df_base.index)
if sedes_sel and 'Sede de tienda' in df_base.columns:
    mask &= df_base['Sede de tienda'].isin(sedes_sel)
if disc_sel and 'Tipo de discapacidad' in df_base.columns:
    mask &= df_base['Tipo de discapacidad'].isin(disc_sel)
if puestos_sel and 'Puesto colaborador' in df_base.columns:
    mask &= df_base['Puesto colaborador'].isin(puestos_sel)

df_f = df_base[mask]

if df_f.empty:
    st.warning("No hay registros que coincidan con los filtros seleccionados o la hoja está vacía.")
else:
    t_entrevistas, t_checklist, t_explorador = st.tabs([
        "📋 KPIs Entrevistas", 
        "🛠 KPIs Checklist de Puesto", 
        "🔍 Buscador y Detalles"
    ])

    with t_entrevistas:
        n_total = len(df_f)
        
        def pct(col, val):
            if n_total == 0 or col not in df_f.columns: return 0.0
            return (df_f[col].astype(str).str.upper() == str(val).upper()).sum() / n_total

        def pct_contiene(col, sub):
            if n_total == 0 or col not in df_f.columns: return 0.0
            return df_f[col].astype(str).str.upper().str.contains(str(sub).upper()).sum() / n_total

        def contar_casos(col, val):
            if col not in df_f.columns: return 0
            return (df_f[col].astype(str).str.upper() == str(val).upper()).sum()

        st.subheader("1. Bienestar Laboral")
        b1, b2, b3, b4, b5 = st.columns(5)
        b1.metric("Colaboradores", f"{n_total}")
        b2.metric("Cómodos en Puesto", f"{pct_contiene('Ambiente de trabajo', 'Sí'):.1%}")
        b3.metric("Cómodos en Sede", f"{1 - pct('Recomendación cambio de sede', 'Sí'):.1%}")
        b4.metric("Trabajan Tranquilos", f"{pct('Trabaja con tranquilidad', 'Sí'):.1%}")
        b5.metric("Estrés Laboral", f"{pct('Estrés por carga laboral', 'Sí'):.1%}")

        st.subheader("2. Inclusión y Accesibilidad")
        i1, i2, i3, i4, i5 = st.columns(5)
        i1.metric("Inst. Adaptadas", f"{pct('Requiere instrucciones adaptadas', 'Sí'):.1%}")
        i2.metric("Apoyo del Jefe", f"{pct('Apoyo principal', 'Jefe'):.1%}")
        i3.metric("Apoyo Visual", f"{pct_contiene('Formato Preferido de apoyo', 'VISUAL'):.1%}")
        i4.metric("Apoyo Escrito", f"{pct_contiene('Formato Preferido de apoyo', 'ESCRITO'):.1%}")
        i5.metric("Apoyo Verbal", f"{pct_contiene('Formato Preferido de apoyo', 'VERBAL'):.1%}")

        st.subheader("3. Riesgos Psicosociales y Retención")
        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("Bullying/Discrim.", f"{contar_casos('Presencia de acoso o Bulling u otro', 'Sí')} casos")
        r2.metric("Dif. Comunicación", f"{contar_casos('Comunicación Compañeros', 'Regular')} casos")
        r3.metric("Conflictos Comp.", f"{contar_casos('Comunicación Compañeros', 'Malo')} casos")
        r4.metric("Problemas Clientes", f"{(df_f['Retos en la relación con clientes'].astype(str).str.upper() != 'NO').sum()} casos")
        r5.metric("Riesgo de Salida", f"{pct('Riesgo de salida de la empresa', 'Sí'):.1%}", delta_color="inverse")

        st.subheader("4. Adaptaciones del Puesto")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Ajustes Ergonómicos", f"{(df_f['Formato Preferido de apoyo'].astype(str).str.contains('ERGONÓMICO|ERGONOMICO', case=False)).sum()} colab.")
        a2.metric("Restricciones Físicas", f"{(df_f['Actividad más difícil'].astype(str).str.contains('FÍSICO|FISICO|ESTAR DE PIE', case=False)).sum()} colab.")
        a3.metric("Dificultad Peso", f"{(df_f['Actividad más difícil'].astype(str).str.contains('PESO|CARGAR|MERCADERÍA|MERCADERIA', case=False)).sum()} colab.")
        a4.metric("Accesibilidad Específica", f"{(df_f['Mejora solicitada'].astype(str).str.contains('ACCESIBILIDAD|RAMPA|INFRAESTRUCTURA', case=False)).sum()} colab.")

        st.markdown("---")
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            if 'Tipo de discapacidad' in df_f.columns:
                fig_disc = px.pie(df_f, names='Tipo de discapacidad', title='Distribución por Tipo de Discapacidad', hole=0.4)
                st.plotly_chart(fig_disc, use_container_width=True)
        with c_g2:
            if 'Sede de tienda' in df_f.columns and 'Tipo de sexo' in df_f.columns:
                fig_sede = px.histogram(df_f, x='Sede de tienda', color='Tipo de sexo', title='Evaluaciones por Sede', barmode='group')
                st.plotly_chart(fig_sede, use_container_width=True)

    with t_checklist:
        st.subheader("Métricas de Desempeño y Capacidad Operativa (Checklist)")
        
        st.markdown("#### Desempeño y Adaptación Operativa")
        ch1, ch2, ch3, ch4 = st.columns(4)
        ch1.metric("Cumple Procedimientos", f"{pct('Cumple procedimientos', 'Sí'):.1%}")
        ch2.metric("Cumple Tiempos de Entrega", f"{pct('Cumple tiempos', 'Sí'):.1%}")
        ch3.metric("Comprende Instrucciones", f"{pct('Comprende instrucciones', 'Sí'):.1%}")
        ch4.metric("Identifica Prioridades", f"{pct('Identifica prioridades operativas', 'Sí'):.1%}")

        st.markdown("#### Autonomía y Habilidades Blandas")
        ch5, ch6, ch7 = st.columns(3)
        ch5.metric("Autonomía sin Supervisión", f"{pct('Autonomia_ tareas sin supervisión', 'Sí'):.1%}")
        ch6.metric("Se Adapta a Cambios", f"{pct('AU_se adapata a cambios', 'Sí'):.1%}")
        ch7.metric("Aptitud Colaborativa", f"{pct('Aptitud colaborativa', 'Sí'):.1%}")

        st.markdown("#### Ergonomía, Carga y Seguridad")
        ch8, ch9, ch10, ch11 = st.columns(4)
        ch8.metric("Manipulación Carga Adecuada", f"{pct('Manipulación de carga es adecuada', 'Sí'):.1%}")
        ch9.metric("Permanencia de Pie Afecta", f"{pct('Permanencia de pie', 'Sí'):.1%}")
        ch10.metric("Variedad de Tareas Afecta", f"{pct('Variedad de tareas afecta', 'Sí'):.1%}")
        ch11.metric("Desplazamiento Seguro", f"{pct('Entornos_Desplazamiento seguro', 'Sí'):.1%}")

        st.markdown("#### Ajustes y Soporte en Tienda")
        ch12, ch13 = st.columns(2)
        ch12.metric("Puestos con Ajuste Adecuado", f"{pct('Ajuste puesto persona', 'Adecuado'):.1%}")
        ch13.metric("Cuenta con Apoyos Existentes", f"{pct('Existen apoyos', 'Sí'):.1%}")

        st.markdown("---")
        cg_3, cg_4 = st.columns(2)
        with cg_3:
            if 'Nivel de exigencia del puesto' in df_f.columns and 'Puesto colaborador' in df_f.columns:
                fig_exig = px.box(df_f, x='Puesto colaborador', y='Nivel de exigencia del puesto', title='Nivel de Exigencia Operativa según el Puesto')
                st.plotly_chart(fig_exig, use_container_width=True)
        with cg_4:
            if 'Recomendación técnica' in df_f.columns:
                df_recom = df_f['Recomendación técnica'].value_counts().reset_index()
                df_recom.columns = ['Dictamen', 'Total']
                fig_rec = px.bar(df_recom, x='Total', y='Dictamen', orientation='h', title='Distribución de Recomendaciones Técnicas')
                st.plotly_chart(fig_rec, use_container_width=True)

    with t_explorador:
        st.subheader("Buscador General de Colaboradores")
        query = st.text_input("Ingresa Nombre o ID de colaborador:")
        
        if query and 'Nombre del colaborador' in df_f.columns and 'ID' in df_f.columns:
            df_d = df_f[
                df_f['Nombre del colaborador'].str.contains(query, case=False, na=False) |
                df_f['ID'].str.contains(query, case=False, na=False)
            ]
        else:
            df_d = df_f

        st.dataframe(df_d, use_container_width=True, hide_index=True)
        
        csv_data = df_d.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar Reporte Consolidado (CSV)",
            data=csv_data,
            file_name="reporte_consolidado_inclusion.csv",
            mime="text/csv"
        )