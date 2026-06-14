import os
from pathlib import Path

import pandas as pd

# Indicar las rutas de cada archivo y carpeta
raiz = Path(__file__).resolve().parent
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(raiz / ".matplotlib-cache"))

import matplotlib.pyplot as plt

datos = raiz / "datos" / "simulaciones.csv"
resultados = raiz / "resultados"

# Columnas que se van a usar para el analisis
columnas = [
    "Radio",
    "Angulo",
    "Num_Ag",
    "Radio_Ag",
    "Factor_H",
    "Masa",
    "E_max",
    "F_max",
    "F_media",
    "SEA",
    "CFE",
]


# Cargar los datos y eliminar casos no validos
def cargar_datos():
    tabla = pd.read_csv(datos)
    tabla.columns = [columna.strip() for columna in tabla.columns]

    # Quedarse solo con simulaciones correctas
    if "Estado" in tabla.columns:
        tabla = tabla[tabla["Estado"].astype(str).str.upper().eq("OK")]

    # Convertir las columnas a numeros y eliminar filas incompletas
    for columna in columnas:
        tabla[columna] = pd.to_numeric(tabla[columna], errors="coerce")

    tabla = tabla.dropna(subset=columnas)
    tabla = tabla[(tabla[["SEA", "CFE"]] > 0).all(axis=1)]

    return tabla


# Generar las graficas de analisis usadas en el TFM
def generar_analisis():
    resultados.mkdir(exist_ok=True)
    tabla = cargar_datos()

    # Matriz de correlacion entre variables
    correlacion = tabla[columnas].corr()
    plt.figure(figsize=(8, 6))
    imagen = plt.imshow(correlacion, cmap="viridis", vmin=-1, vmax=1)
    plt.colorbar(imagen, label="Coeficiente de correlación")
    plt.xticks(range(len(columnas)), columnas, rotation=90)
    plt.yticks(range(len(columnas)), columnas)
    plt.title("Matriz de correlación")
    plt.tight_layout()
    plt.savefig(resultados / "matriz_correlacion.png", dpi=180)
    plt.close()

    # Influencia del radio sobre el SEA
    plt.figure(figsize=(8, 5))
    plt.scatter(tabla["Radio"], tabla["SEA"], alpha=0.75)
    plt.xlabel("Radio (mm)")
    plt.ylabel("SEA (kJ/kg)")
    plt.title("Influencia de Radio sobre SEA")
    plt.tight_layout()
    plt.savefig(resultados / "influencia_radio_sea.png", dpi=180)
    plt.close()

    # Influencia del radio sobre el CFE
    plt.figure(figsize=(8, 5))
    plt.scatter(tabla["Radio"], tabla["CFE"], alpha=0.75)
    plt.xlabel("Radio (mm)")
    plt.ylabel("CFE")
    plt.title("Influencia de Radio sobre CFE")
    plt.tight_layout()
    plt.savefig(resultados / "influencia_radio_cfe.png", dpi=180)
    plt.close()

    # Relacion entre SEA y CFE
    plt.figure(figsize=(8, 5))
    plt.scatter(tabla["SEA"], tabla["CFE"], alpha=0.75)
    plt.xlabel("SEA")
    plt.ylabel("CFE")
    plt.title("Relación entre SEA y CFE")
    plt.tight_layout()
    plt.savefig(resultados / "relacion_sea_cfe.png", dpi=180)
    plt.close()


if __name__ == "__main__":
    generar_analisis()
