import os

import numpy as np
import pandas as pd

from optimizacion import (
    agregar_puntuacion,
    cargar_datos_entrenamiento_validos,
    cargar_metadatos,
    generar_predicciones_nsga2,
    raiz,
    resultados,
)

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(raiz / ".matplotlib-cache"))

import matplotlib.pyplot as plt


# Calcular las soluciones que pertenecen al frente de Pareto
def frente_pareto(tabla, columna_sea, columna_cfe):
    ordenada = tabla.sort_values([columna_sea, columna_cfe], ascending=[False, False])
    indices_pareto = []
    mejor_cfe = float("-inf")

    # Una fila entra si mejora el mejor CFE visto hasta ese momento
    for indice, fila in ordenada.iterrows():
        if fila[columna_cfe] > mejor_cfe:
            indices_pareto.append(indice)
            mejor_cfe = fila[columna_cfe]

    return tabla.loc[indices_pareto].sort_values(columna_sea, ascending=False).reset_index(drop=True)


# Dibujar los puntos y la linea del frente de Pareto
def dibujar_pareto(puntos, pareto, columna_sea, columna_cfe, nombre_salida, titulo, etiqueta_puntos):
    ruta_salida = resultados / nombre_salida
    pareto_ordenado = pareto.sort_values(columna_sea)
    puntos_agrupados = (
        puntos.groupby([columna_sea, columna_cfe], as_index=False)
        .size()
        .rename(columns={"size": "repeticiones"})
    )
    tamano_puntos = 28 + 10 * np.sqrt(puntos_agrupados["repeticiones"])

    plt.figure(figsize=(8, 6))
    plt.scatter(
        puntos_agrupados[columna_sea],
        puntos_agrupados[columna_cfe],
        s=tamano_puntos,
        alpha=0.42,
        color="tab:blue",
        edgecolors="white",
        linewidths=0.45,
        label=etiqueta_puntos,
        zorder=1,
    )
    plt.plot(
        pareto_ordenado[columna_sea],
        pareto_ordenado[columna_cfe],
        color="red",
        linewidth=1.7,
        label="Frente de Pareto",
        zorder=2,
    )
    plt.scatter(
        pareto_ordenado[columna_sea],
        pareto_ordenado[columna_cfe],
        s=18,
        color="red",
        edgecolors="red",
        linewidths=0.2,
        zorder=3,
    )
    plt.xlabel(columna_sea)
    plt.ylabel(columna_cfe)
    plt.title(titulo)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=180)
    plt.close()

    return ruta_salida


# Calcular el Pareto usando las simulaciones reales
def calcular_pareto_real(tabla):
    pareto = frente_pareto(tabla, "SEA", "CFE")
    pareto = pareto.rename(columns={"SEA": "pred_SEA", "CFE": "pred_CFE"})
    pareto = agregar_puntuacion(pareto)
    return pareto.rename(columns={"pred_SEA": "SEA", "pred_CFE": "CFE"})


# Generar el Pareto real y el Pareto predicho
def generar_pareto():
    metadatos = cargar_metadatos()
    tabla = cargar_datos_entrenamiento_validos(metadatos)
    resultados.mkdir(exist_ok=True)

    pareto_real = calcular_pareto_real(tabla)
    pareto_real.to_csv(resultados / "frente_pareto_real_sea_cfe.csv", index=False)
    dibujar_pareto(
        tabla,
        pareto_real,
        "SEA",
        "CFE",
        "frente_pareto_real_sea_cfe.png",
        "Frente de Pareto real: simulaciones Abaqus",
        "Simulaciones reales",
    )

    predicciones = generar_predicciones_nsga2(tabla, metadatos, devolver_todas=True)
    predicciones.to_csv(resultados / "predicciones_nsga2_sea_cfe.csv", index=False)

    pareto_predicho = frente_pareto(predicciones, "pred_SEA", "pred_CFE")
    pareto_predicho = agregar_puntuacion(pareto_predicho, referencia=tabla)

    pareto_predicho.to_csv(resultados / "frente_pareto_predicho_sea_cfe.csv", index=False)
    dibujar_pareto(
        predicciones,
        pareto_predicho,
        "pred_SEA",
        "pred_CFE",
        "frente_pareto_predicho_sea_cfe.png",
        "Frente de Pareto predicho: NSGA-II",
        "Geometrias evaluadas por NSGA-II",
    )

    print("Pareto terminado. Resultados guardados en la carpeta resultados.")
