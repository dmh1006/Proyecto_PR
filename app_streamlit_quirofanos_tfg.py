from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from Proyecto.planificador_tfg import (
    agenda_dia,
    analisis_procedimientos,
    construir_catalogo_quirurgico,
    cargar_datos,
    obtener_agenda_combinada,
    ocupacion_por_dia_quirofano,
    preparar_dataset_funcional,
    proponer_huecos,
    resumen_general,
    tiempos_muertos,
    uso_quirofanos,
)

st.set_page_config(
    page_title="Planificación de quirófanos · TFG",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def cargar_base() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = cargar_datos()
    df_real = preparar_dataset_funcional(df)
    catalogo = construir_catalogo_quirurgico(df_real)
    return df, df_real, catalogo


def inicializar_estado() -> None:
    if "cirugias_anadidas" not in st.session_state:
        st.session_state.cirugias_anadidas = []


# ----------------------------------------------------------
# UTILIDADES VISUALES
# ----------------------------------------------------------

def minutos_desde_referencia(ts: pd.Timestamp, referencia: pd.Timestamp) -> float:
    return (ts - referencia).total_seconds() / 60


def figura_timeline_agenda(agenda: pd.DataFrame, fecha: pd.Timestamp, titulo: str) -> go.Figure:
    inicio_bloque = pd.Timestamp(f"{fecha.strftime('%Y-%m-%d')} 08:00")
    fin_bloque = pd.Timestamp(f"{fecha.strftime('%Y-%m-%d')} 20:00")

    if agenda.empty:
        fig = go.Figure()
        fig.update_layout(
            title=titulo,
            xaxis_title="Hora",
            yaxis_title="Quirófano",
            template="plotly_white",
            height=500,
        )
        return fig

    data = agenda.copy()
    data["inicio_min"] = data["inicio_dt"].apply(lambda x: minutos_desde_referencia(x, inicio_bloque))
    data["fin_min"] = data["fin_dt"].apply(lambda x: minutos_desde_referencia(x, inicio_bloque))
    data["duracion_plot"] = data["fin_min"] - data["inicio_min"]
    data["etiqueta"] = data["procedimiento_base"].fillna(data["procedimiento"]).fillna("Sin nombre")
    data["fuente_plot"] = data.get("fuente", "Histórico")

    fig = px.timeline(
        data,
        x_start="inicio_dt",
        x_end="fin_dt",
        y="quirofano",
        color="fuente_plot",
        hover_data={
            "etiqueta": True,
            "inicio_dt": True,
            "fin_dt": True,
            "duracion_min": ':.0f',
            "fuente_plot": True,
            "quirofano": False,
        },
    )
    fig.update_yaxes(categoryorder="category ascending")
    fig.update_layout(
        title=titulo,
        xaxis_title="Hora del día",
        yaxis_title="Quirófano",
        height=520,
        template="plotly_white",
        legend_title="Origen",
        margin=dict(l=10, r=10, t=60, b=10),
    )
    fig.update_xaxes(range=[inicio_bloque, fin_bloque], tickformat="%H:%M")
    return fig


def figura_ocupacion_diaria(df_ocup: pd.DataFrame) -> go.Figure:
    fig = px.imshow(
        df_ocup,
        text_auto='.0f',
        aspect='auto',
        labels=dict(x="Quirófano", y="Fecha", color="% ocupación"),
    )
    fig.update_layout(height=700, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10))
    return fig


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "agenda") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


# ----------------------------------------------------------
# APP
# ----------------------------------------------------------

