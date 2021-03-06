# -*- coding: utf-8 -*-
"""Web-Scale k-Means clustering.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1M2tSKizEobcRhiWuUZKIHQOKDDUJe2Xh

The dataset we use to run our experiments is the The Enron Email Dataset which comprises 500,000+ emails from 150 employees of the Enron Corporation [Link to download the Enroll Email dataset](https://www.kaggle.com/wcukierski/enron-email-dataset). After cleaning the webscale dataset and preprocessing it, we will perform the k-means clustering on 18000 email subjects using the batch algorithm and the minibatch algorithm to see how the minibatch outperforms the batch algorithm in terms of balance between the computional cost at training time and the quality of the clustering as described in the [paper](https://www.eecs.tufts.edu/~dsculley/papers/fastkmeans.pdf)
"""

# Commented out IPython magic to ensure Python compatibility.
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
from sklearn.cluster import KMeans 
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from sklearn.metrics import pairwise_distances
from nltk.tokenize import word_tokenize
from nltk.stem.porter import PorterStemmer
from nltk.corpus import stopwords
from bs4 import BeautifulSoup
from scipy.stats import multivariate_normal as mvn
import nltk
import os
import random




import string
# Input data files are available in the "../input/" directory.
# For example, running this (by clicking run or pressing Shift+Enter) will list the files in the input directory

# email module has some useful functions
import matplotlib.pyplot as plt
# %matplotlib inline
plt.style.use('fivethirtyeight')

import os, sys, email,re

from google.colab import drive
drive.mount('/content/drive')

path='/content/drive/My Drive/archive/emails.csv'

df = pd.read_csv(path,nrows = 18000)

"""# Data cleaning part"""

# create list of email objects
emails = list(map(email.parser.Parser().parsestr,df['message']))

# extract headings such as subject, from, to etc..
headings  = emails[0].keys()

# Goes through each email and grabs info for each key
# doc['From'] grabs who sent email in all emails
for key in headings:
    df[key] = [doc[key] for doc in emails]

##Useful functions
def get_raw_text(emails):
    email_text = []
    for email in emails.walk():
        if email.get_content_type() == 'text/plain':
            email_text.append(email.get_payload())
    return ''.join(email_text)

df['body'] = list(map(get_raw_text, emails))
df.head()
df['user'] = df['file'].map(lambda x: x.split('/')[0])

df['Date'] = pd.to_datetime(df['Date'], infer_datetime_format=True)
#df.head()
#df.dtypes

"""Clean the subjects columns"""

import nltk
nltk.download('stopwords')

def clean_column(data):
    if data is not None:
        stopwords_list = stopwords.words('english')
        #exclusions = ['RE:', 'Re:', 're:']
        #exclusions = '|'.join(exclusions)
        data =  data.lower()
        data = re.sub('re:', '', data)
        data = re.sub('-', '', data)
        data = re.sub('_', '', data)
        # Remove data between square brackets
        data =re.sub('\[[^]]*\]', '', data)
        # removes punctuation
        data = re.sub(r'[^\w\s]','',data)
        data = re.sub(r'\n',' ',data)
        data = re.sub(r'[0-9]+','',data)
        # strip html 
        p = re.compile(r'<.*?>')
        data = re.sub(r"\'ve", " have ", data)
        data = re.sub(r"can't", "cannot ", data)
        data = re.sub(r"n't", " not ", data)
        data = re.sub(r"I'm", "I am", data)
        data = re.sub(r" m ", " am ", data)
        data = re.sub(r"\'re", " are ", data)
        data = re.sub(r"\'d", " would ", data)
        data = re.sub(r"\'ll", " will ", data)
        data = re.sub('forwarded by phillip k allenhouect on    pm', '',data)
        data = re.sub(r"httpitcappscorpenroncomsrrsauthemaillinkaspidpage", "", data)
        
        data = p.sub('', data)
        if 'forwarded by:' in data:
            data = data.split('subject')[1]
        data = data.strip()
        return data
    return 'No Subject'


df['Subject_new'] = df['Subject'].apply(clean_column)
df['body_new'] = df['body'].apply(clean_column)

