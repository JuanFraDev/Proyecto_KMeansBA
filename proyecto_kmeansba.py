# -*- coding: utf-8 -*-
"""Proyecto_kmeansBA.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1-Icdaa1npbouLL4tMoaIPebkPu3_pgff
"""

#Nubia Araujo
#Madelin Constante
#Juan Donoso
#Mateo Montenegro
#Brenda Simbaña

# ================================================
#         LIBRERÍAS NECESARIAS
# ================================================
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.metrics.cluster import adjusted_rand_score, adjusted_mutual_info_score, normalized_mutual_info_score
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.datasets import load_iris
import random
from scipy.spatial.distance import pdist, squareform
import warnings
import nltk
import string
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
import re

# ================================================
#         FUNCIONES AUXILIARES
# ================================================

# Preparar datos: separar X (features) y y (clase)
def prepare_data(dataset):
    dataset = pd.DataFrame(dataset)

    if "Species" in dataset.columns:
        y = dataset['Species']
        X = dataset.drop(columns=['Species'])
    elif dataset.iloc[:, -1].dtype == 'object' or dataset.iloc[:, -1].dtype == 'int64':
        X = dataset.iloc[:, :-1]
        y = dataset.iloc[:, -1]
    else:
        return None

    return {'X': X, 'y': y}

# Calcular matriz de distancia euclidiana
def calculate_distance_matrix(X):
    D = squareform(pdist(X, metric='euclidean'))
    return D

# Calcular centroides dados los clusters
def calculate_centroids(X, cluster_assignment, k):
    X = np.array(X)
    centroids = np.zeros((k, X.shape[1]))

    for i in range(1, k + 1):
        mask = cluster_assignment == i
        if np.any(mask):
            centroids[i-1] = np.mean(X[mask], axis=0)

    return centroids

# Ajustar cardinalidad para que cada cluster tenga tamaño objetivo
def adjust_cardinality(cluster_assignment, X, centroids, target_cardinality):
    max_iterations = 1000
    iteration = 0
    k = len(target_cardinality)
    cluster_sizes = np.bincount(cluster_assignment, minlength=k+1)[1:]

    X = np.array(X)

    while np.any(cluster_sizes > target_cardinality) and iteration < max_iterations:
        iteration += 1

        for j in np.where(cluster_sizes > target_cardinality)[0]:
            idx = np.where(cluster_assignment == j+1)[0]
            if len(idx) == 0:
                continue

            element = idx[0]
            distances = np.sum((centroids - X[element])**2, axis=1)

            available_clusters = np.where(cluster_sizes < target_cardinality)[0]
            valid_clusters = [c for c in available_clusters if c != j]

            if len(valid_clusters) == 0:
                cluster_assignment[element] = -1
                cluster_sizes[j] -= 1
            else:
                chosen = valid_clusters[np.argmin(distances[valid_clusters])]
                cluster_assignment[element] = chosen + 1
                cluster_sizes[j] -= 1
                cluster_sizes[chosen] += 1

    unassigned_idx = np.where(cluster_assignment == -1)[0]
    if len(unassigned_idx) > 0:
        for element in unassigned_idx:
            available_clusters = np.where(cluster_sizes < target_cardinality)[0]
            if len(available_clusters) > 0:
                chosen = available_clusters[np.argmin(cluster_sizes[available_clusters])]
                cluster_assignment[element] = chosen + 1
                cluster_sizes[chosen] += 1
            else:
                cluster_assignment[element] = 1
                cluster_sizes[0] += 1

    if iteration >= max_iterations:
        warnings.warn("The adjustment process reached the maximum number of iterations.")

    return cluster_assignment

# Generar solución inicial con kmeans
def generate_initial_solution(X, target_cardinality, seed=45):
    np.random.seed(seed)
    km = KMeans(n_clusters=len(target_cardinality), random_state=seed)
    cluster_assignment = km.fit_predict(X) + 1  # +1 para hacer compatible con el código R
    centroids = calculate_centroids(X, cluster_assignment, len(target_cardinality))
    cluster_assignment = adjust_cardinality(cluster_assignment, X, centroids, target_cardinality)
    return cluster_assignment

