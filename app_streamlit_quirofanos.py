from io import BytesIO
import calendar

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

try:
    from Proyecto.analisis_quirofano import (
        cargar_datos,
        preparar_dataset_funcional,
        construir_catalogo_quirurgico,
        estimar_nueva_cirugia,
        agenda_dia,
        calcular_huecos_quirofano,
    )
except ImportError:
    from analisis_quirofano import (
        cargar_datos,
        preparar_dataset_funcional,
        construir_catalogo_quirurgico,
        estimar_nueva_cirugia,
        agenda_dia,
        calcular_huecos_quirofano,
    )


st.set_page_config(
    page_title="Planificador quirúrgico",
    page_icon="🏥",
    layout="wide",
)

CSS = """
<style>
    .stApp {
        background-color: #f3f4f6;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .card {
        background: white;
        border: 1px solid #d7dee7;
        border-radius: 22px;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
    }

    .kpi-card {
        padding: 20px 24px;
        min-height: 110px;
    }

    .kpi-label {
        color: #5b7191;
        font-size: 17px;
        margin-bottom: 6px;
    }

    .kpi-value {
        color: #081a44;
        font-size: 26px;
        font-weight: 800;
        line-height: 1.1;
    }

    .section-title {
        color: #081a44;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 18px;
    }

    .mini-card {
        background: #eef2f6;
        border-radius: 16px;
        padding: 16px 16px 14px 16px;
        min-height: 96px;
        margin-bottom: 12px;
    }

    .mini-label {
        color: #607694;
        font-size: 16px;
        margin-bottom: 4px;
    }

    .mini-value {
        color: #081a44;
        font-size: 20px;
        font-weight: 800;
    }

    .chip {
        display: inline-block;
        background: #eef2f6;
        color: #081a44;
        border-radius: 999px;
        padding: 6px 12px;
        margin-right: 8px;
        margin-bottom: 8px;
        font-size: 14px;
        font-weight: 700;
    }

    .info-box {
        border: 1px dashed #d6dde6;
        border-radius: 18px;
        padding: 18px;
        color: #4c607b;
        font-size: 15px;
        line-height: 1.5;
        margin-top: 8px;
    }

    .calendar-card {
        padding: 18px 14px 20px 14px;
        margin-top: 18px;
    }

    .calendar-title {
        color: #081a44;
        font-size: 28px;
        font-weight: 800;
        margin: 4px 0 18px 2px;
    }

    .calendar-wrap {
        background: #dfe5ec;
        border-radius: 22px;
        padding: 18px 18px 22px 18px;
        overflow-x: auto;
    }

    .calendar-grid {
        min-width: 1180px;
    }

    .calendar-header {
        display: grid;
        grid-template-columns: 80px repeat(12, 1fr);
        gap: 0;
        margin-bottom: 10px;
        color: #345173;
        font-size: 15px;
    }

    .calendar-hour {
        text-align: center;
        border-left: 1px solid #aebbc9;
        padding-bottom: 8px;
    }

    .calendar-row {
        display: grid;
        grid-template-columns: 80px 1fr;
        align-items: center;
        margin-bottom: 16px;
        column-gap: 18px;
    }

    .qx-label {
        color: #294b72;
        font-size: 20px;
        font-weight: 700;
        text-align: left;
    }

    .timeline {
        position: relative;
        height: 80px;
        background: #e9aeb8;
        border-radius: 18px;
        overflow: hidden;
    }

    .timeline-grid {
        position: absolute;
        inset: 0;
        background-image: repeating-linear-gradient(
            to right,
            transparent,
            transparent calc(8.333% - 1px),
            rgba(70, 90, 120, 0.22) calc(8.333% - 1px),
            rgba(70, 90, 120, 0.22) 8.333%
        );
        pointer-events: none;
    }

    .surgery-block {
        position: absolute;
        top: 10px;
        height: 60px;
        background: #f6b800;
        border: 1px solid #b57d00;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 4px 8px;
        overflow: hidden;
        z-index: 2;
    }

    .surgery-text {
        color: #111111;
        font-size: 12px;
        line-height: 1.2;
        font-weight: 700;
        text-transform: uppercase;
        white-space: normal;
    }

    .candidate-yes {
        display: inline-block;
        background: #071838;
        color: white;
        border-radius: 999px;
        padding: 4px 12px;
        font-weight: 700;
        font-size: 14px;
    }

    .candidate-no {
        display: inline-block;
        background: white;
        color: #111827;
        border: 1px solid #d1d5db;
        border-radius: 999px;
        padding: 4px 12px;
        font-weight: 700;
        font-size: 14px;
    }

    .export-card {
        margin-top: 18px;
        padding: 18px 22px;
    }

    div[data-testid="stMetric"] {
        background: transparent;
        border: none;
        padding: 0;
    }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data
def cargar_base():
    df = cargar_datos()
    df_real = preparar_dataset_funcional(df)
    catalogo = construir_catalogo_quirurgico(df_real)
    return df_real, catalogo


def formatear_min(valor):
    if pd.isna(valor):
        return "-"
    return f"{int(round(float(valor)))} min"


def truncar(texto, n=38):
    texto = str(texto)
    return texto if len(texto) <= n else texto[: n - 3] + "..."


def dibujar_kpi(label, value):
    st.markdown(
        f"""
        <div class='card kpi-card'>
            <div class='kpi-label'>{label}</div>
            <div class='kpi-value'>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dibujar_ficha(ficha):
    st.markdown("<div class='section-title'>Ficha operativa</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"<div class='mini-card'><div class='mini-label'>Duración mediana</div><div class='mini-value'>{formatear_min(ficha['duracion_mediana_min'])}</div></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='mini-card'><div class='mini-label'>Duración planificable</div><div class='mini-value'>{formatear_min(ficha['duracion_planificable_min'])}</div></div>",
            unsafe_allow_html=True,
        )

    c3, c4 = st.columns(2)
    with c3:
        st.markdown(
            f"<div class='mini-card'><div class='mini-label'>Preparación</div><div class='mini-value'>{formatear_min(ficha['prep_min'])}</div></div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"<div class='mini-card'><div class='mini-label'>Postcirugía</div><div class='mini-value'>{formatear_min(ficha['post_min'])}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='mini-label' style='margin-bottom:10px;'>Quirófanos habituales</div>", unsafe_allow_html=True)

    quir = [q.strip() for q in str(ficha["quirofanos_habituales"]).split(",") if q.strip()]
    if quir:
        st.markdown("".join([f"<span class='chip'>{q}</span>" for q in quir]), unsafe_allow_html=True)
    else:
        st.markdown("<span class='chip'>Sin datos</span>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class='info-box'>
            El modelo actual prioriza quirófanos habituales y huecos con menor holgura.
            Es una base útil para validar el valor del sistema antes de añadir restricciones
            de cirujano, equipamiento y prioridades reales.
        </div>
        """,
        unsafe_allow_html=True,
    )


def construir_label_candidato(row):
    inicio = pd.to_datetime(row["inicio"]).strftime("%H:%M")
    fin = pd.to_datetime(row["fin_estimado"]).strftime("%H:%M")
    holgura = int(round(float(row["holgura_min"])))
    habitual = "habitual" if bool(row["es_quirofano_habitual"]) else "no habitual"
    return f"{row['quirofano']} | {inicio}-{fin} | holgura {holgura} min | {habitual}"


def obtener_agenda_base(df_real: pd.DataFrame, fecha) -> pd.DataFrame:
    return agenda_dia(df_real, fecha).copy()


def obtener_agenda_combinada(df_real: pd.DataFrame, fecha, cirugias_anadidas: pd.DataFrame) -> pd.DataFrame:
    agenda_base = obtener_agenda_base(df_real, fecha)

    if cirugias_anadidas is None or cirugias_anadidas.empty:
        return agenda_base.sort_values(["quirofano", "inicio_dt"]).reset_index(drop=True)

    fecha_ts = pd.to_datetime(fecha)
    extras = cirugias_anadidas[cirugias_anadidas["fecha"] == fecha_ts].copy()

    if extras.empty:
        return agenda_base.sort_values(["quirofano", "inicio_dt"]).reset_index(drop=True)

    agenda_total = pd.concat([agenda_base, extras], ignore_index=True)
    return agenda_total.sort_values(["quirofano", "inicio_dt"]).reset_index(drop=True)


def obtener_agenda_mensual(df_real: pd.DataFrame, fecha_ref, cirugias_anadidas: pd.DataFrame) -> pd.DataFrame:
    fecha_ref = pd.to_datetime(fecha_ref)
    inicio_mes = fecha_ref.replace(day=1)
    fin_mes = inicio_mes + pd.offsets.MonthEnd(1)

    fechas = pd.date_range(inicio_mes, fin_mes, freq="D")
    agendas = []

    for fecha in fechas:
        agenda_fecha = obtener_agenda_combinada(df_real, fecha, cirugias_anadidas)
        if not agenda_fecha.empty:
            agendas.append(agenda_fecha)

    if not agendas:
        return pd.DataFrame()

    agenda_mes = pd.concat(agendas, ignore_index=True)
    return agenda_mes.sort_values(["fecha", "quirofano", "inicio_dt"]).reset_index(drop=True)


def proponer_huecos_desde_agenda(
    agenda_fecha: pd.DataFrame,
    catalogo: pd.DataFrame,
    procedimiento: str,
    fecha,
    hora_inicio_bloque="08:00",
    hora_fin_bloque="20:00",
    max_resultados=10,
):
    ficha = estimar_nueva_cirugia(catalogo, procedimiento)
    duracion_necesaria = ficha["duracion_planificable_min"]

    agenda = agenda_fecha.copy()
    quirofanos_preferidos = [
        q.strip() for q in str(ficha["quirofanos_habituales"]).split(",")
        if q.strip()
    ]

    quirofanos_a_explorar = sorted(agenda["quirofano"].dropna().astype(str).unique().tolist()) if not agenda.empty else []
    for q in quirofanos_preferidos:
        if q not in quirofanos_a_explorar:
            quirofanos_a_explorar.append(q)

    candidatos = []

    for qx in quirofanos_a_explorar:
        agenda_qx = agenda[agenda["quirofano"] == qx].copy()

        huecos = calcular_huecos_quirofano(
            agenda_qx=agenda_qx,
            fecha=fecha,
            hora_inicio_bloque=hora_inicio_bloque,
            hora_fin_bloque=hora_fin_bloque,
        )

        for h in huecos:
            if h["duracion_hueco_min"] >= duracion_necesaria:
                candidatos.append(
                    {
                        "procedimiento": ficha["procedimiento"],
                        "quirofano": qx,
                        "inicio": h["inicio_hueco"],
                        "fin_estimado": h["inicio_hueco"] + pd.Timedelta(minutes=duracion_necesaria),
                        "duracion_necesaria": duracion_necesaria,
                        "duracion_disponible": h["duracion_hueco_min"],
                        "holgura_min": h["duracion_hueco_min"] - duracion_necesaria,
                        "es_quirofano_habitual": qx in quirofanos_preferidos,
                    }
                )

    if not candidatos:
        return pd.DataFrame()

    candidatos_df = pd.DataFrame(candidatos)
    candidatos_df = candidatos_df.sort_values(
        by=["es_quirofano_habitual", "holgura_min", "inicio"],
        ascending=[False, True, True],
    )
    return candidatos_df.head(max_resultados).reset_index(drop=True)


def dibujar_calendario(agenda: pd.DataFrame, inicio_bloque: str, fin_bloque: str):
    st.markdown("<div class='calendar-title'>Calendario visual del día</div>", unsafe_allow_html=True)

    if agenda.empty:
        st.info("No hay actividad quirúrgica para ese día.")
        return

    qx_orden = sorted(agenda["quirofano"].dropna().astype(str).unique().tolist())
    if not qx_orden:
        st.info("No hay actividad quirúrgica para ese día.")
        return

    try:
        hora_ini = int(str(inicio_bloque).split(":")[0])
        hora_fin = int(str(fin_bloque).split(":")[0])
    except Exception:
        hora_ini, hora_fin = 8, 20

    if hora_fin <= hora_ini:
        hora_ini, hora_fin = 8, 20

    total_min = max(60, (hora_fin - hora_ini) * 60)

    header = ["<div></div>"]
    for h in range(hora_ini, hora_fin):
        header.append(f"<div class='calendar-hour'>{h}:00</div>")
    header_html = "".join(header)

    html = [
        "<div class='calendar-wrap'><div class='calendar-grid'>",
        f"<div class='calendar-header'>{header_html}</div>",
    ]

    for qx in qx_orden:
        agenda_qx = agenda[agenda["quirofano"].astype(str) == qx].copy()
        html.append("<div class='calendar-row'>")
        html.append(f"<div class='qx-label'>{qx}</div>")
        html.append("<div class='timeline'><div class='timeline-grid'></div>")

        for _, row in agenda_qx.iterrows():
            inicio = pd.to_datetime(row["inicio_dt"])
            fin = pd.to_datetime(row["fin_dt"])

            offset = max(0, (inicio.hour * 60 + inicio.minute) - (hora_ini * 60))
            dur = max(20, int((fin - inicio).total_seconds() / 60))

            left = min(100, (offset / total_min) * 100)
            width = min(100 - left, (dur / total_min) * 100)

            proc = truncar(
                row["procedimiento_base"] if "procedimiento_base" in row else row["procedimiento"],
                34,
            )
            etiqueta = f"{proc}<br>{inicio.strftime('%H:%M')}-{fin.strftime('%H:%M')}"

            html.append(
                f"<div class='surgery-block' style='left:{left:.3f}%; width:{width:.3f}%;'>"
                f"<div class='surgery-text'>{etiqueta}</div></div>"
            )

        html.append("</div></div>")

    html.append("</div></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def preparar_tabla_candidatos(candidatos: pd.DataFrame) -> pd.DataFrame:
    if candidatos.empty:
        return candidatos

    tabla = candidatos.copy()
    tabla["Inicio"] = pd.to_datetime(tabla["inicio"]).dt.strftime("%H:%M")
    tabla["Fin estimado"] = pd.to_datetime(tabla["fin_estimado"]).dt.strftime("%H:%M")
    tabla["Necesaria"] = tabla["duracion_necesaria"].round().astype(int).astype(str) + " min"
    tabla["Disponible"] = tabla["duracion_disponible"].round().astype(int).astype(str) + " min"
    tabla["Holgura"] = tabla["holgura_min"].round().astype(int).astype(str) + " min"
    tabla["Habitual"] = tabla["es_quirofano_habitual"].map(lambda x: "Sí" if bool(x) else "No")

    tabla = tabla.rename(
        columns={
            "procedimiento": "Procedimiento",
            "quirofano": "Quirófano",
        }
    )

    return tabla[
        [
            "Procedimiento",
            "Quirófano",
            "Inicio",
            "Fin estimado",
            "Necesaria",
            "Disponible",
            "Holgura",
            "Habitual",
        ]
    ]


def render_tabla_candidatos(candidatos: pd.DataFrame):
    st.markdown("<div class='card' style='padding:18px 22px; margin-top:18px;'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title' style='margin-bottom:16px;'>Mejores huecos candidatos</div>", unsafe_allow_html=True)

    if candidatos.empty:
        st.warning("No se han encontrado huecos válidos para esa configuración.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    tabla = preparar_tabla_candidatos(candidatos)

    html = ["<table style='width:100%; border-collapse:collapse;'>"]
    html.append("<thead><tr>")
    for col in tabla.columns:
        html.append(
            f"<th style='text-align:left; padding:14px 18px; color:#5b7191; font-size:16px; border-bottom:1px solid #d7dee7;'>{col}</th>"
        )
    html.append("</tr></thead><tbody>")

    for _, row in tabla.iterrows():
        html.append("<tr>")
        for col in tabla.columns:
            valor = row[col]
            if col == "Habitual":
                badge = "candidate-yes" if valor == "Sí" else "candidate-no"
                valor = f"<span class='{badge}'>{valor}</span>"
            html.append(
                f"<td style='padding:18px; border-bottom:1px solid #e6ebf0; font-size:15px; color:#081a44;'>{valor}</td>"
            )
        html.append("</tr>")

    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def preparar_agenda_exportacion(agenda: pd.DataFrame) -> pd.DataFrame:
    if agenda.empty:
        return pd.DataFrame(
            columns=["Fecha", "Quirófano", "Inicio", "Fin", "Procedimiento", "Cirujano", "Paciente"]
        )

    df = agenda.copy()
    df["Fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m-%d")
    df["Quirófano"] = df["quirofano"].astype(str)
    df["Inicio"] = pd.to_datetime(df["inicio_dt"]).dt.strftime("%H:%M")
    df["Fin"] = pd.to_datetime(df["fin_dt"]).dt.strftime("%H:%M")
    df["Procedimiento"] = df["procedimiento_base"].fillna(df.get("procedimiento", ""))
    df["Cirujano"] = df.get("cirujano_principal", "").fillna("")
    df["Paciente"] = df.get("paciente_id", "").fillna("")

    return df[["Fecha", "Quirófano", "Inicio", "Fin", "Procedimiento", "Cirujano", "Paciente"]]


def agenda_a_csv_bytes(agenda: pd.DataFrame) -> bytes:
    export_df = preparar_agenda_exportacion(agenda)
    return export_df.to_csv(index=False).encode("utf-8-sig")


def generar_pdf_diario(agenda: pd.DataFrame, fecha_ref, inicio_bloque="08:00", fin_bloque="20:00") -> bytes:
    buffer = BytesIO()
    fecha_ref = pd.to_datetime(fecha_ref)

    try:
        hora_ini = int(str(inicio_bloque).split(":")[0])
        hora_fin = int(str(fin_bloque).split(":")[0])
    except Exception:
        hora_ini, hora_fin = 8, 20

    if hora_fin <= hora_ini:
        hora_ini, hora_fin = 8, 20

    total_min = max(60, (hora_fin - hora_ini) * 60)

    export_df = preparar_agenda_exportacion(agenda)

    with PdfPages(buffer) as pdf:
        fig = plt.figure(figsize=(14, 8))
        ax = fig.add_subplot(111)
        ax.axis("off")

        ax.text(0.02, 0.95, "Planificación quirúrgica - vista diaria", fontsize=20, fontweight="bold")
        ax.text(0.02, 0.90, f"Fecha: {fecha_ref.strftime('%Y-%m-%d')}", fontsize=12)
        ax.text(0.02, 0.86, f"Cirugías del día: {len(export_df)}", fontsize=12)
        ax.text(0.02, 0.82, f"Quirófanos activos: {agenda['quirofano'].nunique() if not agenda.empty else 0}", fontsize=12)

        if not export_df.empty:
            tabla = export_df.head(18)
            table = ax.table(
                cellText=tabla.values,
                colLabels=tabla.columns,
                loc="center",
                cellLoc="center",
                bbox=[0.02, 0.05, 0.96, 0.68],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 1.4)

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        if not agenda.empty:
            qx_orden = sorted(agenda["quirofano"].dropna().astype(str).unique().tolist())

            fig, ax = plt.subplots(figsize=(16, max(5, len(qx_orden) * 1.2 + 2)))
            ax.set_title(f"Calendario quirúrgico del día - {fecha_ref.strftime('%Y-%m-%d')}", fontsize=16, fontweight="bold", pad=18)

            for idx, qx in enumerate(qx_orden):
                ax.add_patch(Rectangle((hora_ini, idx - 0.35), hora_fin - hora_ini, 0.7, facecolor="#e9aeb8", edgecolor="none"))

                agenda_qx = agenda[agenda["quirofano"].astype(str) == qx].copy()
                for _, row in agenda_qx.iterrows():
                    inicio = pd.to_datetime(row["inicio_dt"])
                    fin = pd.to_datetime(row["fin_dt"])
                    x0 = inicio.hour + inicio.minute / 60
                    width = max(0.15, (fin - inicio).total_seconds() / 3600)
                    etiqueta = truncar(row["procedimiento_base"] if "procedimiento_base" in row else row["procedimiento"], 22)

                    ax.add_patch(
                        Rectangle(
                            (x0, idx - 0.27),
                            width,
                            0.54,
                            facecolor="#f6b800",
                            edgecolor="#b57d00",
                            linewidth=1.0,
                        )
                    )
                    ax.text(
                        x0 + width / 2,
                        idx,
                        f"{etiqueta}\n{inicio.strftime('%H:%M')}-{fin.strftime('%H:%M')}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        fontweight="bold",
                    )

            ax.set_xlim(hora_ini, hora_fin)
            ax.set_ylim(-0.8, len(qx_orden) - 0.2)
            ax.set_yticks(range(len(qx_orden)))
            ax.set_yticklabels(qx_orden, fontsize=11, fontweight="bold")
            ax.set_xticks(list(range(hora_ini, hora_fin)))
            ax.set_xticklabels([f"{h}:00" for h in range(hora_ini, hora_fin)], fontsize=10)
            ax.grid(axis="x", linestyle="--", alpha=0.3)
            ax.invert_yaxis()
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)

            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf_mensual(agenda_mes: pd.DataFrame, fecha_ref) -> bytes:
    buffer = BytesIO()
    fecha_ref = pd.to_datetime(fecha_ref)

    anio = fecha_ref.year
    mes = fecha_ref.month
    nombre_mes = calendar.month_name[mes]

    with PdfPages(buffer) as pdf:
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111)
        ax.axis("off")
        ax.text(0.02, 0.95, f"Planificación quirúrgica mensual - {nombre_mes} {anio}", fontsize=20, fontweight="bold")
        ax.text(0.02, 0.90, f"Total cirugías del mes: {len(agenda_mes)}", fontsize=12)
        ax.text(0.02, 0.86, f"Quirófanos con actividad: {agenda_mes['quirofano'].nunique() if not agenda_mes.empty else 0}", fontsize=12)

        counts = {}
        if not agenda_mes.empty:
            agenda_mes_aux = agenda_mes.copy()
            agenda_mes_aux["dia"] = pd.to_datetime(agenda_mes_aux["fecha"]).dt.day
            counts = agenda_mes_aux.groupby("dia").size().to_dict()

        cal = calendar.monthcalendar(anio, mes)
        encabezados = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        celdas = []

        for semana in cal:
            fila = []
            for dia in semana:
                if dia == 0:
                    fila.append("")
                else:
                    n = counts.get(dia, 0)
                    texto = f"{dia}"
                    if n > 0:
                        texto += f"\n{n} cir."
                    fila.append(texto)
            celdas.append(fila)

        table = ax.table(
            cellText=celdas,
            colLabels=encabezados,
            cellLoc="center",
            loc="center",
            bbox=[0.05, 0.25, 0.90, 0.50],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 2.2)

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(14, 8))
        ax = fig.add_subplot(111)
        ax.axis("off")
        ax.text(0.02, 0.95, "Detalle mensual", fontsize=18, fontweight="bold")

        export_df = preparar_agenda_exportacion(agenda_mes)
        if not export_df.empty:
            tabla = export_df.head(28)
            table = ax.table(
                cellText=tabla.values,
                colLabels=tabla.columns,
                loc="center",
                cellLoc="center",
                bbox=[0.02, 0.04, 0.96, 0.82],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8.5)
            table.scale(1, 1.35)

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    buffer.seek(0)
    return buffer.getvalue()


# ----------------------
# CARGA DE DATOS
# ----------------------
df_real, catalogo = cargar_base()
opciones_procedimiento = sorted(catalogo["procedimiento_base"].dropna().astype(str).unique().tolist())
prioridades = ["Programada", "Preferente", "Urgente"]
fecha_default = pd.to_datetime(df_real["fecha"].min()).date()

# ----------------------
# ESTADO
# ----------------------
if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "paciente": "Paciente demo",
        "cirujano": "Dr. Demo",
        "procedimiento": opciones_procedimiento[0] if opciones_procedimiento else "",
        "prioridad": "Programada",
        "fecha": fecha_default,
        "inicio_bloque": "08:00",
        "fin_bloque": "20:00",
    }

if "candidatos" not in st.session_state:
    st.session_state.candidatos = pd.DataFrame()

if "cirugias_anadidas" not in st.session_state:
    st.session_state.cirugias_anadidas = pd.DataFrame(
        columns=[
            "quirofano",
            "fecha",
            "inicio_dt",
            "fin_dt",
            "procedimiento",
            "procedimiento_base",
            "cirujano_principal",
            "paciente_id",
        ]
    )

if "agenda_actual" not in st.session_state:
    st.session_state.agenda_actual = obtener_agenda_combinada(
        df_real,
        st.session_state.form_data["fecha"],
        st.session_state.cirugias_anadidas,
    )

if "seleccion_candidato" not in st.session_state:
    st.session_state.seleccion_candidato = 0

form_data = st.session_state.form_data

# ----------------------
# WIDGETS REACTIVOS
# ----------------------
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
panel_izq, panel_der = st.columns([1.25, 1.0])

with panel_izq:
    st.markdown("<div class='section-title'>Nueva planificación</div>", unsafe_allow_html=True)

    f1, f2 = st.columns(2)
    with f1:
        paciente = st.text_input(
            "Paciente",
            value=form_data["paciente"],
            key="paciente_input",
        )
    with f2:
        cirujano = st.text_input(
            "Cirujano",
            value=form_data["cirujano"],
            key="cirujano_input",
        )

    f3, f4 = st.columns(2)
    with f3:
        procedimiento = st.selectbox(
            "Procedimiento",
            options=opciones_procedimiento,
            index=opciones_procedimiento.index(form_data["procedimiento"]) if form_data["procedimiento"] in opciones_procedimiento else 0,
            key="procedimiento_input",
        )
    with f4:
        prioridad = st.selectbox(
            "Prioridad",
            options=prioridades,
            index=prioridades.index(form_data["prioridad"]) if form_data["prioridad"] in prioridades else 0,
            key="prioridad_input",
        )

    f5, f6 = st.columns(2)
    with f5:
        fecha_sel = st.date_input(
            "Fecha",
            value=form_data["fecha"],
            key="fecha_input",
        )
    with f6:
        inicio_bloque = st.text_input(
            "Inicio bloque",
            value=form_data["inicio_bloque"],
            key="inicio_input",
        )

    f7, _ = st.columns(2)
    with f7:
        fin_bloque = st.text_input(
            "Fin bloque",
            value=form_data["fin_bloque"],
            key="fin_input",
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        generar = st.button(
            "Generar propuesta",
            use_container_width=True,
            type="primary",
            key="btn_generar",
        )
    with b2:
        anadir = st.button(
            "Añadir cirugía seleccionada",
            use_container_width=True,
            key="btn_anadir",
        )

ficha_preview = estimar_nueva_cirugia(catalogo, procedimiento) if procedimiento else {
    "duracion_mediana_min": None,
    "duracion_planificable_min": None,
    "prep_min": None,
    "post_min": None,
    "quirofanos_habituales": "",
    "n_casos_historicos": 0,
}

agenda_preview = obtener_agenda_combinada(
    df_real,
    fecha_sel,
    st.session_state.cirugias_anadidas,
)

agenda_mes_preview = obtener_agenda_mensual(
    df_real,
    fecha_sel,
    st.session_state.cirugias_anadidas,
)

with panel_der:
    dibujar_ficha(ficha_preview)

with c1:
    dibujar_kpi("Cirugías del día", str(len(agenda_preview)))
with c2:
    dibujar_kpi("Duración planificable", formatear_min(ficha_preview["duracion_planificable_min"]))
with c3:
    dibujar_kpi("Casos históricos", str(ficha_preview["n_casos_historicos"]))
with c4:
    dibujar_kpi("Quirófanos activos", str(agenda_preview["quirofano"].nunique()))

# ----------------------
# GENERAR PROPUESTA
# ----------------------
if generar:
    st.session_state.form_data = {
        "paciente": paciente,
        "cirujano": cirujano,
        "procedimiento": procedimiento,
        "prioridad": prioridad,
        "fecha": fecha_sel,
        "inicio_bloque": inicio_bloque,
        "fin_bloque": fin_bloque,
    }

    agenda_planificacion = obtener_agenda_combinada(
        df_real,
        fecha_sel,
        st.session_state.cirugias_anadidas,
    )

    candidatos = proponer_huecos_desde_agenda(
        agenda_fecha=agenda_planificacion,
        catalogo=catalogo,
        procedimiento=procedimiento,
        fecha=fecha_sel,
        hora_inicio_bloque=inicio_bloque,
        hora_fin_bloque=fin_bloque,
        max_resultados=10,
    )

    st.session_state.agenda_actual = agenda_planificacion
    st.session_state.candidatos = candidatos
    st.session_state.seleccion_candidato = 0
    st.rerun()

# selector de hueco elegible
if not st.session_state.candidatos.empty:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    etiquetas_candidatos = [construir_label_candidato(row) for _, row in st.session_state.candidatos.iterrows()]
    idx_sel = min(st.session_state.seleccion_candidato, len(etiquetas_candidatos) - 1)
    seleccion_label = st.selectbox(
        "Hueco a añadir",
        options=etiquetas_candidatos,
        index=idx_sel,
        key="selector_candidato",
    )
    st.session_state.seleccion_candidato = etiquetas_candidatos.index(seleccion_label)

# ----------------------
# AÑADIR CIRUGÍA
# ----------------------
if anadir:
    if st.session_state.candidatos.empty:
        st.warning("Primero genera una propuesta.")
    else:
        idx = min(st.session_state.seleccion_candidato, len(st.session_state.candidatos) - 1)
        elegido = st.session_state.candidatos.iloc[idx].copy()

        nueva = {
            "quirofano": elegido["quirofano"],
            "fecha": pd.to_datetime(st.session_state.form_data["fecha"]),
            "inicio_dt": pd.to_datetime(elegido["inicio"]),
            "fin_dt": pd.to_datetime(elegido["fin_estimado"]),
            "procedimiento": st.session_state.form_data["procedimiento"],
            "procedimiento_base": st.session_state.form_data["procedimiento"],
            "cirujano_principal": st.session_state.form_data["cirujano"],
            "paciente_id": st.session_state.form_data["paciente"],
        }

        st.session_state.cirugias_anadidas = (
            pd.concat([st.session_state.cirugias_anadidas, pd.DataFrame([nueva])], ignore_index=True)
            .sort_values(["fecha", "quirofano", "inicio_dt"])
            .reset_index(drop=True)
        )

        st.session_state.agenda_actual = obtener_agenda_combinada(
            df_real,
            st.session_state.form_data["fecha"],
            st.session_state.cirugias_anadidas,
        )

        st.success(
            f"Cirugía añadida en {elegido['quirofano']} de "
            f"{pd.to_datetime(elegido['inicio']).strftime('%H:%M')} a "
            f"{pd.to_datetime(elegido['fin_estimado']).strftime('%H:%M')}."
        )

# ----------------------
# EXPORTACIÓN
# ----------------------
st.markdown("<div class='card export-card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title' style='font-size:22px; margin-bottom:10px;'>Exportar planificación</div>", unsafe_allow_html=True)

exp1, exp2, exp3 = st.columns([1.2, 1, 1])

with exp1:
    vista_exportacion = st.selectbox(
        "Vista a exportar",
        options=["Día actual", "Mes actual"],
        key="vista_exportacion",
    )

if vista_exportacion == "Día actual":
    agenda_export = obtener_agenda_combinada(
        df_real,
        fecha_sel,
        st.session_state.cirugias_anadidas,
    )
    nombre_base = f"planificacion_diaria_{pd.to_datetime(fecha_sel).strftime('%Y_%m_%d')}"
else:
    agenda_export = obtener_agenda_mensual(
        df_real,
        fecha_sel,
        st.session_state.cirugias_anadidas,
    )
    nombre_base = f"planificacion_mensual_{pd.to_datetime(fecha_sel).strftime('%Y_%m')}"

csv_bytes = agenda_a_csv_bytes(agenda_export)

if vista_exportacion == "Día actual":
    pdf_bytes = generar_pdf_diario(
        agenda_export,
        fecha_sel,
        inicio_bloque=inicio_bloque,
        fin_bloque=fin_bloque,
    )
else:
    pdf_bytes = generar_pdf_mensual(
        agenda_export,
        fecha_sel,
    )

with exp2:
    st.download_button(
        "Descargar CSV",
        data=csv_bytes,
        file_name=f"{nombre_base}.csv",
        mime="text/csv",
        use_container_width=True,
        key="download_csv",
    )

with exp3:
    st.download_button(
        "Descargar PDF",
        data=pdf_bytes,
        file_name=f"{nombre_base}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="download_pdf",
    )

st.markdown("</div>", unsafe_allow_html=True)

# ----------------------
# RENDER FINAL
# ----------------------
st.markdown("<div class='card calendar-card'>", unsafe_allow_html=True)
dibujar_calendario(
    st.session_state.agenda_actual if not st.session_state.agenda_actual.empty else agenda_preview,
    inicio_bloque,
    fin_bloque,
)
st.markdown("</div>", unsafe_allow_html=True)

render_tabla_candidatos(st.session_state.candidatos)