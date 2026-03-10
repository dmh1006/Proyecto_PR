from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "Data" / "quirofano_febrero_limpio.csv"


def cargar_datos() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["fecha", "inicio_dt", "fin_dt"])
    return df


def filtrar_cirugias_reales(df: pd.DataFrame) -> pd.DataFrame:
    return df[~df["esta_suspendida"]].copy()


def analisis_procedimientos(df_real: pd.DataFrame) -> pd.DataFrame:
    stats = (
        df_real.groupby("procedimiento")
        .agg(
            n_cirugias=("procedimiento", "count"),
            duracion_media=("duracion_min", "mean"),
            duracion_mediana=("duracion_min", "median"),
            desviacion=("duracion_min", "std")
        )
        .sort_values("n_cirugias", ascending=False)
        .round(2)
    )

    print("\n=== TOP PROCEDIMIENTOS ===")
    print(stats.head(15).to_string())

    return stats


def uso_quirofanos(df_real: pd.DataFrame) -> pd.Series:
    uso = df_real["quirofano"].value_counts()

    print("\n=== USO DE QUIROFANOS ===")
    print(uso.to_string())

    return uso


def tiempos_muertos(df_real: pd.DataFrame) -> pd.DataFrame:
    df_gap = df_real.sort_values(["quirofano", "fecha", "inicio_dt"]).copy()

    df_gap["fin_anterior"] = df_gap.groupby(["quirofano", "fecha"])["fin_dt"].shift(1)

    df_gap["tiempo_muerto"] = (
        df_gap["inicio_dt"] - df_gap["fin_anterior"]
    ).dt.total_seconds() / 60

    tiempo_medio = df_gap["tiempo_muerto"].dropna().mean()

    print("\n=== TIEMPO MUERTO MEDIO ENTRE CIRUGIAS (MISMO DIA) ===")
    print(round(tiempo_medio, 2), "min")

    return df_gap


def normalizar_procedimiento(texto: str) -> str:
    if pd.isna(texto):
        return "DESCONOCIDO"

    texto = str(texto).strip().upper()

    reemplazos = {
        "APENDICECTOMIA POR LAPAROSCOPIA": "APENDICECTOMIA LAPAROSCOPICA",
        "APENDICECTOMIA LAPAROSCOPICA": "APENDICECTOMIA LAPAROSCOPICA",
        "RESECCION DE VESICULA BILIAR, ABORDAJE ENDOSCOPICO PERCUTA": "COLECISTECTOMIA LAPAROSCOPICA",
        "SUPLEMENTO EN REGION INGUINAL, DERECHA, CON SUSTITUTO SINT": "HERNIA INGUINAL DERECHA",
        "SUPLEMENTO EN REGION INGUINAL, IZQUIERDA, CON SUSTITUTO SI": "HERNIA INGUINAL IZQUIERDA",
        "SUPLEMENTO EN REGION INGUINAL, BILATERAL, CON SUSTITUTO S": "HERNIA INGUINAL BILATERAL",
    }

    return reemplazos.get(texto, texto)


def preparar_dataset_funcional(df: pd.DataFrame) -> pd.DataFrame:
    df_real = filtrar_cirugias_reales(df)
    df_real["procedimiento_base"] = df_real["procedimiento"].apply(normalizar_procedimiento)
    return df_real


def construir_catalogo_quirurgico(df_real: pd.DataFrame) -> pd.DataFrame:
    catalogo = (
        df_real.groupby("procedimiento_base")
        .agg(
            n_casos=("procedimiento_base", "count"),
            duracion_media_min=("duracion_min", "mean"),
            duracion_mediana_min=("duracion_min", "median"),
            desviacion_min=("duracion_min", "std"),
            quirofanos_habituales=("quirofano", lambda x: ", ".join(sorted(set(x.astype(str)))))
        )
        .sort_values("n_casos", ascending=False)
        .round(2)
        .reset_index()
    )

    # Estimación operativa simple
    catalogo["prep_min"] = 15
    catalogo["post_min"] = 10
    catalogo["buffer_variabilidad_min"] = (
        catalogo["desviacion_min"].fillna(0) * 0.5
    ).round(0)

    catalogo["duracion_planificable_min"] = (
        catalogo["duracion_mediana_min"].fillna(0)
        + catalogo["prep_min"]
        + catalogo["post_min"]
        + catalogo["buffer_variabilidad_min"]
    ).round(0)

    return catalogo


def obtener_ficha_procedimiento(catalogo: pd.DataFrame, procedimiento: str) -> pd.Series:
    proc_norm = normalizar_procedimiento(procedimiento)
    fila = catalogo[catalogo["procedimiento_base"] == proc_norm]

    if fila.empty:
        raise ValueError(f"No se encontró el procedimiento: {procedimiento}")

    return fila.iloc[0]


def estimar_nueva_cirugia(catalogo: pd.DataFrame, procedimiento: str) -> dict:
    ficha = obtener_ficha_procedimiento(catalogo, procedimiento)

    return {
        "procedimiento": ficha["procedimiento_base"],
        "n_casos_historicos": int(ficha["n_casos"]),
        "duracion_mediana_min": float(ficha["duracion_mediana_min"]),
        "prep_min": float(ficha["prep_min"]),
        "post_min": float(ficha["post_min"]),
        "buffer_variabilidad_min": float(ficha["buffer_variabilidad_min"]),
        "duracion_planificable_min": float(ficha["duracion_planificable_min"]),
        "quirofanos_habituales": ficha["quirofanos_habituales"],
    }


def main():
    df = cargar_datos()
    df_real = filtrar_cirugias_reales(df)

    print("\n=== DATASET ===")
    print(len(df), "registros totales")
    print(len(df_real), "cirugías reales")

    analisis_procedimientos(df_real)
    uso_quirofanos(df_real)
    tiempos_muertos(df_real)

    print("\n=== CATALOGO QUIRURGICO ===")
    df_funcional = preparar_dataset_funcional(df)
    catalogo = construir_catalogo_quirurgico(df_funcional)
    print(catalogo.head(10).to_string(index=False))

    print("\n=== EJEMPLO ESTIMACION NUEVA CIRUGIA ===")
    ejemplo = estimar_nueva_cirugia(catalogo, "APENDICECTOMIA LAPAROSCOPICA")
    print(ejemplo)


if __name__ == "__main__":
    main()