# Evaluar solución con coeficiente silhouette y penalización por cardinalidad
def evaluate_solution(cluster_assignment, X, target_cardinality, penalty_weight=10):
    unique_clusters = np.unique(cluster_assignment)
    if len(unique_clusters) < 2:
        return -float('inf')  # Retornar un valor muy bajo si solo hay un cluster

    # Calcular silhouette
    ss = silhouette_samples(X, cluster_assignment)

    # Calcular penalización
    current_counts = np.bincount(cluster_assignment, minlength=len(target_cardinality)+1)[1:]
    penalty = penalty_weight * np.sum(np.abs(current_counts - target_cardinality))

    return np.mean(ss) - penalty

# Algoritmo Bat (simplificado)
def run_bat_algorithm(X, target_cardinality, n_bats=30, max_iterations=20,
                      f_min=0, f_max=2, loudness=0.5, pulse_rate=0.5,
                      alpha=0.9, gamma=0.9):
    np.random.seed(1521)
    seeds = np.random.choice(range(1, 10001), n_bats, replace=False)

    X = np.array(X)
    n_samples = X.shape[0]

    bats = []
    for i in range(n_bats):
        bats.append({
            'position': generate_initial_solution(X, target_cardinality, seed=seeds[i]),
            'velocity': np.zeros(n_samples),
            'frequency': np.random.uniform(f_min, f_max),
            'loudness': loudness,
            'pulse_rate': pulse_rate,
            'seed': seeds[i]
        })

    best_solution = bats[0]['position']
    best_score = evaluate_solution(best_solution, X, target_cardinality)
    best_seed = bats[0]['seed']

    for iteration in range(max_iterations):
        for i in range(n_bats):
            bat = bats[i]
            bat['frequency'] = np.random.uniform(f_min, f_max)
            bat['velocity'] = bat['velocity'] + (bat['position'] - best_solution) * bat['frequency']
            new_position = np.round(bat['position'] + bat['velocity']).astype(int)
            new_position = np.clip(new_position, 1, len(target_cardinality))

            if np.random.random() > bat['pulse_rate']:
                new_position = np.random.randint(1, len(target_cardinality) + 1, n_samples)

            for j in range(1, len(target_cardinality) + 1):
                while np.sum(new_position == j) > target_cardinality[j-1]:
                    idx = np.where(new_position == j)[0]
                    random_idx = np.random.choice(idx)
                    new_position[random_idx] = np.random.randint(1, len(target_cardinality) + 1)

            new_score = evaluate_solution(new_position, X, target_cardinality)

            if new_score > best_score and np.random.random() < bat['loudness']:
                bats[i]['position'] = new_position
                bats[i]['loudness'] = alpha * bat['loudness']
                bats[i]['pulse_rate'] = pulse_rate * (1 - np.exp(-gamma * iteration))
                if new_score > best_score:
                    best_solution = new_position
                    best_score = new_score
                    best_seed = bats[i]['seed']

    return {'best_solution': best_solution, 'best_score': best_score, 'best_seed': best_seed, 'seeds': seeds}

# Función para imprimir resultados y calcular métricas
def print_results(results, y, X, D, target_cardinality, dataset_name):
    best_solution = results['best_solution']
    best_score = results['best_score']
    best_seed = results['best_seed']
    seeds = results['seeds']
    num_instances = X.shape[0]
    num_variables = X.shape[1] + 1

    # Convertir a arrays de numpy para usar con las métricas
    y_true = np.array(y)
    y_pred = best_solution

    ARI_value = adjusted_rand_score(y_true, y_pred)
    AMI_value = adjusted_mutual_info_score(y_true, y_pred)
    NMI_value = normalized_mutual_info_score(y_true, y_pred)

    # Calcular silhouette
    silhouette_values = silhouette_samples(X, y_pred)
    mean_silhouette = silhouette_score(X, y_pred)

    # Guardar resultados de silhouette
    silhouette_df = pd.DataFrame({
        'cluster': y_pred,
        'sil_width': silhouette_values
    })
    silhouette_df.to_csv("silhouette_results.csv", index=False)
    print("Silhouette coefficient results saved to 'silhouette_results.csv'.")

    num_clusters = len(np.unique(best_solution))
    class_dist = np.bincount(best_solution)[1:] if 0 not in best_solution else np.bincount(best_solution)

    # Crear un dataframe para global_results (en R se guardaba como variable global)
    global_results = pd.DataFrame({
        'name': [dataset_name],
        'Best_Seed': [best_seed],
        'ARI': [ARI_value],
        'AMI': [AMI_value],
        'NMI': [NMI_value],
        'Mean_Silhouette': [mean_silhouette],
        'Clusters': [num_clusters],
        'number_features': [num_variables],
        'number_instances': [num_instances],
        'cardinality_BAT': [class_dist.tolist()],
        'cardinality_REAL': [target_cardinality]
    })

    print(f"Average silhouette coefficient: {mean_silhouette}")
    print("Seeds used for each bat:")
    print(seeds)
    print(f"\nSeed of the bat with the best solution: {best_seed}")

    print("\nOptimal cardinality for each cluster:")
    print(class_dist)

    return global_results

