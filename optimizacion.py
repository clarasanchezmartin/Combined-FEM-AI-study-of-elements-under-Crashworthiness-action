import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

# Indicar las rutas de cada archivo y carpeta
raiz = Path(__file__).resolve().parent
carpeta_modelos = raiz / "modelos"
resultados = raiz / "resultados"
ruta_metadatos = carpeta_modelos / "metadata.json"

# Valores fijos para la busqueda de geometrias con NSGA-II
poblacion = 200
generaciones = 200
cantidad_mejores = 10
peso_sea = 0.5
peso_cfe = 0.5
semilla = 42

# Limites elegidos para las variables de geometria
limite_inferior = np.array([25.0, 0.0, 0.0, 2.0, 0.60], dtype=float)
limite_superior = np.array([55.0, 3.0, 8.0, 6.0, 0.85], dtype=float)
valores_num_ag = [0, 2, 4, 6, 8]


# Cargar el archivo metadata.json que se crea al entrenar
def cargar_metadatos():
    with ruta_metadatos.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


# Cargar las simulaciones reales que se usaron para entrenar
def cargar_datos_entrenamiento_validos(metadatos=None):
    metadatos = metadatos or cargar_metadatos()
    tabla = pd.read_csv(metadatos["data_path"])

    # Quedarse solo con simulaciones correctas
    if "Estado" in tabla.columns:
        tabla = tabla[tabla["Estado"].astype(str).str.upper().eq("OK")]

    # Quedarse solo con resultados positivos
    tabla = tabla[(tabla[["SEA", "CFE"]] > 0).all(axis=1)]
    return tabla


# Convertir los numeros que crea NSGA-II en una geometria valida
def decodificar_geometrias(valores, valores_num_ag):
    valores = np.atleast_2d(valores)
    num_ag_permitidos = np.array(valores_num_ag)
    num_ag_cercano = num_ag_permitidos[
        np.abs(valores[:, 2, None] - num_ag_permitidos).argmin(axis=1)
    ]

    candidatos = pd.DataFrame(
        {
            "Radio": np.round(valores[:, 0], 2),
            "Angulo": np.round(valores[:, 1], 2),
            "Num_Ag": num_ag_cercano.astype(int),
            "Radio_Ag": np.round(valores[:, 3], 2),
            "Factor_H": np.round(valores[:, 4], 2),
        }
    )

    # Si no hay agujeros, Radio_Ag y Factor_H se ponen a cero
    sin_agujeros = candidatos["Num_Ag"].eq(0)
    candidatos.loc[sin_agujeros, ["Radio_Ag", "Factor_H"]] = 0.0

    return candidatos


