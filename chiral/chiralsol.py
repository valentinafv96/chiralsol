#!/usr/bin/env python3

# Importando librerías

import numpy as np
import dask.array as da
from anomalies import anomaly
from functools import partial
import time
import pandas as pd
from multiprocessing import Pool, cpu_count
import warnings
warnings.filterwarnings("ignore")


# FUNCIÓN GENERAL PARA CORRER EN PARALELO

def soluciones(arreglo, zmax):

    # Se divide el arreglo en las componentes k y l

    split = np.array_split(arreglo, 2)
    K = split[0]
    L = split[1]

    # Se obtiene la solución simplificada con el paquete anomaly

    anomaly.free(L, K)
    b = anomaly.free.simplified

    # Se organizan los términos de la solución de menor a mayor

    b = np.sort(b)

    # Se definen los criterios para que las componentes de la solucion
    # sean != 0, estén en el rango [-zmax,zmax] y sean no triviales

    aux = [(abs(b) <= zmax) & (b != 0)]

    pos = np.array([i for i in b if i >= 0])
    neg = np.array([i for i in b if i < 0])

    comp = np.isin(pos, np.absolute(neg))

    # Se descartan soluciones que no cumplan dichos criterios

    if np.array(aux).all() and anomaly.free.gcd != 0 and not comp.any():

        # Se retorna un diccionario para listar las soluciones en un DataFrame

        return {'k-l': arreglo, 'k': K, 'l': L, 'Solucion': b, 'mcd': anomaly.free.gcd}


# PARÁMETROS IMPORTANTES PARA CORRER EL PROGRAMA EN PARALELO POR BLOQUES

def param(n, N, max, zmax, imax):

    # Número total de listas k-l de mi sistema

    N_uni = pow(2 * max + 1., n - 2)

    # Número máximo (SUGERIDO) de iteraciones

    if imax is None:
        if N // N_uni > 10:
            imax = 0
        else:
            imax = int((10 * N_uni) // N)

    return imax

# PROGRAMA EN PARALELO


def paralelo(n, N=1000000, max=9, zmax=30, imax=None, output_name='soluciones'):

    # Número de fermiones de Weyl

    n = int(n)

    imax = param(n, N, max, zmax, imax)

    # Se define un contador i y un DataFrame vacío

    i = 0
    result_df = pd.DataFrame()

    # Inicializando el tiempo

    start_p = time.time()

    # El programa en paralelo se corre un número imax de iteraciones

    while i <= imax:

        # Se generan los arreglos l-k de forma aleatoria

        kl = da.random.randint(- max, max + 1, (N, n - 2))
        kl = kl.to_dask_dataframe().drop_duplicates().to_dask_array()

        # Se obtiene el arreglo

        kl = kl.compute()

        # Se pone a trabajar el # de CPU's disponibles en paralelo para
        # encontrar las soluciones correspondientes a los arreglos k, l

        pool = Pool(cpu_count())
        sol = pool.map(partial(soluciones, zmax=zmax), kl)
        pool.close()

        # Se elimina el arreglo generado de k-l para liberar la RAM

        del kl

        # Se añaden los resultados a una lista y se eliminan lo None

        result = [s for s in sol if s]

        # Se agregan los resultados al data frame

        result_df = result_df.append(result, ignore_index=True)

        i += 1

    # Se eliminan las soluciones repetidas

    lg = len(result_df.index)

    for k in range(1, int(zmax)):
        for j in range(lg):
            try:
                if k == result_df['Solucion'][j][-1]:
                    result_df['Solucion'][j] = np.sort(-result_df['Solucion'][j])
            except KeyError:
                continue

        result_df['Solucion_s'] = result_df['Solucion'].astype(str)
        result_df = result_df.drop_duplicates('Solucion_s')

    # Se organizan los resultados del DataFrame final

    result_df = result_df.sort_values(by=['Solucion_s']).drop('Solucion_s', axis='columns').reset_index(drop=True)

    # Se entrega un archivo .json con las soluciones para un n determinado

    result_df.to_json(output_name + f'_{n}.json', orient='records')

    if imax != 0:
        print(f'\nGrid → {[N*imax,n-2]}')
    else:
        print(f'\nGrid → {[N,n-2]}')

    print(f'Tiempo ejecución → {(time.time()-start_p)/60.} min')
    print(f'Soluciones únicas → {len(result_df.index)}\n')

    return len(result_df.index)