def plot_silhouette(X, labels, distance_matrix):
    silhouette_vals = silhouette_samples(distance_matrix, labels, metric='precomputed')
    n_clusters = len(np.unique(labels))
    y_lower = 10

    plt.figure(figsize=(10, 6))

    for i in range(n_clusters):
        ith_cluster_silhouette_vals = silhouette_vals[labels == i]
        ith_cluster_silhouette_vals.sort()

        size_cluster_i = ith_cluster_silhouette_vals.shape[0]
        y_upper = y_lower + size_cluster_i

        color = plt.cm.nipy_spectral(float(i) / n_clusters)
        plt.fill_betweenx(
            np.arange(y_lower, y_upper),
            0,
            ith_cluster_silhouette_vals,
            facecolor=color,
            edgecolor=color,
            alpha=0.7
        )

        plt.text(-0.05, y_lower + 0.5 * size_cluster_i, str(i))
        y_lower = y_upper + 10  # espacio entre clusters

    plt.axvline(x=np.mean(silhouette_vals), color="red", linestyle="--", label="Mean silhouette")
    plt.xlabel("Silhouette coefficient")
    plt.ylabel("Cluster")
    plt.title("Silhouette plot for each cluster")
    plt.legend()
    plt.tight_layout()
    plt.show()

#Verificar encoding para cargar el archivo
import chardet

with open('ICMLA_2014_2015_2016_2017.csv', 'rb') as f:
    result = chardet.detect(f.read(100000))
    print(result)

# ================================================
#         TF-IDF MATRIZ + LIST + DATAFRAME
# ================================================

nltk.download('stopwords')

# ================================================
#         INSERTAR Y PREPROCESAR TEXTOS
# ================================================
df = pd.read_csv('ICMLA_2014_2015_2016_2017.csv', encoding='ISO-8859-1')
df = df[['paper_id', 'title', 'keywords', 'abstract', 'session', 'year']]
df['abstract'] = df['abstract'].fillna('')

stop_words = set(stopwords.words('english'))
stemmer = PorterStemmer()

def preprocess_text(text):
    text = re.sub(r'[^A-Za-z0-9]+', ' ', text)
    text = text.lower()
    words = text.split()
    words = [stemmer.stem(w) for w in words if w not in stop_words]
    return words

df['tokens'] = df['abstract'].apply(preprocess_text)

# ================================================
#         CREAR MATRIZ TF-IDF
# ================================================

N = len(df)
vocabulario = sorted(set(word for doc in df['tokens'] for word in doc))
word_index = {word: i for i, word in enumerate(vocabulario)}

# Inicializar matriz de frecuencia término-documento
matriz = np.zeros((len(vocabulario), N))

# Llenar la matriz con conteos
for j, doc in enumerate(df['tokens']):
    for word in doc:
        i = word_index[word]
        matriz[i, j] += 1

# Calcular DF (número de documentos donde aparece cada palabra)
df_counts = np.count_nonzero(matriz, axis=1).reshape(-1, 1)

# Calcular WTF (ponderación logarítmica)
wtf = np.where(matriz > 0, 1 + np.log10(matriz), 0)

