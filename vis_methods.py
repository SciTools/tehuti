#!/usr/bin/env python
# (C) British Crown Copyright 2014 - 2015, Met Office
#
# This file is part of Tehuti.
#
# Tehuti is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tehuti is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Tehuti.  If not, see <http://www.gnu.org/licenses/>.
import warnings

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

from tehuti import shorten_sha


Y_AXIS_LABELS = {'timeit': 'Time (s)',
                 'linecount': 'Number of lines',
                 'pylint': 'PyLint score',
                 'memoryuse': 'Memory (MB)',
                 'accuracy': 'Accuracy (%)'}


class Visualiser(object):
    """The base class for visualiser states."""

    def _select_data_common(self, commit, metrics):
        if commit is None:
            commits = self.vis.results.keys()
        elif isinstance(commit, basestring):
            commits = list(commit)
        if metrics is None:
            # Only choose metrics that show up in all runs.
            keys = None
            for metrics in self.vis.results.values():
                if keys is None:
                    keys = set(metrics.keys()) - {'name'}
                else:
                    metrics_keys = metrics.keys()
                    common = set(metrics_keys) & keys
                    keys = common
            metrics = list(keys)
        return commits, metrics

    def select_data(self, commit, metrics):
        raise NotImplemented

    def plot(self, alternate_plot):
        raise NotImplemented


class VaryRepoCommit(Visualiser):
    """
    A visualiser state that plots benchmark results against repository commits
    for all supplied metrics.

    Metric results may either be plotted each on individual axes, or all on the
    same axes.

    """
    def __init__(self, vis):
        """
        A visualiser that provides functionality to visualise tehuti metric
        results over a series of commits to an underlying GitHub repo.

        Arg:

        * vis:
            The :class:`tehuti-vis.Vis` class that this class is providing
            a visualiser state for.

        """
        self.vis = vis

    def select_data(self, commits, metrics):
        """
        The select data method for this state.

        Select and re-format data from the supplied metrics results file.

        Data is selected based on all specified `commits` and `metrics`. Data
        is formatted into the standard format used by plot states, with
        specific formatting that collapses any lists of values into the single
        minimum value in that list.
        If no commits or metrics are specified then all commits or metrics
        in the supplied metrics results file are selected.

        Args:

        * commit:
            One or more valid repository commits that have been benchmarked.
        * metrics:
            One or more metrics that have results in the metrics results file.

        Returns:
            The selected data formatted for plotting.

        """
        commits, metrics = self._select_data_common(commits, metrics)
        data = {}
        for metric in metrics:
            data[metric] = {commit: 0 for commit in commits}
            for commit in commits:
                result = self.vis.results[commit][metric]
                if isinstance(result, list):
                    data[metric][commit] = min(result)
                else:
                    data[metric][commit] = result
        return data

    def _plot_single_axis(self):
        """
        Plot the results of all specified metrics onto a single axis.

        Only sets of metrics that all record the same performance benchmark
        can be plotted on the same axis.

        """
        plot_data = self.vis.plot_data

        plt.hold('on')
        ax = plt.axes()
        for name, results in plot_data.iteritems():
            # Pad the start of the labels list.
            x_labels = ['']
            x_labels.extend([shorten_sha(k) for k in results.keys()])
            x_points = range(0, len(x_labels)+1)
            values = results.values()
            ax.plot(x_points[1:-1], values, label=name)
        metric_unit = Y_AXIS_LABELS[name.split('-')[0]]
        ax.set_xticks(x_points)
        ax.set_xticklabels(x_labels, rotation=30)
        ax.set_ylabel(metric_unit)
        ax.set_title('{} metrics'.format(metric_unit.split(' ')[0]))
        ax.legend()
        plt.show()

    def _plot(self):
        """
        Plot the results of each of the specified metrics on their own axis.

        """
        plot_data = self.vis.plot_data
        for name, results in plot_data.iteritems():
            # Pad the start of the labels list.
            x_labels = ['']
            x_labels.extend([shorten_sha(k) for k in results.keys()])
            x_points = range(0, len(x_labels)+1)
            values = results.values()

            ax = plt.axes()
            ax.set_title(name)
            ax.plot(x_points[1:-1], values)
            ax.set_xticks(x_points)
            ax.set_xticklabels(x_labels, rotation=30)
            ax.set_ylabel(Y_AXIS_LABELS[name.split('-')[0]])
            plt.show()

    def plot(self, alternate_plot):
        """
        The plot method for this state.

        Calls a private plotting method (either `_plot` or `_plot_single_axis`)
        to produce the plots.

        Arg:

        * alternate_plot: (boolean)
            Toggle to select whether to plot each metric on its own axis or all
            metrics on the same axis.

        """
        can_plot_single_axis = False
        if alternate_plot:
            can_plot_single_axis = True
            k = [k.split('-')[0] for k in self.vis.plot_data.keys()]
            if len({}.fromkeys(k).keys()) > 1:
                can_plot_single_axis = False
                msg = ('Cannot plot data on single axis: more than one '
                       'metric type was found in results.')
                warnings.warn(msg)
        if can_plot_single_axis:
            self._plot_single_axis()
        else:
            self._plot()


