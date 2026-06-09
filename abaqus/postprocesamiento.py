
from odbAccess import *
from abaqusConstants import *
import os
import numpy as np
import math
import ast
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Fijar la carpeta en la que nos encontramos como directorio base
import inspect
dirbase = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
os.chdir(dirbase)

# Parametros para obtener la masa del cilindro (en mm y kg/m3)
altura_cilindro = 200.0 
espesor_cilindro = 3.0
densidad = 2.77e-09  

inps = 'generacion_inps.py'

# Calcula la masa del tubo segun los parametros
def calcular_masa(radio_cilindro, angulo_taper, num_agujeros, radio_agujero):
    radio_superior = radio_cilindro - altura_cilindro * math.tan(math.radians(angulo_taper))

    # Calcula medidas del cilindro cónico
    generatriz = math.sqrt((radio_superior - radio_cilindro)**2 + altura_cilindro**2)
    area_lateral = math.pi * (radio_cilindro + radio_superior) * generatriz

    # Calcula el area total de los agujeros
    area_agujeros = 0.0
    if num_agujeros > 0:
        area_agujeros = num_agujeros * math.pi * radio_agujero**2

    # Calcula el volumen y la masa del cilindro
    volumen = (area_lateral - area_agujeros) * espesor_cilindro
    masa = volumen * densidad

    return masa

# Toma un ODB y obtiene imagenes con las curvas de los resultados que interesan 
def PostProcessing(radio_cilindro, angulo_taper, num_agujeros, radio_agujero, factor_altura, nombre_odb):

    # Abrir un ODB
    odb = openOdb(path=nombre_odb, readOnly=True)
    step = odb.steps['dyn']

    def extraer_datos(nombre_set, variable, modo):

        # Comprobacion de errores (si no esta el set da error)
        if nombre_set not in odb.rootAssembly.nodeSets:
            raise Exception('No existe el set %s en el ODB %s' % (nombre_set, nombre_odb))

        # Selecciona todos los nodos del set 
        nodos_set = odb.rootAssembly.nodeSets[nombre_set].nodes[0]

        datos = []
        tiempos = []

        # Recorre todos los nodos
        for nodo in nodos_set:
            nombre_region = 'Node CILINDRO-1.%d' % nodo.label

            # Guarda los datos de cada nodo
            if nombre_region in step.historyRegions and variable in step.historyRegions[nombre_region].historyOutputs:
                history_data = step.historyRegions[nombre_region].historyOutputs[variable].data
                datos.append([punto[1] for punto in history_data])

                # Guarda la columna de tiempos solo la primer vez
                if not tiempos:
                    tiempos = [punto[0] for punto in history_data]

        if not datos:  # Control de errores por si no hay datos en el odb
            return [0.0], np.array([0.0])

        # Crear una matriz con todos los puntos
        matriz = np.array(datos)

        if modo == 'media':  # si es la curva del desplazamiento queremos la media entre todos los nodos
            resultado = np.mean(matriz, axis=0)
        else:  # para rf queremos la suma de todos los nodos
            resultado = np.sum(matriz, axis=0)

        return tiempos, resultado

    # Curvas U y RF
    tiempo, u = extraer_datos('SUP', 'U3', 'media')
    _, rf = extraer_datos('BASE', 'RF3', 'suma')

    # ALLIE (Energia Interna)
    # Primero mirar la region en la que se encuentra ALLIE
    region_global = None
    for region in step.historyRegions.values():
        if 'ALLIE' in region.historyOutputs:
            region_global = region
            break
    if region_global is None:
        raise Exception('No existe ALLIE en %s' % nombre_odb)

    # Guardar los puntos de la energia y su tiempo
    allie = [p[1] for p in region_global.historyOutputs['ALLIE'].data]
    tiempo_energia = [p[0] for p in region_global.historyOutputs['ALLIE'].data]

    # Calcular masa y el resto de parametros en las unidades que interesan
    masa = calcular_masa(radio_cilindro, angulo_taper, num_agujeros, radio_agujero)

    # Energia maxima absorbida (en kJ)
    e_max = max(allie) / 1000000.0

    # SEA (en kJ/kg) 
    sea = e_max / masa

    # Fmax (en kN)
    f_max = max(np.abs(rf)) / 1000.0

    # Fmedia (en kN)
    u_max = max(np.abs(u)) / 1000.0  
    f_media = e_max / u_max 

    # CFE
    cfe = f_media / f_max 

    # Indicar carpetas para dejar las graficas y curvas y si no las hay, crearlas
    carpeta_graficas = os.path.join(dirbase, 'graficas')
    carpeta_curvas = os.path.join(dirbase, 'curvas_csv')

    if not os.path.exists(carpeta_graficas):
        os.mkdir(carpeta_graficas)
    if not os.path.exists(carpeta_curvas):
        os.mkdir(carpeta_curvas)

    # nombre unico basado en el odb para nombrar cada imagen
    nombre_base = os.path.splitext(os.path.basename(nombre_odb))[0]

    # Crear un png con la grafica f-d
    plt.figure(figsize=(8, 6))
    plt.plot(np.abs(u), np.abs(rf), 'b-', label='Respuesta')
    plt.xlabel('Desplazamiento |U3| (mm)')
    plt.ylabel('Fuerza |RF3| (N)')
    plt.title('Fuerza vs Desplazamiento')
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(carpeta_graficas, nombre_base + '_fuerza_desplazamiento.png'))
    plt.close()

    # Crear un png con la grafica ALLIE
    plt.figure(figsize=(8, 6))
    plt.plot(tiempo_energia, allie, 'g-')
    plt.xlabel('Tiempo (s)')
    plt.ylabel('Energia (J)')
    plt.title('Energia Interna')
    plt.grid(True)
    plt.savefig(os.path.join(carpeta_graficas, nombre_base + '_energia.png'))
    plt.close()

    # Guardar tambien las curvas en formato tabla csv
    n = min(len(tiempo), len(u), len(rf))
    with open(os.path.join(carpeta_curvas, nombre_base + '_curva_fuerza_desplazamiento.csv'), 'w') as f:
        f.write('Tiempo,U3,RF3\n')
        for j in range(n):
            f.write('%s,%s,%s\n' % (tiempo[j], u[j], rf[j]))

    with open(os.path.join(carpeta_curvas, nombre_base + '_curva_energia.csv'), 'w') as f:
        f.write('Tiempo,ALLIE\n')
        for j in range(len(allie)):
            f.write('%s,%s\n' % (tiempo_energia[j], allie[j]))

    odb.close()

    return masa, e_max, sea, f_max, f_media, cfe