# Calcular IDF
idf = np.log10(N / df_counts)

# Calcular matriz TF-IDF
tfidf = np.round(wtf * idf, 4)

# ================================================
#         CONVERTIR A LISTA DE DICCIONARIOS Y DATAFRAME
# ================================================
# Crear lista de diccionarios (uno por documento)
tfidf_list = []
for j in range(tfidf.shape[1]):  # por cada documento
    doc_dict = {}
    for i in range(tfidf.shape[0]):  # por cada palabra
        valor = tfidf[i, j]
        if valor > 0:
            palabra = vocabulario[i]
            doc_dict[palabra] = valor
    tfidf_list.append(doc_dict)

# Crear DataFrame TF-IDF
tfidf = tfidf.T
tf_idf_df = pd.DataFrame(tfidf, columns=vocabulario).fillna(0)
print(tf_idf_df)

# ================================================
#         CREAR MATRIZ DOCUMENTO PALABRA
# ================================================
# Opcional: limitar vocabulario a las 1000 palabras más frecuentes
# Limitar vocabulario a las 1000 palabras más frecuentes
df_counts_dict = {word: int(np.count_nonzero(matriz[word_index[word], :])) for word in vocabulario}
most_common_words = sorted(df_counts_dict.items(), key=lambda x: x[1], reverse=True)[:1000]
vocab = [word for word, _ in most_common_words]
word2idx = {word: idx for idx, word in enumerate(vocab)}

# Matriz vacía
tfidf_matrix = np.zeros((N, len(vocab)))

# Llenar la matriz
for i, tfidf in enumerate(tfidf_list):
    for word, value in tfidf.items():
        if word in word2idx:
            j = word2idx[word]
            tfidf_matrix[i, j] = value

# ================================================
#          GUARDAR MATRIZ TF-IDF EN CSV
# ================================================

# Define the output CSV file name
output_csv_name = 'embeddings_tfidf.csv'

try:
    # Save the tf_idf_df DataFrame to a CSV file
    tf_idf_df.to_csv(output_csv_name, index=False)
    print(f"La matriz TF-IDF se ha guardado exitosamente en '{output_csv_name}'")
except Exception as e:
    print(f"Error al guardar la matriz TF-IDF en CSV: {e}")

# ================================================
#         LLM
# ================================================
"""
Emplear la info del dataset ICMLA_2014_2015_2016_2017 para obtener embeddings del campo abstract empleando LLM's.
"""
import google.generativeai as genai
import pandas as pd
import numpy as np
import time

import re
import nltk

from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
nltk.download('stopwords')

model_name = 'models/text-embedding-004'

try:
  genai.configure(api_key="AIzaSyBjcBorkf8qglk69q5DpCgAC2Nv9Rj3Dw4")
except KeyError:
    print("Error: La variable de entorno GOOGLE_API_KEY no está configurada.")
    exit()

df = pd.read_csv('ICMLA_2014_2015_2016_2017.csv', encoding='Windows-1252')
abstracts = df['abstract'].tolist()

def normalizar(documents):
  processed_documents = []
  for doc in documents:
    if isinstance(doc, str):
        current_text = doc
    elif isinstance(doc, list):
        current_text = ' '.join(map(str, doc))
    text = current_text.lower()
    text = re.sub('[^A-Za-z0-9]+',' ', text)
    processed_documents.append(text)
  return processed_documents

def preprocesamiento(documents):
  stop_words = set(stopwords.words('english'))
  stemmer = PorterStemmer()
  processed_documents = []
  for document in documents:
    tokens = document.split()
    filtered_tokens = [token for token in tokens if not token in stop_words]

    stemmed_tokens = [stemmer.stem(word) for word in filtered_tokens]
    processed_documents.append(stemmed_tokens)

  return processed_documents

def generate_embeddings_batch(texts, model, task_type="CLUSTERING", batch_size=50):
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        try:
            result = genai.embed_content(
                model=model,
                content=batch_texts,
                task_type=task_type
            )
            all_embeddings.extend(result['embedding'])
        except Exception as e:
            print(f"Error generando embeddings para el lote que comienza en el índice {i}: {e}")
            return None
        print(f"Procesado lote de {len(batch_texts)} abstracts. Embeddings generados: {len(all_embeddings)}")
    return all_embeddings