df['body_new'].head(5)

from wordcloud import WordCloud, STOPWORDS
stopwords = set(STOPWORDS)
to_add = ['FW', 'ga', 'httpitcappscorpenroncomsrrsauthemaillinkaspidpage', 'cc', 'aa', 'aaa', 'aaaa',
         'hou', 'cc', 'etc', 'subject', 'pm']

for i in to_add:
    stopwords.add(i)

"""Visuallize email subjects"""

stemmer = PorterStemmer()
def stemming_tokenizer(str_input):
    words = re.sub(r"[^A-Za-z0-9\-]", " ", str_input).lower().split()
    words = [porter_stemmer.stem(word) for word in words]
    return words

def tokenize_and_stem(text):
    # first tokenize by sentence, then by word to ensure that punctuation is caught as it's own token
    tokens = [word for sent in nltk.sent_tokenize(text) for word in nltk.word_tokenize(sent)]
    filtered_tokens = []
    # filter out any tokens not containing letters (e.g., numeric tokens, raw punctuation)
    for token in tokens:
        if re.search('[a-zA-Z]', token):
            filtered_tokens.append(token)
    stems = [stemmer.stem(t) for t in filtered_tokens]
    return stems

"""TF-IDF tranformation for K-means algorithm

After we do a little bit of text cleaning, i.e. convert to lower case, remove stop words and HTML we can move on to using TF-IDF which is pretty straightforward to do in sklearn.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
data = df['body_new']

tf_idf_vectorizor = TfidfVectorizer(stop_words = 'english',#tokenizer = tokenize_and_stem,
                             max_features = 25000)
tf_idf = tf_idf_vectorizor.fit_transform(data)
tf_idf_norm = normalize(tf_idf)
tf_idf_array = tf_idf_norm.toarray()

"""After running this code we can have a sneak peek at our feature names using the get_feature_names() method below."""

pd.DataFrame(tf_idf_array, columns=tf_idf_vectorizor.get_feature_names()).head()

from sklearn.cluster import MiniBatchKMeans, KMeans
from sklearn.metrics.pairwise import pairwise_distances_argmin
from sklearn.decomposition import PCA
import time
sklearn_pca = PCA(n_components = 2)
Y_sklearn = sklearn_pca.fit_transform(tf_idf_array)

"""# Implementation of the K-Means clustering using Minibatch"""

class Minibatchkmeans:

    def __init__(self, k, seed = None, batchsize=None, max_iter=None):
        self.k = k
        self.seed = seed
        self.batchsize=batchsize
        if self.seed is not None:
            np.random.seed(self.seed)
        self.max_iter = max_iter
        
            
    
    def initialise_centroids(self, data):
        
        initial_centroids = np.random.permutation(data.shape[0])[:self.k]
        self.centroids = data[initial_centroids]

        return self.centroids

    def assign_clusters(self, data):
      if data.ndim == 1:
        data = data.reshape(-1, 1)
              
      dist_to_centroid =  pairwise_distances(data, self.centroids, metric = 'euclidean')
      self.cluster_labels = np.argmin(dist_to_centroid, axis = 1)
              
      return  self.cluster_labels
      
    
    def update_centroids(self, data,replacement=True):
      C = self.centroids.copy()
      if replacement:
        data_batch = data[np.random.choice(data.shape[0], self.batchsize, replace=True)]
      else:
        data_batch = data[self.batchsize*i:self.batchsize*(i+1)]

      V = np.zeros(C.shape[0])
      idxs = np.empty(data_batch.shape[0], dtype=np.int)
        # Assign the closest centers without update for the whole batch:
      for j, x in enumerate(data_batch):
        idxs[j] = np.argmin(((C - x)**2).sum(1))

        # Update centers:
      for j, x in enumerate(data_batch):
        V[idxs[j]] += 1
        eta = 1.0 / V[idxs[j]]
        C[idxs[j]] = (1.0 - eta) * C[idxs[j]] + eta * x
        
      self.updatecentroids=C

      return self.updatecentroids

    def predict(self, data):
        
        return self.assign_clusters(data)
    
    def fitmbkmeans(self, data):
        self.centroids = self.initialise_centroids(data)
        
        # Main kmeans loop
        for iter in range(self.max_iter):

            self.cluster_labels = self.assign_clusters(data)
            self.centroids = self.update_centroids(data)          
            if iter % 100 == 0:
                print("Running Model Iteration %d " %iter)
        print("Model finished running")
        return self   

    def kupdate_centroids(self, data):
      C = self.centroids.copy()
      V = np.zeros(C.shape[0])
      for x in data:
        idx = np.argmin(((C - x)**2).sum(1))
        V[idx] += 1
        eta = 1.0 / V[idx]
        C[idx] = (1.0 - eta) * C[idx] + eta * x

      self.kupdatecentroids=C

      return self.kupdatecentroids

    def fitkmeans(self, data):
        self.centroids = self.initialise_centroids(data)
        
        # Main kmeans loop
        for iter in range(self.max_iter):

            self.cluster_labels = self.assign_clusters(data)
            self.centroids = self.kupdate_centroids(data)          
            if iter % 100 == 0:
                print("Running Model Iteration %d " %iter)
        print("Model finished running")
        return self