def simulacion(r, a, n_ag, r_ag, factor, i):

    # Nombrar el ODB y guardar la ruta en la que se encuentra
    nombre_odb = 'caso_%03d.odb' % i
    ruta_odb = os.path.join(dirbase, nombre_odb)

    # Valores por defecto por si algo falla
    resultado = [0.0] * 6
    estado = 'OK' # Indica si la simulacion ha salido
    error = '' # Indica cual ha sido el error si no ha salido bien

    try:
        if not os.path.exists(ruta_odb):
            raise Exception('No existe %s' % nombre_odb)
        
        # Guarda todos los resultados que buscamos en un array 
        resultado = PostProcessing(r, a, n_ag, r_ag, factor, ruta_odb)

    except Exception as e:
        estado = 'ERROR'
        error = str(e).replace(',', ';')

    # Escribir los resultados en un csv que se crea solo cuando no esta creado todavia
    csv_file = os.path.join(dirbase, 'dataset_LHS_postprocesado.csv')
    existe = os.path.isfile(csv_file)

    with open(csv_file, 'a') as f:
        if not existe: # Si el archivo no existia, escribir la cabecera 
            f.write('Caso,Radio,Angulo,Num_Ag,Radio_Ag,Factor_H,Masa,E_max,SEA,F_max,F_media,CFE,Estado,Error\n')

        f.write('%d,%0.2f,%0.2f,%d,%0.2f,%0.2f,%s,%s,%s,%s,%s,%s,%s,%s\n' % (
            i, r, a, n_ag, r_ag, factor,
            resultado[0], resultado[1], resultado[2], resultado[3], resultado[4], resultado[5], estado, error))