abstracts = normalizar(abstracts)
abstracts = preprocesamiento(abstracts)
print(abstracts)

embeddings_list = []
texts_per_batch = 50

for i in range(0, len(abstracts), texts_per_batch):
    batch = abstracts[i:i + texts_per_batch]
    try:
        result = genai.embed_content(
            model=model_name,
            content=batch,
            task_type="CLUSTERING"
        )
        embeddings_list.extend(result['embedding'])
        print(f"Lote {i//texts_per_batch + 1} procesado. Total embeddings: {len(embeddings_list)}")
        if len(abstracts) > texts_per_batch:
             time.sleep(1)
    except Exception as e:
        print(f"Error procesando el lote {i//texts_per_batch + 1}: {e}")
        break

if embeddings_list and len(embeddings_list) == len(abstracts):
    print("¡Embeddings generados exitosamente para todos los abstracts!")

else:
    print(f"Se generaron {len(embeddings_list)} embeddings de {len(abstracts)} abstracts.")

for embedding in embeddings_list:
    print(embedding)

print(f"Instancias: {len(embeddings_list)}")
print(f"Variables: {len(embeddings_list[0])}")

if embeddings_list and len(embeddings_list) == len(df):
  ids_abstracts = []
  if 'Paper_Id' in df.columns:
      ids_abstracts = df['Paper_Id'].tolist()
      id_column_name = 'Paper_Id'
  elif 'Title' in df.columns:
      ids_abstracts = df['Title'].tolist()
      id_column_name = 'Title'
  else:
      ids_abstracts = df.index.tolist()
      id_column_name = 'Original_Index'

  embeddings_df = pd.DataFrame({
        id_column_name: ids_abstracts,
        'embedding': embeddings_list
    })
  try:
      output_csv_name = 'abstract_embeddings_LLM.csv'
      embeddings_df.to_csv(output_csv_name, index=False)
      print(f"Los IDs y sus embeddings correspondientes se han guardado en '{output_csv_name}'")
  except Exception as e:
      print(f"Error guardando el CSV de embeddings: {e}")
elif embeddings_list:
    print(f"El número de embeddings ({len(embeddings_list)}) no coincide con el número de abstracts ({len(df)}).")
else:
    print("No se generaron embeddings.")

# ================================================
#         INSTALAR DEPENDENCIAS
# ================================================
#!pip install gensim
#!pip install transformers
#!pip install torch
#Reiniciar el entorno de ejecución luego de instalar las dependencias

# =====================================================
#         WORD2VEC INICIALIZADO CON EMBEDDINGS DE BERT
# =====================================================

import pandas as pd
import re
import nltk
import numpy as np
from gensim.models import Word2Vec
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from transformers import BertTokenizer, BertModel
import torch

# ================================================
#         CARGAR DATASET
# ================================================
def cargar_csv(dataset):
    datos = pd.read_csv(dataset, skiprows=1, header=None, encoding="latin1")
    datos.columns = ['paper_id', 'title', 'keywords', 'abstract', 'session', 'year']
    return datos

dataset_path = "ICMLA_2014_2015_2016_2017.csv"
df = cargar_csv(dataset_path)

# ================================================
#         PRE-PROCESAMIENTO
# ================================================
nltk.download('stopwords')

def normalizar(documents):
    processed_documents = []
    for doc in documents:
        if isinstance(doc, str):
            current_text = doc
        elif isinstance(doc, list):
            current_text = ' '.join(map(str, doc))
        text = current_text.lower()
        text = re.sub('[^A-Za-z0-9]+',' ', text)
        processed_documents.append(text)
    return processed_documents

def preprocesamiento(documents):
    stop_words = set(stopwords.words('english'))
    stemmer = PorterStemmer()
    processed_documents = []
    for document in documents:
        tokens = document.split()
        filtered_tokens = [token for token in tokens if token not in stop_words]
        stemmed_tokens = [stemmer.stem(word) for word in filtered_tokens]
        processed_documents.append(stemmed_tokens)
    return processed_documents