# Usar NSGA-II para buscar geometrias buenas en SEA y CFE a la vez
def generar_predicciones_nsga2(tabla, metadatos, devolver_todas=False):
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize

    variables_entrada = metadatos["feature_columns"]
    columnas_geometria = ["Radio", "Angulo", "Num_Ag", "Radio_Ag", "Factor_H"]

    # Si se necesita el Pareto, guardar todas las geometrias evaluadas durante la busqueda
    predicciones_generadas = []

    # Cargar los modelos entrenados para predecir SEA y CFE
    models = {
        objetivo: joblib.load(raiz / ruta_modelo)
        for objetivo, ruta_modelo in metadatos["models"].items()
    }

    class ProblemaGeometria(Problem):
        # pymoo necesita saber cuantas variables y objetivos tiene el problema
        def __init__(self):
            super().__init__(n_var=5, n_obj=2, xl=limite_inferior, xu=limite_superior)

        def _evaluate(self, X, out, *args, **kwargs):
            candidatos = decodificar_geometrias(X, valores_num_ag)
            entradas_modelo = candidatos[variables_entrada]

            pred_sea = models["SEA"].predict(entradas_modelo)
            pred_cfe = models["CFE"].predict(entradas_modelo)

            # Para el Pareto interesa conservar todos los candidatos que evalua NSGA-II
            if devolver_todas:
                predicciones_lote = candidatos.copy()
                predicciones_lote["pred_SEA"] = pred_sea
                predicciones_lote["pred_CFE"] = pred_cfe
                predicciones_generadas.append(predicciones_lote)

            # pymoo minimiza, por eso se ponen negativos para maximizar SEA y CFE
            out["F"] = np.column_stack([-pred_sea, -pred_cfe])

    resultado = minimize(
        ProblemaGeometria(),
        NSGA2(pop_size=poblacion),
        ("n_gen", generaciones),
        seed=semilla,
        verbose=False,
    )

    # En Pareto se devuelven todas las geometrias evaluadas, sin repetir la misma geometria
    if devolver_todas:
        predicciones = pd.concat(predicciones_generadas, ignore_index=True)
        predicciones = predicciones.drop_duplicates(subset=columnas_geometria).reset_index(drop=True)
        return predicciones

    # En optimizacion solo se devuelven las geometrias finales de la ultima poblacion
    candidatos = decodificar_geometrias(resultado.pop.get("X"), valores_num_ag)
    candidatos = candidatos.drop_duplicates().reset_index(drop=True)
    X = candidatos[variables_entrada]
    candidatos["pred_SEA"] = models["SEA"].predict(X)
    candidatos["pred_CFE"] = models["CFE"].predict(X)

    return candidatos


# Crear una puntuacion conjunta mezclando SEA y CFE
def agregar_puntuacion(predicciones, referencia=None, peso_sea_usado=peso_sea, peso_cfe_usado=peso_cfe):
    resultado = predicciones.copy()

    sea = resultado["pred_SEA"]
    cfe = resultado["pred_CFE"]

    if referencia is None:
        referencia_sea = sea
        referencia_cfe = cfe
    else:
        referencia_sea = pd.concat([sea, referencia["SEA"]], ignore_index=True)
        referencia_cfe = pd.concat([cfe, referencia["CFE"]], ignore_index=True)

    min_sea = referencia_sea.min()
    max_sea = referencia_sea.max()
    min_cfe = referencia_cfe.min()
    max_cfe = referencia_cfe.max()
    rango_sea = max_sea - min_sea
    rango_cfe = max_cfe - min_cfe

    # Pasar SEA y CFE a escala 0-1 para poder mezclarlos
    resultado["score_SEA"] = 1.0 if rango_sea == 0 else (sea - min_sea) / rango_sea
    resultado["score_CFE"] = 1.0 if rango_cfe == 0 else (cfe - min_cfe) / rango_cfe
    resultado["score_total"] = (
        peso_sea_usado * resultado["score_SEA"] + peso_cfe_usado * resultado["score_CFE"]
    )

    return resultado.sort_values("score_total", ascending=False)


# Buscar las mejores geometrias usando NSGA-II
def optimizar():
    metadatos = cargar_metadatos()
    tabla = cargar_datos_entrenamiento_validos(metadatos)

    predicciones = generar_predicciones_nsga2(tabla, metadatos)
    ranking = agregar_puntuacion(predicciones, referencia=tabla)
    ranking = ranking.drop_duplicates(subset=["pred_SEA", "pred_CFE"]).reset_index(drop=True)

    resultados.mkdir(exist_ok=True)
    ruta_mejores = resultados / "mejores_geometrias.csv"
    columnas_salida = [
        "Radio",
        "Angulo",
        "Num_Ag",
        "Radio_Ag",
        "Factor_H",
        "pred_SEA",
        "pred_CFE",
        "score_total",
    ]
    ranking.head(cantidad_mejores)[columnas_salida].to_csv(ruta_mejores, index=False)

    print("Optimizacion terminada. Resultados guardados en la carpeta resultados.")
    print(ranking[columnas_salida].head(cantidad_mejores).to_string(index=False))
