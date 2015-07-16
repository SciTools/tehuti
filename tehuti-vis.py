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
import argparse

from tehuti import Results
from vis_methods import VaryRepoCommit, Violin, ManyBenchmarks, VarySetup


class Vis(object):
    """Provides functionality to visualise tehuti metrics results."""

    def __init__(self, results, method):
        """
        Construct a tehuti metrics visualiser.

        The data selected and plots produced are determined by the
        visualisation method (or state) that the visualiser is constructed
        with.

        Args:

        * results: (dict)
            The benchmarking results to visualise. Should be the dictionary of
            benchmarking results loaded from a Tehuti metrics JSON file.
        * method: (str)
            The visualisation method (state) to use. Available states are:
                * 'basic': plot benchmark results against repository commits
                           for all supplied metrics.
                * 'violin': plot benchmark results as a violin plot.
                * 'many': plot multiple benchmarks on a single plot.

        """
        self.results = results
        self._method = method
        self.plot_data = None

        self.methods = {'basic': VaryRepoCommit(self),
                        'violin': Violin(self),
                        'many': ManyBenchmarks(self),
                        'setup': VarySetup(self),
                        }

    @property
    def method(self):
        return self.methods[self._method]

    @method.setter
    def method(self, value):
        try:
            self._method = self.methods[value]
        except KeyError:
            msg = 'Vis has no method {!r}.'
            raise AttributeError(msg.format(value))

    def select_data(self, commits=None, metrics=None):
        """
        Select data to plot. Processing is handed off to the `select_data`
        method of the current state.

        Kwargs:

         * commits:
            One or more valid repository commits that have been benchmarked.
            If no commits are specified then all commits found in the
            benchmarking results will be added to the data to visualise.
         * metrics:
            One or more metrics that have results in the metrics results file.
            If no metrics are specified then all metrics found in the
            benchmarking results will be added to the data to visualise.

        """
        self.plot_data = self.method.select_data(commits, metrics)

    def plot(self, alternate_plot=False):
        """
        Plot data. Plotting is handed off to the `plot` method of the current
        state.

        Kwarg:

        * alternate_plot:
            Toggle to select the alternate plotting mode of the `plot` method
            of the current state.

        """
        if self.plot_data is None:
            self.select_data()
        self.method.plot(alternate_plot)


if __name__ == '__main__':
    choices = ['basic', 'violin', 'many', 'setup',
               'basic-oneplot', 'violin-boxplot', 'many-oneplot',
               'setup-oneplot']
    parser = argparse.ArgumentParser()
    parser.add_argument('plotstyle', choices=choices,
                        default='basic')
    parser.add_argument('module', help='the metrics module to visualise')
    parser.add_argument('-m', '--metrics', default=None, nargs='+',
                        help='select metrics to visualise by ID')
    parser.add_argument('-c', '--commits', nargs='+', default=None)
    options = parser.parse_args()
    module = __import__(options.module).metrics
    results = Results.load(options.module).results
    try:
        method, alternate = options.plotstyle.split('-')
    except ValueError:
        method, alternate = options.plotstyle, False
    else:
        alternate = True
    visualiser = Vis(results, method)
    visualiser.select_data(options.commits, options.metrics)
    visualiser.plot(alternate)