abstracts = df['abstract'].astype(str).tolist()
abstracts = normalizar(abstracts)
abstracts = preprocesamiento(abstracts)

# ================================================
#         GENERACIÓN DE EMBEDDINGS CON BERT
# ================================================
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

def get_word_embeddings(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    word_embeddings = []
    with torch.no_grad():
        outputs = model(**inputs)
    last_hidden_states = outputs.last_hidden_state
    for i, token in enumerate(inputs.input_ids[0]):
        word = tokenizer.decode([token])
        if word not in ['[CLS]', '[SEP]', '[PAD]']:
            embedding = last_hidden_states[0][i].numpy()
            word_embeddings.append((word, embedding))
    return word_embeddings

# ================================================
#         CONSTRUIR VOCABULARIO CON BERT
# ================================================
bert_word_embeddings = {}

for abstract in abstracts:
    text = ' '.join(abstract)
    try:
        word_embeds = get_word_embeddings(text)
        for word, embedding in word_embeds:
            clean_word = word.replace('##', '').lower()
            if clean_word not in bert_word_embeddings:
                bert_word_embeddings[clean_word] = embedding
    except Exception as e:
        print(f"Error procesando abstract: {e}")
        continue

# ================================================
#         INICIALIZAR WORD2VEC CON EMBEDDINGS DE BERT
# ================================================
embedding_dim = 768
model_w2v = Word2Vec(
    vector_size=embedding_dim,
    window=5,
    min_count=1,
    workers=4,
    epochs=10
)

model_w2v.build_vocab(abstracts)

for word in model_w2v.wv.key_to_index:
    if word in bert_word_embeddings:
        model_w2v.wv[word] = bert_word_embeddings[word]
    else:
        model_w2v.wv[word] = np.mean(list(bert_word_embeddings.values()), axis=0)

model_w2v.train(
    abstracts,
    total_examples=len(abstracts),
    epochs=model_w2v.epochs
)

# ================================================
#         EMBEDDINGS POR ABSTRACT
# ================================================
embeddings_list = []

for tokens in abstracts:
    valid_vectors = [model_w2v.wv[word] for word in tokens if word in model_w2v.wv]
    if valid_vectors:
        avg_vector = np.mean(valid_vectors, axis=0)
    else:
        avg_vector = np.zeros(embedding_dim)
    embeddings_list.append(avg_vector.tolist())

for embedding in embeddings_list:
    print(embedding)

# ================================================
#         GUARDAR EMBEDDINGS EN CSV
# ================================================
print(f"Instancias: {len(embeddings_list)}")
print(f"Variables: {len(embeddings_list[0]) if embeddings_list else 0}")

if embeddings_list and len(embeddings_list) == len(df):
    ids_abstracts = []
    if 'paper_id' in df.columns:
        ids_abstracts = df['paper_id'].tolist()
        id_column_name = 'paper_id'
    elif 'title' in df.columns:
        ids_abstracts = df['title'].tolist()
        id_column_name = 'title'
    else:
        ids_abstracts = df.index.tolist()
        id_column_name = 'index'

    embeddings_df = pd.DataFrame({
        id_column_name: ids_abstracts,
        'embedding': embeddings_list
    })
    try:
        output_csv_name = 'abstract_embeddings_word2vec.csv'
        embeddings_df.to_csv(output_csv_name, index=False)
        print(f"Los IDs y sus embeddings correspondientes se han guardado en '{output_csv_name}'")
    except Exception as e:
        print(f"Error guardando el CSV de embeddings: {e}")
elif embeddings_list:
    print(f"El número de embeddings ({len(embeddings_list)}) no coincide con el número de abstracts ({len(df)}).")
else:
    print("No se generaron embeddings.")

# ================================================
#         CLUSTERING CON KMEAS
# ================================================
from sklearn.cluster import KMeans

# Obtener el número de valores únicos en la columna 'session'
unique_sessions_count = df['session'].nunique()
print(f"Cantidad de nombres únicos en la columna 'session': {unique_sessions_count}")

k = unique_sessions_count  # Cambia esto según lo que descubras con el método del codo
kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)

