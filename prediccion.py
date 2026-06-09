import json
from pathlib import Path
import joblib
import pandas as pd


# Indicar las rutas de cada archivo y carpeta
raiz = Path(__file__).resolve().parent
carpeta_modelos = raiz / "modelos"
ruta_metadatos = carpeta_modelos / "metadata.json"


# Cargar el archivo metadata.json que se crea al entrenar
def cargar_metadatos():
    with ruta_metadatos.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


# Pedir manualmente una geometria para predecir
def pedir_geometria(variables_entrada):
    fila = {}
    print("Introduce los valores de la geometria:")
    for variable in variables_entrada:
        fila[variable] = float(input(f"{variable}: ").replace(",", "."))
    return pd.DataFrame([fila])


# Preparar la geometria nueva que se va a predecir
def preparar_entrada(args, variables_entrada):
    # Si se introduce un CSV, leerlo y quedarse con las variables de entrada
    if args.csv:
        return pd.read_csv(args.csv)[variables_entrada]

    # Si no se introduce nada, pedir los datos por pantalla
    return pedir_geometria(variables_entrada)


# Cargar los modelos entrenados y hacer las predicciones
def predecir(args):
    # Leer qué columnas usa el modelo y dónde están guardados los modelos
    metadatos = cargar_metadatos()
    variables_entrada = metadatos["feature_columns"]
    X = preparar_entrada(args, variables_entrada)

    # Copiar la geometria para añadirle después las predicciones
    predicciones = X.copy()

    # Cargar cada modelo (el de SEA y el de CFE)y predecir su objetivo correspondiente
    for objetivo, ruta_modelo in metadatos["models"].items():
        model = joblib.load(raiz / ruta_modelo)
        predicciones[f"pred_{objetivo}"] = model.predict(X)

    # Guardar las predicciones en CSV si se indica una ruta, o mostrarlas por pantalla
    if args.output:
        predicciones.to_csv(args.output, index=False)
        print("Prediccion terminada. Resultados guardados.")
    else:
        print(predicciones.to_string(index=False))
