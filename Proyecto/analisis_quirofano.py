from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "Data" / "quirofano_febrero_limpio.csv"


def cargar_datos():
    df = pd.read_csv(DATA_PATH, parse_dates=["inicio_dt", "fin_dt"])
    return df


def analisis_procedimientos(df):

    stats = (
        df.groupby("procedimiento")
        .agg(
            n_cirugias=("procedimiento", "count"),
            duracion_media=("duracion_min", "mean"),
            duracion_mediana=("duracion_min", "median"),
            desviacion=("duracion_min", "std")
        )
        .sort_values("n_cirugias", ascending=False)
    )

    print("\n=== TOP PROCEDIMIENTOS ===")
    print(stats.head(15))

    return stats


def uso_quirofanos(df):

    uso = df["quirofano"].value_counts()

    print("\n=== USO DE QUIROFANOS ===")
    print(uso)

    return uso


def tiempos_muertos(df):

    df = df.sort_values(["quirofano", "inicio_dt"])

    df["fin_anterior"] = df.groupby("quirofano")["fin_dt"].shift(1)

    df["tiempo_muerto"] = (
        df["inicio_dt"] - df["fin_anterior"]
    ).dt.total_seconds() / 60

    print("\n=== TIEMPO MUERTO MEDIO ENTRE CIRUGIAS ===")
    print(df["tiempo_muerto"].mean())

    return df


def main():

    df = cargar_datos()

    print("\n=== DATASET ===")
    print(len(df), "cirugías")

    analisis_procedimientos(df)

    uso_quirofanos(df)

    tiempos_muertos(df)


if __name__ == "__main__":
    main()