# ===========================================================
#         VALOR DE K Y VECTOR CARDINALIDAD_CLUSTERS
# ===========================================================
# Ver ejemplos por cluster
def analizar_clusters(df, k):
    for i in range(k):
        cluster_docs = df[df['cluster'] == i]['abstract']
        print(f"\nCluster {i} ejemplos:")
        if len(cluster_docs) >= 2:
            print(cluster_docs.sample(2).values)
        else:
            print(cluster_docs.values)  # Muestra lo que haya, aunque sea 1
    print("\nDistribución de documentos por cluster:")
    print(df['cluster'].value_counts())

    # Obtener la cantidad de documentos por cluster
    cluster_counts = df['cluster'].value_counts().sort_index()

    # Guardar solo las cantidades en una lista (vector)
    cardinalidades_clusters = cluster_counts.tolist()

    # Mostrar resultado
    print("Cardinalidades por cluster:", cardinalidades_clusters)
    return cardinalidades_clusters

df['cluster'] = kmeans.fit_predict(tfidf_matrix)
cardinalidades_clusters = analizar_clusters(df, k)
# ================================================
#         VALIDACIÓN: TF-IDF
# ================================================
D = calculate_distance_matrix(tf_idf_df)
y = df['session'].values
results = run_bat_algorithm(tf_idf_df, cardinalidades_clusters)
global_results = print_results(results, y, tf_idf_df, D, cardinalidades_clusters, "tf-idf")
# Ver resultados
print(results['best_solution'])
print('best_score:', results['best_score'])
print(global_results['AMI'])  # Adjusted Mutual Information
print(global_results['ARI'])  # Adjusted Rand Index
print(global_results['NMI'])  # Normalized Mutual Information
#Mostrar Gráfico de Silueta
plot_silhouette(tfidf_matrix, df['cluster'].values, D)

import ast
import numpy as np
import pandas as pd

# Carga de embeddings desde CSV
LLM_embeddings_df = pd.read_csv('abstract_embeddings_LLM.csv')

# Convertir strings a listas (si es necesario)
LLM_embeddings = LLM_embeddings_df['embedding'].apply(ast.literal_eval)

# Convertir a matriz NumPy 2D
X = np.vstack(LLM_embeddings.values)
df['cluster'] = kmeans.fit_predict(X)
cardinalidades_clusters = analizar_clusters(df, k)

# ================================================
#         VALIDACIÓN: LLM
# ================================================
y = df['session'].values
D = calculate_distance_matrix(X)

results = run_bat_algorithm(X, cardinalidades_clusters)
global_results = print_results(results, y, X, D, cardinalidades_clusters, "LLM_embeddings_df")
# Ver resultados
print(results['best_solution'])
print('best_score:', results['best_score'])
print(global_results['AMI'])  # Adjusted Mutual Information
print(global_results['ARI'])  # Adjusted Rand Index
print(global_results['NMI'])  # Normalized Mutual Information
#Mostrar Gráfico de Silueta
plot_silhouette(X, df['cluster'].values, D)

import ast
import numpy as np
import pandas as pd

# Carga de embeddings desde CSV
w2v_embeddings_df = pd.read_csv('abstract_embeddings_word2vec.csv')

# Convertir strings a listas (si es necesario)
w2v_embeddings = w2v_embeddings_df['embedding'].apply(ast.literal_eval)

# Convertir a matriz NumPy 2D
X = np.vstack(w2v_embeddings.values)
df['cluster'] = kmeans.fit_predict(X)
cardinalidades_clusters = analizar_clusters(df, k)

# ================================================
#         VALIDACIÓN: WORD2VEC con modelo BERT
# ================================================
y = df['session'].values
D = calculate_distance_matrix(X)
results = run_bat_algorithm(X, cardinalidades_clusters)
global_results = print_results(results, y, X, D, cardinalidades_clusters, "w2v_embeddings_df")
# Ver resultados
print(results['best_solution'])
print('best_score:', results['best_score'])
print(global_results['AMI'])  # Adjusted Mutual Information
print(global_results['ARI'])  # Adjusted Rand Index
print(global_results['NMI'])  # Normalized Mutual Information
#Mostrar Gráfico de Silueta
plot_silhouette(X, df['cluster'].values, D)
