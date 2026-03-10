import pandas as pd
import numpy as np
import os

RUTA_EXCEL = r"C:\Users\dario\Desktop\UNIVERSIDAD\Ingenieria de la salud- UBU\HUBU\Qº FEBRERO.xls"

def cargar_y_limpiar(ruta_excel: str) -> pd.DataFrame:
    bruto = pd.read_excel(ruta_excel, header=None, engine="xlrd")

    columnas_utiles = [
        0, 4, 5, 7, 12, 13, 16, 18, 21, 22, 26, 27, 28,
        29, 30, 31, 32, 33, 34, 35, 36, 37, 38
    ]

    df = bruto.iloc[11:, columnas_utiles].copy()

    df.columns = [
        "paciente_id",
        "servicio",
        "quirofano",
        "centro",
        "fecha",
        "hora_inicio",
        "hora_fin",
        "anestesia",
        "ambulatorio",
        "tipo_caso",
        "turno",
        "progr",
        "impl",
        "dx_codigo",
        "diagnostico",
        "proc_codigo",
        "procedimiento",
        "cirujano_principal",
        "anestesista_principal",
        "suspendida",
        "motivo_suspension",
        "provincia",
        "sector",
    ]

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .replace({"nan": np.nan, "None": np.nan, "": np.nan})
            )

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    df["inicio_dt"] = pd.to_datetime(
        df["fecha"].dt.strftime("%Y-%m-%d") + " " + df["hora_inicio"].astype(str),
        errors="coerce"
    )

    df["fin_dt"] = pd.to_datetime(
        df["fecha"].dt.strftime("%Y-%m-%d") + " " + df["hora_fin"].astype(str),
        errors="coerce"
    )

    cruza_medianoche = df["fin_dt"] < df["inicio_dt"]
    df.loc[cruza_medianoche, "fin_dt"] = df.loc[cruza_medianoche, "fin_dt"] + pd.Timedelta(days=1)

    df["duracion_min"] = (df["fin_dt"] - df["inicio_dt"]).dt.total_seconds() / 60
    df["duracion_horas"] = df["duracion_min"] / 60
    df["es_urgencia"] = df["tipo_caso"].eq("U")
    df["esta_suspendida"] = df["suspendida"].eq("S")

    return df


if __name__ == "__main__":
    print("¿Existe el archivo?:", os.path.exists(RUTA_EXCEL))

    df = cargar_y_limpiar(RUTA_EXCEL)

    print("\n=== RESUMEN INICIAL ===")
    print(f"Filas totales: {len(df)}")
    print(f"Quirófanos detectados: {df['quirofano'].nunique()}")
    print(f"Suspendidas: {df['esta_suspendida'].sum()}")
    print(f"Urgencias: {df['es_urgencia'].sum()}")

    print("\n=== PRIMERAS FILAS ===")
    print(df.head(10).to_string(index=False))

    df.to_csv("quirofano_febrero_limpio.csv", index=False)
    print("\nArchivo generado: quirofano_febrero_limpio.csv")