class Violin(Visualiser):
    """
    A visualiser state that plots benchmarking results as a violin plot.

    """
    def __init__(self, vis):
        """
        A visualiser that provides functionality to visualise tehuti metric
        results on a violin plot.

        A violin plot is similar to a box plot but also shows the
        probability density of values in the range of values covered by the
        violin plot, which gives the plot the shape that inspired its name.

        Arg:

        * vis:
            The :class:`tehuti-vis.Vis` class that this class is providing
            a visualiser state for.

        """
        self.vis = vis

    def select_data(self, commits, metrics):
        """
        The select data method for this state.

        Select and re-format data from the supplied metrics results file.

        Data is selected based on all specified `commits` and `metrics`. Data
        is formatted into the standard format used by plot states, with
        specific formatting that appends any single values into single-element
        lists.
        If no commits or metrics are specified then all commits or metrics
        in the supplied metrics results file are selected.

        Args:

        * commits:
            One or more valid repository commits that have been benchmarked.
        * metrics:
            One or more metrics that have results in the metrics results file.

        Returns:
            The selected data formatted for plotting.

        """
        commits, metrics = self._select_data_common(commits, metrics)
        data = {}
        for metric in metrics:
            data[metric] = {commit: 0 for commit in commits}
            for commit in commits:
                result = self.vis.results[commit][metric]
                if not isinstance(result, list):
                    data[metric][commit] = [result]
                else:
                    data[metric][commit] = result
        return data

    # http://pyinsci.blogspot.co.uk/2009/09/violin-plot-with-matplotlib.html
    # Based on (minor label tweaks and line plotting on single value input):
    def plot(self, alternate_plot):
        """
        The plot method for this state.

        Produces a violin plot, with optional box-and-whisker plot overlay.

        Arg:

        * alternate_plot: (boolean)
            Toggle to select whether to overlay a box-and-whisker plot on each
            violin plot.

        """
        plot_data = self.vis.plot_data
        for name, results in plot_data.iteritems():
            ax = plt.axes()
            x_labels = [shorten_sha(k) for k in results.keys()]
            x_points = range(len(results.keys()))
            dist = max(x_points) - min(x_points)
            w = min(0.15 * max(dist, 1.0), 0.5)
            for d, p in zip(results.values(), x_points):
                # If we only have a single value, plot a line instead
                try:
                    k = gaussian_kde(d)  # Calculate the kernel density.
                except ValueError:
                    ax.hlines(d, p-w, p+w)
                else:
                    k_min = k.dataset.min()  # Lower bound of violin.
                    k_max = k.dataset.max()  # Upper bound of violin.
                    x = np.arange(k_min, k_max, (k_max-k_min)/100.)
                    v = k.evaluate(x)  # Violin profile (density curve).
                    v = v / v.max() * w  # Scale violin to available space.
                    ax.fill_betweenx(x, p, v+p, facecolor='y', alpha=0.3)
                    ax.fill_betweenx(x, p, -v+p, facecolor='y', alpha=0.3)
            if alternate_plot:
                ax.boxplot(results.values(), positions=x_points,
                           notch=True, vert=True)
            ax.set_xticks(x_points)
            ax.set_xticklabels(x_labels, rotation=30)
            ax.set_title(name)
            plt.show()
