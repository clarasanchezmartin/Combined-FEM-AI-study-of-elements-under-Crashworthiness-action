# Estudio combinado FEM-IA de elementos sometidos a cargas de impacto

Trabajo de Fin de Máster centrado en la automatización de simulaciones mediante Abaqus y Python, y en el uso de los resultados obtenidos para entrenar un modelo predictivo de inteligencia artificial. El objetivo es analizar y optimizar el comportamiento de geometrías tubulares frente a cargas de impacto mediante criterios de *crashworthiness*.

Nota: el archivo analisis.py se ha utilizado como script auxiliar para la generación de gráficas de los datos obtenidos en la simulación masiva de Abaqus

## Primera parte: generación de la base de datos con Abaqus

Esta parte permite generar automáticamente las geometrías, ejecutar las simulaciones en Abaqus y postprocesar los resultados para construir la base de datos utilizada posteriormente por el modelo predictivo.

### Requisitos

Esta parte requiere disponer de una instalación de Abaqus con soporte para la ejecución de scripts de Python.

### Uso

Generar los archivos de entrada ejecutando en Abaqus:

```text
generacion_inps.py
```

A continuación, ejecutar en la misma carpeta:

```text
crearodbs.bat
```

Una vez finalizadas las simulaciones y generados los archivos ODB, ejecutar en Abaqus:

```text
postprocesamiento.py
```

### Datos

Las combinaciones geométricas utilizadas como entrada se generan mediante Latin Hypercube Sampling con:

```text
LHS.py
```

El archivo generado contiene los parámetros geométricos empleados para crear cada uno de los modelos de Abaqus.

### Archivos principales

* `LHS.py`: genera las combinaciones geométricas mediante muestreo LHS.
* `generacion_inps.py`: crea los modelos y los archivos de entrada de Abaqus.
* `crearodbs.bat`: ejecuta las simulaciones y genera los archivos ODB.
* `postprocesamiento.py`: extrae los resultados de las simulaciones y genera la base de datos.

### Resultados

El postprocesamiento de los archivos ODB permite obtener las métricas de comportamiento estructural necesarias para crear la base de datos de simulaciones.

## Segunda parte: creación y entrenamiento del modelo predictivo

Esta parte utiliza la base de datos obtenida mediante las simulaciones de Abaqus para entrenar modelos predictivos, evaluar nuevas geometrías, buscar configuraciones óptimas y generar frentes de Pareto.

### Instalación

Crear y activar un entorno virtual e instalar las librerías necesarias.

En macOS o Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Uso

Ejecutar el asistente para acceder a las diferentes opciones disponibles:

```bash
python asistente.py
```

### Datos

El archivo principal de entrada es:

```text
datos/simulaciones.csv
```

Las columnas geométricas esperadas son:

```text
Radio, Angulo, Num_Ag, Radio_Ag, Factor_H
```

Las variables objetivo son:

```text
SEA, CFE
```

### Archivos principales

* `asistente.py`: proporciona el menú principal de ejecución.
* `entrenamiento.py`: entrena y evalúa los modelos predictivos.
* `prediccion.py`: obtiene predicciones para nuevas geometrías.
* `optimizacion.py`: busca configuraciones geométricas con mejores prestaciones.
* `pareto.py`: genera y representa los frentes de Pareto.
* `requirements.txt`: contiene las librerías necesarias para ejecutar el proyecto.

### Resultados

Los modelos entrenados se almacenan en:

```text
modelos/
```

Los archivos CSV, las métricas de evaluación y las gráficas generadas se almacenan en:

```text
resultados/
```