"""#Performing k-Means using the MiniBatch algorithm, evaluate the time for our model to be trained and visualize the clusters"""

# Commented out IPython magic to ensure Python compatibility.
test = Minibatchkmeans(3, 42, 100, 600)
# %time fitted = test.fitmbkmeans(Y_sklearn)
predicted_values = test.predict(Y_sklearn)

plt.scatter(Y_sklearn[:, 0], Y_sklearn[:, 1], c=predicted_values, s=50, cmap='viridis')

centers = fitted.centroids
plt.scatter(centers[:, 0], centers[:, 1],c='black', s=300, alpha=0.6);

"""# Performing k-Means using the Batch algorithm and evaluate the time for our model to be trained"""

# Commented out IPython magic to ensure Python compatibility.
testkmeans = Minibatchkmeans(3, 42, 100, 600)
# %time fittedkmeans = testkmeans.fitkmeans(Y_sklearn)
predicted_valueskmeans = testkmeans.predict(Y_sklearn)
plt.scatter(Y_sklearn[:, 0], Y_sklearn[:, 1], c=predicted_valueskmeans, s=50, cmap='viridis')

centerskmeans = fittedkmeans.centroids
plt.scatter(centerskmeans[:, 0], centerskmeans[:, 1],c='black', s=300, alpha=0.6);

"""# From the two previous images displaying clustering using Batch on one hand and Minibatch on the other hand, we don't observe so much differences in the clusters. While in terms of computational cost, the K-Means algorithm implemented using Minibatch took 12 seconds to be trained while the k-Means algorithm implemented used the Batch took 3 mins to be trained.

# How can we improve the model?

1. Use a different method to initialize the centroids:k-means++
2. Use the elbow method to get the optimal number of clusters
3. Use the L1 regularizer to promote sparsity so that our model learns the informative features
4. As we are using web-scale data, large dataset, using k-means with sklearn will lead to better results.

Below is an implementation of the  k-Means clustering with batch and  Minibatch
"""

k_means = KMeans(init='k-means++',n_clusters=3, max_iter=600, random_state=42)
t0 = time.time()
k_means.fit(Y_sklearn)
t_batch = time.time() - t0
fitted = k_means.fit(Y_sklearn)
prediction = k_means.predict(Y_sklearn)

mbk = MiniBatchKMeans(init='k-means++', batch_size=100, n_clusters=3, max_iter=600, random_state=42)
mbkfitted = mbk.fit(Y_sklearn)
t0 = time.time()
mbk.fit(Y_sklearn)
t_mini_batch = time.time() - t0
mbkprediction = mbk.predict(Y_sklearn)

# #############################################################################
import matplotlib.pyplot as plt

# Plot result

fig = plt.figure(figsize=(8, 3))
fig.subplots_adjust(left=0.02, right=0.98, bottom=0.05, top=0.9)
colors = ['#4EACC5', '#FF9C34', '#4E9A06']

