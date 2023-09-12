import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.sparse import csr_matrix
from sklearn.metrics import davies_bouldin_score, calinski_harabasz_score
from sklearn.metrics import silhouette_score

from STMiner.Algorithm.distance import get_exp_array


def _adjust_arr(arr, rotate, reverse_x, reverse_y):
    if rotate:
        arr = np.rot90(arr)
    if reverse_y:
        arr = np.flipud(arr)
    if reverse_x:
        arr = np.fliplr(arr)
    return arr


def _get_figure(fig_count, num_cols):
    num_rows = (fig_count + num_cols - 1) // num_cols
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(12, 3 * num_rows))
    # Disable the axis for each subplot
    for ax in axes.flat:
        ax.axis('off')
    return axes, fig


class Plot:
    def __init__(self, sp):
        self.sp = sp

    def plot_gene(self,
                  gene,
                  cmap='Spectral_r',
                  reverse_y=False,
                  reverse_x=False,
                  rotate=False,
                  spot_size=None,
                  log1p=False):
        arr = get_exp_array(self.sp.adata, gene)
        arr = _adjust_arr(arr, rotate, reverse_x, reverse_y)
        if log1p:
            arr = np.log1p(arr)
        sparse_matrix = csr_matrix(arr)
        if spot_size is not None:
            ax = sns.scatterplot(x=sparse_matrix.nonzero()[1],
                                 y=sparse_matrix.nonzero()[0],
                                 c=sparse_matrix.data,
                                 s=spot_size,
                                 cmap=cmap)
        else:
            ax = sns.scatterplot(x=sparse_matrix.nonzero()[1],
                                 y=sparse_matrix.nonzero()[0],
                                 c=sparse_matrix.data,
                                 cmap=cmap)
        ax.set_axis_off()
        ax.set_title(gene)
        plt.show()

    def plot_genes(self,
                   label=None,
                   gene_list=None,
                   n_gene=12,
                   cmap=None,
                   num_cols=4,
                   vmax=100,
                   vmin=0,
                   rotate=False,
                   reverse_y=False,
                   reverse_x=False,
                   plot_type='heatmap'):
        result = self.sp.genes_labels
        adata = self.sp.adata
        if gene_list is None:
            if label is None or result is None:
                raise 'Error: Parameter [label] and [result] should not be None.'
            else:
                gene_list = list(result[result['labels'] == label]['gene_id'])[:n_gene]
        genes_count = len(gene_list)
        axes, fig = _get_figure(genes_count, num_cols)
        fig.subplots_adjust(hspace=0.5)
        for i, gene in enumerate(gene_list):
            row = i // num_cols
            col = i % num_cols
            if len(axes.shape) == 1:
                ax = axes[i]
            else:
                ax = axes[row, col]
            arr = get_exp_array(adata, gene)
            arr = _adjust_arr(arr, rotate, reverse_x, reverse_y)
            sns.set(style="white")
            if cmap is None:
                cmap = sns.color_palette("Spectral_r", as_cmap=True)
            if plot_type == 'heatmap':
                sns.heatmap(arr,
                            cbar=False,
                            ax=ax,
                            cmap=cmap,
                            vmax=np.percentile(arr, vmax),
                            vmin=np.percentile(arr, vmin))
            elif plot_type == 'scatter':
                sparse_matrix = csr_matrix(arr)
                sns.scatterplot(x=sparse_matrix.nonzero()[1],
                                y=sparse_matrix.nonzero()[0],
                                ax=ax,
                                c=sparse_matrix.data,
                                cmap=cmap)
            ax.set_axis_off()
            ax.set_title(gene)
        plt.tight_layout()
        plt.show()

    def plot_pattern(self,
                     cmap=None,
                     vmax=99,
                     num_cols=4,
                     rotate=False,
                     reverse_y=False,
                     reverse_x=False):
        result = self.sp.genes_labels
        adata = self.sp.adata
        label_list = set(result['labels'])
        plot_count = len(label_list)
        axes, fig = _get_figure(plot_count, num_cols=num_cols)
        fig.subplots_adjust(hspace=0.5)
        for i, label in enumerate(label_list):
            row = i // num_cols
            col = i % num_cols
            if len(axes.shape) == 1:
                ax = axes[i]
            else:
                ax = axes[row, col]
            gene_list = list(result[result['labels'] == label]['gene_id'])
            total_count = np.zeros(get_exp_array(adata, gene_list[0]).shape)
            for gene in gene_list:
                exp_matrix = get_exp_array(adata, gene)
                total_sum = np.sum(exp_matrix)
                scale_factor = 100 / total_sum
                scaled_matrix = exp_matrix * scale_factor
                total_count += scaled_matrix
            total_count = _adjust_arr(total_count, rotate, reverse_x, reverse_y)
            sns.heatmap(total_count,
                        ax=ax,
                        cbar=False,
                        cmap=cmap if cmap is not None else 'viridis',
                        vmax=np.percentile(total_count, vmax))
            ax.axis('off')
            ax.set_title('Pattern ' + str(label))
        plt.tight_layout()
        plt.show()

    def plot_score(self, mds_comp, min_cluster, max_cluster):
        db_dict = {}
        ch_dict = {}
        si_dict = {}
        for cluster_number in range(min_cluster, max_cluster + 1):
            self.sp.cluster_gene(self, cluster_number, mds_components=mds_comp)
            db_dict[cluster_number] = 1 / davies_bouldin_score(self.sp.genes_distance_array,
                                                               self.sp.kmeans_fit_result.labels_)
            ch_dict[cluster_number] = calinski_harabasz_score(self.sp.genes_distance_array,
                                                              self.sp.kmeans_fit_result.labels_)
            si_dict[cluster_number] = silhouette_score(self.sp.genes_distance_array, self.sp.kmeans_fit_result.labels_)
        score_df = pd.DataFrame([db_dict, si_dict, ch_dict],
                                index=['1/Davies-Bouldin', 'Silhouette', 'Calinski-Harabasz']).T
        norm_score_df = (score_df - score_df.min()) / (score_df.max() - score_df.min())
        sns.lineplot(norm_score_df, markers=True)
        plt.xticks(list(range(min_cluster, max_cluster + 1, 1)))
        plt.title("Evaluate Clustering Performance")
        plt.xlabel("Number of Clusters")
        plt.ylabel("Normalized Score")
        plt.show()