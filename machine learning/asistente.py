from types import SimpleNamespace
import pandas as pd
from entrenamiento import base_datos, entrenar
from pareto import generar_pareto
from optimizacion import optimizar
from prediccion import predecir


# Preguntar texto por pantalla
def pedir_texto(pregunta, valor_por_defecto=None):
    texto_defecto = f" [{valor_por_defecto}]" if valor_por_defecto else ""
    respuesta = input(f"{pregunta}{texto_defecto}: ").strip()
    return respuesta if respuesta else (valor_por_defecto or "")


# Mostrar un menu para usar los otros archivos sin escribir comandos
def menu_principal():
    while True:
        print("\nOptimizador de geometrías para crashworthiness")
        print("=" * 20)
        print("1. Entrenar modelos")
        print("2. Predecir una geometria")
        print("3. Predecir varias geometrias desde CSV")
        print("4. Buscar mejores geometrias SEA/CFE")
        print("5. Generar frentes de Pareto")
        print("6. Ver metricas")
        print("0. Salir")

        opcion = pedir_texto("Elige una opcion")
        print()

        if opcion == "1":
            print(f"Entrenando con: {base_datos}")
            entrenar()

        elif opcion == "2":
            args = SimpleNamespace(csv=None, output=None)
            predecir(args)

        elif opcion == "3":
            ruta_csv = pedir_texto("CSV con nuevas geometrias")
            ruta_salida = pedir_texto("Archivo de salida", "resultados/predicciones.csv")
            args = SimpleNamespace(csv=ruta_csv, output=ruta_salida)
            predecir(args)

        elif opcion == "4":
            optimizar()

        elif opcion == "5":
            generar_pareto()

        elif opcion == "6":
            metricas = pd.read_csv("resultados/metricas.csv")
            print(metricas.to_string(index=False))

        elif opcion == "0":
            break

        else:
            print("Opcion no valida.")

        input("\nPulsa Enter para continuar...")


if __name__ == "__main__":
    # Ejecutar el asistente
    menu_principal()
