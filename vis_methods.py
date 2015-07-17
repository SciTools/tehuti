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
from collections import OrderedDict
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
        else:
            commits = commit
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


class ManyBenchmarks(Visualiser):
    """
    A visualiser state that plots results for two different benchmarks
    (for example time and accuracy) of the same set of metrics against
    repository commits for all supplied metrics.

    """
    def __init__(self, vis):
        """
        A visualiser that provides functionality to visualise two benchmarks of
        tehuti metric results over a series of commits to an underlying
        GitHub repo.

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
        specific formatting that converts any single values into one-element
        lists.
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
        # Get unique benchmarks and metrics.
        benchmarks = {}.fromkeys([m.split('-')[0] for m in metrics]).keys()
        metrics = {}.fromkeys([m.split('-', 1)[1] for m in metrics]).keys()
        if len(benchmarks) > 2:
            msg = ('Expected two benchmarks to plot together but got {}. '
                   'They were: {}.')
            raise ValueError(msg.format(len(benchmarks),
                                        ', '.join(benchmarks)))
        data = {}
        for metric in metrics:
            data[metric] = {b: None for b in benchmarks}
            for b in benchmarks:
                data[metric][b] = {commit: None for commit in commits}
                for commit in commits:
                    # Reconstruct original metric name: 'b-metric'.
                    full_metric = b + '-' + metric
                    result = self.vis.results[commit][full_metric]
                    if isinstance(result, list):
                        data[metric][b][commit] = min(result)
                    else:
                        data[metric][b][commit] = result
        return data

    def _plot_single_axis(self):
        """
        Plot the results of all specified metrics onto a single axis.

        Only sets of metrics that all record the same performance benchmark
        can be plotted on the same axis.

        """
        plot_data = self.vis.plot_data

        plt.hold('on')
        ax1 = plt.axes()
        ax2 = ax1.twinx()
        plots = None
        for name, results in plot_data.iteritems():
            b1 = results[results.keys()[0]]
            b2 = results[results.keys()[1]]
            x_labels = ['']
            x_labels.extend([shorten_sha(k) for k in b1.keys()])
            x_points = range(0, len(x_labels)+1)
            b1_values = b1.values()
            b2_values = b2.values()
            l1 = results.keys()[0] + '-' + name
            l2 = results.keys()[1] + '-' + name
            p1 = ax1.plot(x_points[1:-1], b1_values, label=l1)
            p2 = ax2.plot(x_points[1:-1], b2_values, '--', label=l2)
            if plots is None:
                plots = p1 + p2
            else:
                plots += p1
                plots += p2
        ax1.set_xticks(x_points)
        ax1.set_xticklabels(x_labels, rotation=30)
        ax1.set_ylabel(Y_AXIS_LABELS[results.keys()[0]])
        ax2.set_ylabel(Y_AXIS_LABELS[results.keys()[1]])
        ax1.set_title('Multi metrics')
        labels = [plot.get_label() for plot in plots]
        plt.legend(plots, labels)
        plt.show()

    def _plot(self):
        """
        Plot the results of each of the specified metrics on their own axis.

        """
        plot_data = self.vis.plot_data
        for name, results in plot_data.iteritems():
            b1 = results[results.keys()[0]]
            b2 = results[results.keys()[1]]
            x_labels = ['']
            x_labels.extend([shorten_sha(k) for k in b1.keys()])
            x_points = range(0, len(x_labels)+1)
            b1_values = b1.values()
            b2_values = b2.values()

            ax1 = plt.axes()
            ax1.set_title(name)
            l1 = Y_AXIS_LABELS[results.keys()[0]].split(' ')[0]
            p = ax1.plot(x_points[1:-1], b1_values, label=l1)
            ax1.set_xticks(x_points)
            ax1.set_xticklabels(x_labels, rotation=30)
            ax1.set_ylabel(Y_AXIS_LABELS[results.keys()[0]])

            ax2 = ax1.twinx()
            l2 = Y_AXIS_LABELS[results.keys()[1]].split(' ')[0]
            p2 = ax2.plot(x_points[1:-1], b2_values, '--', label=l2)
            ax2.set_ylabel(Y_AXIS_LABELS[results.keys()[1]])

            plots = p + p2
            labels = [plot.get_label() for plot in plots]
            plt.legend(plots, labels)
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
        if alternate_plot:
            self._plot_single_axis()
        else:
            self._plot()


class VarySetup(Visualiser):
    """
    A visualiser state that plots the result of varying the setup of a common
    tehuti metric. This allows for a performance comparison of different
    methods used to perform a given function.

    Metric results may either be plotted each on individual axes, or all on the
    same axes.

    """
    def __init__(self, vis):
        """
        A visualiser that provides functionality to visualise tehuti metric
        results over a series of setups used to produce the results.

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
        # Get unique benchmarks.
        benchmarks = {}.fromkeys([m.split('-')[0] for m in metrics]).keys()
        # We want all metrics, but without the leading benchmark reference.
        metrics = [m.split('-', 1)[1] for m in metrics]
        data = {}

        for b in benchmarks:
            data[b] = {commit: None for commit in commits}
            for commit in commits:
                # We need to retain the order we receive the metrics in.
                data[b][commit] = OrderedDict.fromkeys(metrics)
                for metric in metrics:
                    # Reconstruct original metric name: 'b-metric'.
                    full_metric = b + '-' + metric
                    result = self.vis.results[commit][full_metric]
                    if isinstance(result, list):
                        data[b][commit][metric] = min(result)
                    else:
                        data[b][commit][metric] = result
        return data

    def _plot_single_axis(self):
        """
        For each benchmarking setup in the plot data, plot the results of all
        specified metrics from two or more commits to the underlying repo onto
        a single axis.

        """
        plot_data = self.vis.plot_data

        plt.hold('on')
        ax = plt.axes()
        for name, inter in plot_data.iteritems():
            for commit, results in inter.iteritems():
                # Pad the start of the labels list.
                x_labels = ['']
                x_labels.extend([metric for metric in results])
                x_points = range(0, len(x_labels)+1)
                values = results.values()
                ax.plot(x_points[1:-1], values, label=shorten_sha(commit))
        metric_unit = Y_AXIS_LABELS[name]
        ax.set_xticks(x_points)
        ax.set_xticklabels(x_labels, rotation=30)
        ax.set_ylabel(metric_unit)
        ax.set_title('{} metrics'.format(metric_unit.split(' ')[0]))
        ax.legend()
        plt.show()

    def _plot(self):
        """
        Plot the results of all specified metrics for each commit and
        benchmarking setup on their own axis.

        """
        plot_data = self.vis.plot_data
        for name, inter in plot_data.iteritems():
            metric_unit = Y_AXIS_LABELS[name]
            for commit, results in inter.iteritems():
                # Pad the start of the labels list.
                x_labels = ['']
                x_labels.extend([metric for metric in results])
                x_points = range(0, len(x_labels)+1)
                values = results.values()

                ax = plt.axes()
                title = '{} metrics ({})'
                ax.set_title(title.format(metric_unit.split(' ')[0],
                                          shorten_sha(commit)))
                ax.plot(x_points[1:-1], values)
                ax.set_xticks(x_points)
                ax.set_xticklabels(x_labels, rotation=30)
                ax.set_ylabel(Y_AXIS_LABELS[name])
                plt.show()

    def plot(self, alternate_plot):
        """
        The plot method for this state.

        Calls a private plotting method (either `_plot` or `_plot_single_axis`)
        to produce the plots.

        Note that the benchmarking setup references are unordered. However the
        order is common in all repository commits, so data from multiple
        commits will be plotted on the correct point on the x-axis. Specify the
        full set of benchmarking methods in an appropriate order to the
        `metrics` command-line argument to tehuti-vis to define the order to
        plot the benchmarking setup references in.

        Arg:

        * alternate_plot: (boolean)
            Toggle to select whether to plot each metric on its own axis or all
            metrics on the same axis.

        """
        if alternate_plot:
            self._plot_single_axis()
        else:
            self._plot()
