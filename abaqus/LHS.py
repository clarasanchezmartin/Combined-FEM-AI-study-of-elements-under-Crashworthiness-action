from scipy.stats import qmc
sampler = qmc.LatinHypercube(d=5)
n_muestras = 300
sample = sampler.random(n=n_muestras)

#          r_cil,   ang,   n_ag, r_ag, factor
l_bounds = [25.0,   0.0,    0.0,  2.0,   0.60]  
u_bounds = [55.0,   3.0,    8.0,  6.0,   0.85]
sample_scaled = qmc.scale(sample, l_bounds, u_bounds)

# Numero de casos en los que la conicidad debe ser 0
angulo_cero = int(round(30))

valores = []
for i, fila in enumerate(sample_scaled):

    r, a, n_ag, r_ag, factor = fila

    if i < angulo_cero:
        a = 0.0
    
    # El numero de agujeros debe ser par para simetria 
  
    n_ag_par = max(0, min(8, int(round(n_ag / 2.) * 2))) 

    if n_ag_par == 0: # Si hay 0 agujeros se resetean el resto de variables sobre agujeros
        valores.append([round(r, 2), round(a, 2), 0, 0.0, 0.0])
    else:
        valores.append([round(r, 2), round(a, 2), n_ag_par, round(r_ag, 2), round(factor, 2)])


# Imprimir para copiar a Abaqus
print("valores = " + str(valores))