# We want to have the same colors for the same cluster from the
# MiniBatchKMeans and the KMeans algorithm. Let's pair the cluster centers per
# closest one.
k_means_cluster_centers = k_means.cluster_centers_
order = pairwise_distances_argmin(k_means.cluster_centers_,
                                  mbk.cluster_centers_)
mbk_means_cluster_centers = mbk.cluster_centers_[order]

k_means_labels = pairwise_distances_argmin(Y_sklearn, k_means_cluster_centers)
mbk_means_labels = pairwise_distances_argmin(Y_sklearn, mbk_means_cluster_centers)

# KMeans
ax = fig.add_subplot(1, 3, 1)
for k, col in zip(range(3), colors):
    my_members = k_means_labels == k
    cluster_center = k_means_cluster_centers[k]
    ax.plot(Y_sklearn[my_members, 0], Y_sklearn[my_members, 1], 'w',
            markerfacecolor=col, marker='.')
    ax.plot(cluster_center[0], cluster_center[1], 'o', markerfacecolor=col,
            markeredgecolor='k', markersize=6)
ax.set_title('KMeans')
ax.set_xticks(())
ax.set_yticks(())
plt.text(-3.5, 1.8,  'train time: %.2fs\ninertia: %f' % (
    t_batch, k_means.inertia_))

# MiniBatchKMeans
ax = fig.add_subplot(1, 3, 2)
for k, col in zip(range(3), colors):
    my_members = mbk_means_labels == k
    cluster_center = mbk_means_cluster_centers[k]
    ax.plot(Y_sklearn[my_members, 0], Y_sklearn[my_members, 1], 'w',
            markerfacecolor=col, marker='.')
    ax.plot(cluster_center[0], cluster_center[1], 'o', markerfacecolor=col,
            markeredgecolor='k', markersize=6)
ax.set_title('MiniBatchKMeans')
ax.set_xticks(())
ax.set_yticks(())
plt.text(-3.5, 1.8, 'train time: %.2fs\ninertia: %f' %
         (t_mini_batch, mbk.inertia_))

# Initialise the different array to all False
different = (mbk_means_labels == 4)
ax = fig.add_subplot(1, 3, 3)

for k in range(3):
    different += ((k_means_labels == k) != (mbk_means_labels == k))

identic = np.logical_not(different)
ax.plot(Y_sklearn[identic, 0], Y_sklearn[identic, 1], 'w',
        markerfacecolor='#bbbbbb', marker='.')
ax.plot(Y_sklearn[different, 0], Y_sklearn[different, 1], 'w',
        markerfacecolor='m', marker='.')
ax.set_title('Difference')
ax.set_xticks(())
ax.set_yticks(())

plt.show()

"""Let's extract the top features"""

def get_top_features_cluster(tf_idf_array, prediction, n_feats):
    labels = np.unique(prediction)
    dfs = []
    for label in labels:
        id_temp = np.where(prediction==label) # indices for each cluster
        x_means = np.mean(tf_idf_array[id_temp], axis = 0) # returns average score across cluster
        sorted_means = np.argsort(x_means)[::-1][:n_feats] # indices with top n_feat scores
        features = tf_idf_vectorizor.get_feature_names()
        best_features = [(features[i], x_means[i]) for i in sorted_means]
        df = pd.DataFrame(best_features, columns = ['features', 'score'])
        dfs.append(df)
    return dfs
#dfs = get_top_features_cluster(tf_idf_array, mbkprediction, 20)

"""Let's visualize the top 20 features within each cluster"""

def plot_features(dfs):
    fig = plt.figure(figsize=(14,12))
    x = np.arange(len(dfs[0]))
    for i, df in enumerate(dfs):
        ax = fig.add_subplot(1, len(dfs), i+1)
        ax.set_title("Cluster: "+ str(i), fontsize = 14)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_frame_on(False)
        
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()
        ax.ticklabel_format(axis='x', style='sci', scilimits=(-2,2))
        ax.barh(x, df.score, align='center', color='#40826d')
        yticks = ax.set_yticklabels(df.features)
    plt.show();
#plot_features(dfs)