lhs = [
    [50.03, 0.0, 2, 4.8, 0.64], [51.28, 0.0, 8, 3.89, 0.65], [44.28, 0.0, 2, 3.63, 0.8], [46.35, 0.0, 8, 3.27, 0.67],
    [25.29, 0.0, 0, 0.0, 0.0], [43.72, 0.0, 6, 3.79, 0.79], [27.7, 0.0, 4, 4.84, 0.67], [26.6, 0.0, 6, 5.11, 0.68],
    [49.05, 0.0, 2, 4.02, 0.84], [53.51, 0.0, 6, 4.37, 0.75], [25.47, 0.0, 2, 5.23, 0.8], [50.43, 0.0, 4, 2.48, 0.83],
    [42.54, 0.0, 4, 4.08, 0.76], [46.26, 0.0, 6, 5.08, 0.66], [34.49, 0.0, 6, 3.57, 0.75], [36.17, 0.0, 8, 5.98, 0.62],
    [50.91, 0.0, 6, 2.49, 0.78], [34.61, 0.0, 0, 0.0, 0.0], [35.08, 0.0, 6, 4.98, 0.66], [31.26, 0.0, 0, 0.0, 0.0],
    [44.14, 0.0, 4, 5.68, 0.78], [36.08, 0.0, 2, 3.24, 0.82], [40.66, 0.0, 2, 2.19, 0.77], [29.49, 0.0, 2, 4.06, 0.61],
    [25.8, 0.0, 6, 3.45, 0.74], [32.49, 0.0, 2, 4.29, 0.61], [52.48, 0.0, 2, 4.86, 0.76], [53.16, 0.0, 8, 5.94, 0.72],
    [52.22, 0.0, 6, 3.33, 0.74], [40.46, 0.0, 4, 3.96, 0.7], [39.1, 1.54, 6, 4.95, 0.79], [49.41, 0.75, 8, 4.03, 0.7],
    [45.31, 2.34, 4, 4.34, 0.71], [37.03, 1.93, 4, 5.82, 0.77], [49.92, 2.81, 0, 0.0, 0.0], [41.97, 2.48, 2, 5.5, 0.74],
    [42.83, 1.95, 8, 4.97, 0.66], [29.72, 2.87, 6, 3.05, 0.68], [25.95, 0.31, 6, 3.65, 0.61], [43.67, 1.02, 2, 3.33, 0.78],
    [52.68, 0.78, 0, 0.0, 0.0], [44.64, 1.47, 6, 3.13, 0.79], [46.47, 2.29, 0, 0.0, 0.0], [47.16, 1.1, 6, 4.17, 0.8],
    [43.4, 0.09, 2, 5.8, 0.63], [45.6, 2.75, 6, 5.62, 0.73], [54.13, 0.4, 6, 2.09, 0.72], [52.78, 2.7, 4, 3.76, 0.78],
    [37.38, 0.71, 6, 2.79, 0.64], [28.52, 0.39, 4, 3.0, 0.76], [47.71, 1.88, 2, 5.36, 0.7], [41.14, 2.28, 2, 4.87, 0.75],
    [31.34, 1.42, 8, 2.93, 0.79], [34.8, 2.97, 6, 4.83, 0.75], [53.33, 2.59, 2, 3.25, 0.6], [40.34, 2.56, 0, 0.0, 0.0],
    [28.49, 1.51, 4, 2.34, 0.75], [39.9, 1.61, 8, 5.84, 0.65], [37.29, 2.73, 8, 3.21, 0.69], [27.14, 1.63, 4, 2.63, 0.81],
    [28.76, 1.58, 4, 5.71, 0.79], [37.44, 2.9, 2, 2.7, 0.83], [39.03, 0.07, 6, 5.31, 0.78], [50.86, 2.53, 8, 4.73, 0.81],
    [33.41, 0.4, 8, 3.67, 0.71], [42.37, 2.68, 2, 5.58, 0.63], [53.25, 1.0, 6, 5.67, 0.63], [46.54, 0.05, 0, 0.0, 0.0],
    [32.21, 2.27, 6, 3.93, 0.62], [41.78, 0.44, 4, 5.17, 0.71], [32.71, 1.41, 6, 2.75, 0.65], [38.61, 2.55, 6, 3.08, 0.6],
    [27.98, 2.78, 6, 4.44, 0.65], [38.72, 2.96, 6, 5.75, 0.63], [51.8, 1.27, 6, 4.7, 0.77], [44.82, 0.11, 6, 5.51, 0.77],
    [42.73, 2.74, 8, 2.12, 0.78], [26.24, 0.82, 2, 3.4, 0.68], [53.89, 1.76, 4, 4.64, 0.67], [44.6, 1.38, 4, 4.5, 0.84],
    [32.58, 2.13, 2, 5.57, 0.81], [31.41, 2.17, 2, 2.13, 0.74], [53.47, 0.41, 2, 5.6, 0.72], [52.01, 1.5, 2, 4.78, 0.81],
    [34.38, 0.94, 8, 4.25, 0.83], [52.53, 2.48, 6, 4.45, 0.75], [35.54, 2.02, 8, 5.41, 0.66], [47.3, 1.7, 4, 5.42, 0.68],
    [31.86, 2.13, 0, 0.0, 0.0], [42.08, 2.32, 2, 2.33, 0.82], [40.14, 2.23, 2, 4.01, 0.77], [40.57, 1.83, 4, 3.31, 0.76],
    [34.74, 2.16, 4, 5.92, 0.84], [40.06, 1.03, 2, 2.18, 0.82], [30.07, 1.97, 4, 4.38, 0.69], [43.94, 0.46, 8, 3.81, 0.85],
    [39.69, 0.98, 4, 3.17, 0.69], [30.92, 0.61, 8, 3.19, 0.82], [26.11, 0.71, 4, 4.19, 0.69], [39.46, 1.19, 2, 2.23, 0.63],
    [39.26, 0.96, 8, 3.08, 0.71], [48.94, 2.94, 6, 2.46, 0.8], [31.74, 2.38, 8, 3.02, 0.71], [47.67, 0.99, 2, 4.15, 0.7],
    [28.63, 0.69, 2, 3.62, 0.83], [42.67, 1.73, 2, 5.36, 0.68], [43.53, 1.14, 4, 3.43, 0.84], [30.68, 1.86, 4, 3.98, 0.62],
    [35.63, 0.56, 8, 4.46, 0.65], [46.67, 2.09, 4, 5.99, 0.68], [28.03, 2.63, 2, 2.21, 0.79], [51.68, 2.49, 6, 2.27, 0.74],
    [40.8, 2.44, 6, 3.99, 0.62], [29.94, 2.17, 4, 4.68, 0.61], [52.35, 0.14, 6, 2.69, 0.85], [43.03, 0.42, 6, 3.7, 0.73],
    [53.91, 2.64, 2, 3.88, 0.6], [32.99, 0.95, 2, 4.88, 0.69], [33.0, 0.01, 6, 3.75, 0.63], [31.55, 1.44, 6, 5.88, 0.8],
    [38.85, 1.62, 4, 2.08, 0.68], [46.91, 1.82, 6, 5.6, 0.73], [39.59, 2.4, 0, 0.0, 0.0], [47.87, 1.93, 4, 3.28, 0.71],
    [46.01, 1.39, 8, 5.65, 0.79], [37.56, 0.23, 4, 2.43, 0.69], [36.52, 2.46, 0, 0.0, 0.0], [26.02, 0.92, 2, 5.01, 0.73],
    [37.73, 1.18, 6, 2.59, 0.8], [28.19, 1.07, 4, 3.82, 0.72], [43.19, 1.27, 4, 3.1, 0.79], [29.33, 0.1, 4, 5.26, 0.64],
    [33.97, 0.17, 4, 5.87, 0.75], [51.53, 1.34, 2, 3.51, 0.82], [27.33, 2.42, 4, 5.22, 0.75], [48.89, 0.34, 8, 3.35, 0.78],
    [41.5, 0.83, 2, 5.27, 0.85], [31.96, 2.15, 4, 4.31, 0.8], [49.2, 1.26, 0, 0.0, 0.0], [33.59, 2.89, 4, 5.49, 0.79],
    [36.25, 2.1, 6, 4.41, 0.64], [37.15, 1.95, 2, 2.89, 0.78], [35.38, 0.8, 2, 5.73, 0.76], [27.09, 0.28, 2, 4.28, 0.69],
    [54.49, 1.23, 4, 5.25, 0.7], [38.05, 0.76, 6, 5.14, 0.71], [53.63, 0.56, 8, 4.9, 0.69], [44.75, 1.15, 4, 3.4, 0.64],
    [54.62, 1.07, 4, 2.86, 0.78], [54.74, 1.79, 2, 4.26, 0.61], [29.09, 2.86, 0, 0.0, 0.0], [30.46, 2.44, 4, 2.11, 0.62],
    [50.64, 0.37, 0, 0.0, 0.0], [30.25, 2.99, 2, 4.71, 0.73], [44.96, 0.27, 6, 2.85, 0.64], [45.9, 1.64, 2, 2.22, 0.61],
    [47.48, 0.69, 2, 2.66, 0.61], [25.73, 0.53, 2, 3.48, 0.73], [26.74, 0.35, 2, 4.75, 0.71], [26.41, 2.06, 6, 3.91, 0.67],
    [29.59, 2.2, 4, 3.53, 0.76], [40.94, 2.69, 8, 2.88, 0.72], [38.28, 1.69, 4, 3.59, 0.72], [38.42, 0.78, 6, 4.61, 0.76],
    [27.71, 2.58, 0, 0.0, 0.0], [34.95, 2.19, 0, 0.0, 0.0], [48.67, 1.74, 6, 3.04, 0.69], [53.76, 0.6, 4, 2.98, 0.82],
    [46.78, 1.12, 6, 5.52, 0.61], [47.93, 0.54, 6, 5.38, 0.81], [29.25, 2.53, 6, 4.1, 0.76], [30.75, 2.07, 6, 3.48, 0.67],
    [33.67, 2.1, 6, 5.04, 0.76], [35.72, 0.29, 6, 4.66, 0.65], [38.33, 2.24, 4, 5.47, 0.7], [26.83, 2.62, 6, 4.05, 0.62],
    [52.14, 1.08, 8, 5.71, 0.8], [33.12, 0.72, 0, 0.0, 0.0], [50.31, 1.97, 2, 5.2, 0.84], [38.57, 0.89, 2, 2.44, 0.78],
    [53.08, 0.96, 0, 0.0, 0.0], [49.18, 0.02, 6, 4.95, 0.75], [50.71, 1.87, 6, 4.2, 0.71], [35.92, 1.6, 0, 0.0, 0.0],
    [32.67, 0.89, 2, 5.39, 0.62], [41.81, 1.21, 6, 4.11, 0.68], [52.98, 0.91, 8, 5.33, 0.67], [25.1, 1.53, 2, 2.31, 0.73],
    [31.62, 0.63, 2, 5.0, 0.6], [29.17, 1.15, 6, 5.06, 0.66], [35.14, 1.21, 4, 5.54, 0.65], [42.96, 0.14, 4, 2.38, 0.78],
    [54.0, 0.52, 4, 4.09, 0.78], [52.82, 0.19, 4, 3.86, 0.72], [49.58, 1.03, 4, 5.29, 0.71], [32.03, 2.03, 2, 4.74, 0.77],
    [41.37, 0.32, 6, 3.26, 0.71], [32.32, 1.49, 4, 3.0, 0.67], [47.56, 2.91, 8, 3.78, 0.65], [35.85, 2.79, 4, 2.02, 0.61],
    [32.83, 2.24, 2, 4.53, 0.69], [34.01, 0.58, 8, 5.44, 0.79], [26.97, 2.71, 6, 4.31, 0.66], [25.51, 2.2, 2, 2.5, 0.83],
    [41.02, 3.0, 8, 3.19, 0.74], [27.49, 1.05, 8, 3.95, 0.7], [37.68, 1.71, 0, 0.0, 0.0], [48.32, 1.88, 0, 0.0, 0.0],
    [45.67, 1.76, 4, 4.56, 0.77], [49.8, 1.98, 2, 2.97, 0.81], [32.11, 0.68, 2, 5.46, 0.82], [51.15, 0.86, 4, 2.32, 0.68],
    [25.39, 1.67, 6, 2.92, 0.61], [47.37, 0.46, 2, 2.53, 0.73], [26.56, 0.45, 4, 5.02, 0.62], [46.11, 0.36, 4, 4.53, 0.76],
    [40.22, 0.27, 4, 4.42, 0.65], [28.28, 2.37, 4, 3.72, 0.76], [44.47, 2.66, 2, 5.43, 0.68], [42.26, 1.67, 4, 3.54, 0.8],
    [51.41, 1.09, 0, 0.0, 0.0], [39.39, 0.64, 6, 4.77, 0.8], [48.55, 1.23, 6, 2.74, 0.64], [33.24, 0.65, 4, 4.6, 0.63],
    [36.37, 1.31, 0, 0.0, 0.0], [45.24, 2.93, 2, 3.9, 0.83], [27.3, 2.38, 0, 0.0, 0.0], [34.19, 1.59, 0, 0.0, 0.0],
    [30.57, 1.83, 4, 5.84, 0.62], [28.83, 2.29, 2, 2.56, 0.77], [34.55, 1.56, 6, 5.63, 0.73], [45.48, 2.01, 2, 5.78, 0.84],
    [37.91, 2.69, 2, 2.6, 0.7], [54.52, 1.91, 4, 3.5, 0.63], [49.68, 0.21, 4, 5.96, 0.67], [28.38, 0.88, 8, 4.93, 0.7],
    [30.8, 0.16, 2, 3.83, 0.82], [50.15, 1.8, 8, 2.71, 0.84], [39.78, 2.25, 4, 2.91, 0.69], [50.59, 0.73, 6, 2.06, 0.84],
    [36.91, 1.36, 6, 2.01, 0.79], [27.81, 1.32, 8, 2.26, 0.77], [47.01, 2.91, 6, 5.12, 0.64], [51.88, 1.37, 2, 5.74, 0.72],
    [46.89, 2.77, 2, 3.14, 0.66], [50.27, 0.85, 8, 4.13, 0.63], [54.98, 0.49, 6, 5.34, 0.81], [31.19, 1.57, 0, 0.0, 0.0],
    [35.43, 1.65, 4, 3.59, 0.63], [48.73, 1.12, 8, 2.43, 0.79], [42.1, 1.04, 0, 0.0, 0.0], [25.65, 2.34, 2, 2.25, 0.82],
    [41.66, 0.06, 6, 2.57, 0.82], [45.19, 1.84, 0, 0.0, 0.0], [48.09, 1.16, 2, 3.31, 0.66], [37.86, 2.67, 0, 0.0, 0.0],
    [41.42, 2.82, 0, 0.0, 0.0], [43.31, 2.83, 6, 3.6, 0.69], [33.77, 0.49, 2, 2.88, 0.75], [49.83, 2.51, 6, 2.65, 0.82],
    [31.07, 1.33, 0, 0.0, 0.0], [42.48, 0.62, 6, 5.79, 0.81], [51.06, 1.72, 6, 4.64, 0.72], [40.87, 0.02, 6, 2.4, 0.67],
    [29.88, 0.5, 2, 4.81, 0.62], [36.68, 1.37, 4, 3.69, 0.68], [33.89, 2.21, 4, 3.84, 0.65], [51.35, 0.55, 4, 5.18, 0.85],
    [35.24, 2.8, 8, 4.61, 0.72], [34.23, 0.03, 2, 4.57, 0.84], [36.5, 2.3, 0, 0.0, 0.0], [36.85, 1.24, 4, 3.16, 0.74],
    [49.33, 0.12, 6, 2.8, 0.74], [38.94, 0.83, 0, 0.0, 0.0], [45.8, 0.8, 4, 4.21, 0.65], [25.13, 0.66, 6, 5.16, 0.83],
    [43.85, 1.77, 6, 5.92, 0.66], [54.4, 0.25, 2, 2.37, 0.74], [44.03, 2.79, 0, 0.0, 0.0], [45.93, 0.38, 6, 3.75, 0.85],
    [51.97, 2.94, 2, 5.76, 0.73], [39.94, 0.84, 4, 3.38, 0.81], [30.36, 1.28, 2, 2.16, 0.83], [45.01, 1.53, 6, 3.05, 0.61],
    [38.15, 2.4, 4, 5.09, 0.83], [27.54, 1.35, 2, 2.55, 0.62], [33.3, 0.16, 0, 0.0, 0.0], [30.1, 1.91, 4, 4.83, 0.72],
    [48.14, 1.9, 2, 2.13, 0.81], [44.3, 2.56, 2, 3.42, 0.83], [28.99, 1.8, 6, 2.05, 0.67], [48.27, 2.76, 2, 4.49, 0.66],
    [29.66, 0.64, 2, 5.56, 0.81], [41.22, 2.12, 8, 4.57, 0.64], [36.78, 2.57, 0, 0.0, 0.0], [48.41, 1.48, 8, 2.79, 0.64],
    [54.89, 0.1, 4, 4.23, 0.63], [43.23, 0.22, 0, 0.0, 0.0], [54.21, 1.17, 4, 4.91, 0.75], [26.32, 1.61, 4, 2.62, 0.73]
]


# Si existe un csv anterior, se borra para no duplicar resultados
if os.path.exists(os.path.join(dirbase, 'dataset_LHS_postprocesado.csv')):
    os.remove(os.path.join(dirbase, 'dataset_LHS_postprocesado.csv'))

# Bucle por todos los odbs
for i, caso in enumerate(lhs):
        simulacion(caso[0], caso[1], caso[2], caso[3], caso[4], i + 1)

