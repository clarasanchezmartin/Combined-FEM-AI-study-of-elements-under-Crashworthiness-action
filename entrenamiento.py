import json
import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split

# Indicar las rutas de cada archivo y carpeta
raiz = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(raiz / ".matplotlib-cache"))

import matplotlib.pyplot as plt

base_datos = raiz / "datos" / "simulaciones.csv"
carpeta_modelos = raiz / "modelos"
carpeta_resultados = raiz / "resultados"

# Clasificar las variables
variables_entrada = ["Radio", "Angulo", "Num_Ag", "Radio_Ag", "Factor_H"]
variables_objetivo = ["SEA", "CFE"]

# limpiar los datos a prueba de errores
def cargar_datos(ruta_csv):

    # Leer la base de datos y convertir en una tabla mediante la librería pandas
    tabla = pd.read_csv(ruta_csv)
    tabla.columns = [columna.strip() for columna in tabla.columns]

    # seleccionar las columnas útiles
    columnas_necesarias = variables_entrada + variables_objetivo

    # filtrar la tabla para eliminar los casos inválidos 
    if "Estado" in tabla.columns:
        filas_erroneas = tabla[tabla["Estado"].astype(str).str.upper().ne("OK")].index
        tabla = tabla.drop(filas_erroneas)

    # convertir las columnas necesarias a formato numérico y las que no se pueda fuerza error
    for columna in columnas_necesarias:
        tabla[columna] = pd.to_numeric(tabla[columna], errors="coerce")

    # eliminar las filas donde falta algún valor (se ha forzado error antes)
    tabla = tabla.dropna(subset=columnas_necesarias)

    # eliminar filas donde las variables objetivo no sean mayores que 0
    filas_objetivo_invalido = tabla[(tabla[variables_objetivo] <= 0).any(axis=1)].index
    tabla = tabla.drop(filas_objetivo_invalido)

    return tabla

# Crear el modelo de ML para entrenar, un XGBoost
def crear_modelo():
    import xgboost as xgb

    model = xgb.XGBRegressor(
        objective="reg:squarederror", # indica que es un problema de regresión
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
    )

    return model


# Guardar una grafica comparando los valores reales con los predichos en test
def guardar_grafica_real_vs_predicho(y_real, y_predicho, objetivo):
    ruta_grafica = carpeta_resultados / f"real_vs_predicho_{objetivo.lower()}.png"
    minimo = min(y_real.min(), y_predicho.min())
    maximo = max(y_real.max(), y_predicho.max())

    plt.figure(figsize=(7, 6))
    plt.scatter(y_real, y_predicho, alpha=0.75, edgecolor="black", linewidth=0.4)
    plt.plot(
        [minimo, maximo],
        [minimo, maximo],
        color="red",
        linestyle="--",
        label="Prediccion perfecta",
    )
    plt.xlabel(f"{objetivo} real")
    plt.ylabel(f"{objetivo} predicho")
    plt.title(f"{objetivo}: real vs predicho")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ruta_grafica, dpi=200)
    plt.close()

    return ruta_grafica

# Entrenar el modelo creado
def entrenar():
    ruta_csv = base_datos.resolve()

    # Crear las carpetas para modelos y resultados si no existían
    carpeta_modelos.mkdir(exist_ok=True)
    carpeta_resultados.mkdir(exist_ok=True)

    # Llamar a la tabla limpia y las variables de entrada que utiliza para aprender
    tabla = cargar_datos(ruta_csv)
    X = tabla[variables_entrada]

    # Para guardar resultados del entrenamiento 
    metricas = [] 
    # Para guardar las rutas de los dos modelos entrenados
    modelos = {}

    # Para cada objetivo entrenar un modelo XGBoost
    for objetivo in variables_objetivo:
        y = tabla[objetivo]
        x_train, x_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
        )

        # Llamar a la función que crea el modelo
        model = crear_modelo()

        # GridSearchCV prueba varias combinaciones
        param_grid = {
            "max_depth": [3, 6, 9],
            "learning_rate": [0.01, 0.1, 0.2],
            "subsample": [0.8, 1.0],
            "colsample_bytree": [0.8, 1.0],
        }
        grid_search = GridSearchCV(
            estimator=model,
            param_grid=param_grid,
            cv=3,
            n_jobs=-1,
        )
        grid_search.fit(x_train, y_train)

        # Guardar los mejores parámetros con métodos de GridSearchCV (de la librería sklearn)
        best_model = grid_search.best_estimator_
        best_params = grid_search.best_params_

        # Usar el modelo para predecir los datos reservados para test
        y_pred = best_model.predict(x_test)
        guardar_grafica_real_vs_predicho(y_test, y_pred, objetivo)

        # Guardar modelo dentro de un archivo en una ruta, y dentro del diccionario de python
        ruta_modelo = carpeta_modelos / f"xgboost_{objetivo.lower()}.joblib"
        joblib.dump(best_model, ruta_modelo)
        modelos[objetivo] = str(ruta_modelo.relative_to(raiz))

        # Guardar lo obtenido en una lista de metricas y calcula valores de R2, MAE y RMSE para evaluar el modelo
        metricas.append(
            {
                "objetivo": objetivo,
                "r2": r2_score(y_test, y_pred),
                "mae": mean_absolute_error(y_test, y_pred),
                "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
                "n_train": len(x_train),
                "n_test": len(x_test),
                "mejores_parametros": json.dumps(best_params),
            }
        )

    # Convertir las métricas en una tabla y lo guarda en un csv
    tabla_metricas = pd.DataFrame(metricas)
    ruta_metricas = carpeta_resultados / "metricas.csv"
    tabla_metricas.to_csv(ruta_metricas, index=False)

    # Crear un diccionario y lo guarda en un archivo .json que se necesita para los resultados
    metadatos = {
        "data_path": str(ruta_csv),
        "feature_columns": variables_entrada,
        "target_columns": variables_objetivo,
        "models": modelos,
        "test_size": 0.2,
        "random_state": 42,
    }
    with (carpeta_modelos / "metadata.json").open("w", encoding="utf-8") as archivo:
        json.dump(metadatos, archivo, indent=2, ensure_ascii=True)