def main() -> None:
    inicializar_estado()
    _, df_real, catalogo = cargar_base()

    st.title("🏥 Planificador quirúrgico inteligente")
    st.caption("Prototipo funcional orientado a TFG: análisis histórico, propuesta de huecos y simulación de agenda.")

    with st.sidebar:
        st.header("Configuración")
        fechas_disponibles = sorted(df_real["fecha"].dt.date.unique())
        fecha_sel = st.date_input(
            "Fecha de trabajo",
            value=fechas_disponibles[0],
            min_value=fechas_disponibles[0],
            max_value=fechas_disponibles[-1],
        )
        procedimientos = sorted(catalogo["procedimiento_base"].tolist())
        procedimiento_sel = st.selectbox("Procedimiento a planificar", procedimientos)
        max_resultados = st.slider("Número de propuestas", 1, 10, 5)
        quirofanos_disponibles = sorted(df_real["quirofano"].dropna().astype(str).unique())
        filtro_qx = st.multiselect(
            "Restringir a quirófanos",
            options=quirofanos_disponibles,
            default=quirofanos_disponibles,
        )

    fecha_ts = pd.to_datetime(fecha_sel)
    agenda_historica = agenda_dia(df_real, fecha_ts)
    agenda_combinada = obtener_agenda_combinada(df_real, fecha_ts, st.session_state.cirugias_anadidas)
    propuestas = proponer_huecos(
        df_real=df_real,
        catalogo=catalogo,
        procedimiento=procedimiento_sel,
        fecha=fecha_ts,
        quirofanos_validos=filtro_qx,
        max_resultados=max_resultados,
    )

    # KPIs
    kpis = resumen_general(df_real)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Cirugías", kpis["n_cirugias"])
    c2.metric("Quirófanos", kpis["n_quirofanos"])
    c3.metric("Servicios", kpis["n_servicios"])
    c4.metric("Horas analizadas", kpis["tiempo_total_horas"])
    c5.metric("Duración media (min)", kpis["duracion_media_min"])
    c6.metric("Urgencias (%)", kpis["pct_urgencias"])

    tab1, tab2, tab3, tab4 = st.tabs([
        "Planificación diaria",
        "Análisis histórico",
        "Ocupación mensual",
        "Exportación",
    ])

    with tab1:
        left, right = st.columns([1.1, 0.9])

        with left:
            st.subheader(f"Agenda del día · {fecha_ts.strftime('%d/%m/%Y')}")
            fig = figura_timeline_agenda(
                agenda_combinada,
                fecha_ts,
                "Agenda combinada (histórico + simulación)",
            )
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.subheader("Propuestas de hueco")
            if propuestas.empty:
                st.warning("No se han encontrado huecos válidos para ese procedimiento con los filtros actuales.")
            else:
                propuestas_view = propuestas.copy()
                propuestas_view["inicio"] = propuestas_view["inicio"].dt.strftime("%H:%M")
                propuestas_view["fin_estimado"] = propuestas_view["fin_estimado"].dt.strftime("%H:%M")
                st.dataframe(
                    propuestas_view[[
                        "quirofano",
                        "inicio",
                        "fin_estimado",
                        "duracion_necesaria",
                        "duracion_disponible",
                        "holgura_min",
                        "es_quirofano_habitual",
                    ]],
                    use_container_width=True,
                    hide_index=True,
                )

                idx = st.selectbox(
                    "Selecciona propuesta para añadir a la simulación",
                    options=list(propuestas.index),
                    format_func=lambda i: f"{propuestas.loc[i, 'quirofano']} · {propuestas.loc[i, 'inicio'].strftime('%H:%M')} - {propuestas.loc[i, 'fin_estimado'].strftime('%H:%M')}",
                )

                if st.button("Añadir cirugía a la agenda", type="primary"):
                    fila = propuestas.loc[idx].to_dict()
                    fila["fecha"] = fecha_ts
                    st.session_state.cirugias_anadidas.append(fila)
                    st.success("Cirugía añadida a la simulación de agenda.")
                    st.rerun()

                if st.session_state.cirugias_anadidas and st.button("Vaciar simulación"):
                    st.session_state.cirugias_anadidas = []
                    st.success("Simulación reiniciada.")
                    st.rerun()

            st.markdown("---")
            st.subheader("Cirugías simuladas")
            if st.session_state.cirugias_anadidas:
                sim = pd.DataFrame(st.session_state.cirugias_anadidas).copy()
                sim["inicio"] = pd.to_datetime(sim["inicio"]).dt.strftime("%Y-%m-%d %H:%M")
                sim["fin_estimado"] = pd.to_datetime(sim["fin_estimado"]).dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(
                    sim[["procedimiento", "quirofano", "inicio", "fin_estimado", "holgura_min"]],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Todavía no has añadido ninguna cirugía simulada.")

    with tab2:
        st.subheader("Procedimientos más frecuentes")
        proc = analisis_procedimientos(df_real)
        st.dataframe(proc.head(20), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            top_proc = proc.head(10).copy()
            fig_proc = px.bar(
                top_proc,
                x="n_cirugias",
                y="procedimiento_base",
                orientation="h",
                title="Top 10 procedimientos por volumen",
            )
            fig_proc.update_layout(template="plotly_white", height=450, yaxis_title="")
            st.plotly_chart(fig_proc, use_container_width=True)

        with c2:
            uso = uso_quirofanos(df_real)
            fig_uso = px.bar(
                uso,
                x="quirofano",
                y="horas_ocupadas",
                title="Horas ocupadas por quirófano",
            )
            fig_uso.update_layout(template="plotly_white", height=450)
            st.plotly_chart(fig_uso, use_container_width=True)

        st.subheader("Tiempos muertos entre cirugías")
        gaps = tiempos_muertos(df_real)
        gaps_validos = gaps["tiempo_muerto_min"].notna() & (gaps["tiempo_muerto_min"] >= 0)
        st.metric("Tiempo muerto medio (min)", round(gaps.loc[gaps_validos, "tiempo_muerto_min"].mean(), 2))
        fig_gap = px.histogram(
            gaps.loc[gaps_validos],
            x="tiempo_muerto_min",
            nbins=30,
            title="Distribución de tiempos muertos",
        )
        fig_gap.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_gap, use_container_width=True)

    with tab3:
        st.subheader("Mapa de ocupación diaria por quirófano")
        ocup = ocupacion_por_dia_quirofano(df_real)
        matriz = ocup.pivot(index="fecha_str", columns="quirofano", values="ocupacion_pct").fillna(0)
        st.plotly_chart(figura_ocupacion_diaria(matriz), use_container_width=True)
        st.dataframe(ocup, use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("Exportar resultados")
        vista_exportacion = st.selectbox("Vista a exportar", ["Día actual", "Mes completo"])

        if vista_exportacion == "Día actual":
            agenda_export = agenda_combinada.copy()
            nombre_base = f"planificacion_diaria_{fecha_ts.strftime('%Y_%m_%d')}"
        else:
            agenda_export = df_real.copy()
            if st.session_state.cirugias_anadidas:
                extra = pd.DataFrame(st.session_state.cirugias_anadidas).copy()
                if not extra.empty:
                    extra["fecha"] = pd.to_datetime(extra["fecha"])
                    extra["inicio_dt"] = pd.to_datetime(extra["inicio"])
                    extra["fin_dt"] = pd.to_datetime(extra["fin_estimado"])
                    extra["duracion_min"] = (extra["fin_dt"] - extra["inicio_dt"]).dt.total_seconds() / 60
                    extra["procedimiento_base"] = extra["procedimiento"]
                    extra["fuente"] = "Propuesta añadida"
                    for col in agenda_export.columns:
                        if col not in extra.columns:
                            extra[col] = pd.NA
                    extra = extra[agenda_export.columns]
                    agenda_export = pd.concat([agenda_export, extra], ignore_index=True)
            nombre_base = "planificacion_mensual_febrero_2026"

        st.dataframe(agenda_export.head(30), use_container_width=True, hide_index=True)

        csv_bytes = agenda_export.to_csv(index=False).encode("utf-8-sig")
        xlsx_bytes = to_excel_bytes(agenda_export)

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Descargar CSV",
                data=csv_bytes,
                file_name=f"{nombre_base}.csv",
                mime="text/csv",
            )
        with d2:
            st.download_button(
                "Descargar Excel",
                data=xlsx_bytes,
                file_name=f"{nombre_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.info("Para el TFG, esta exportación te sirve como evidencia del funcionamiento del prototipo y de la simulación de agenda.")


if __name__ == "__main__":
    main()
