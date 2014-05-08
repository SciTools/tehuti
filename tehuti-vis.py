#!/usr/bin/env python
# (C) British Crown Copyright 2014, Met Office
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

import matplotlib.pyplot as plt

from tehuti import Results, sha


# Based on (minor label tweaks and line plotting on single value input):
# http://pyinsci.blogspot.co.uk/2009/09/violin-plot-with-matplotlib.html
def violin_plot(ax,data,bp=False):
    '''
    create violin plots on an axis
    '''
    from scipy.stats import gaussian_kde
    from numpy import arange
    pos = range(len(data))
    dist = max(pos)-min(pos)
    w = min(0.15*max(dist,1.0),0.5)
    for d,p in zip(data,pos):
        # If we only have a single value, plot a line instead
        try:
            k = gaussian_kde(d) #calculates the kernel density
        except ValueError:
            ax.hlines(d, p-w, p+w)
        else:
            line = False
            m = k.dataset.min() #lower bound of violin
            M = k.dataset.max() #upper bound of violin
            x = arange(m,M,(M-m)/100.) # support for violin
            v = k.evaluate(x) #violin profile (density curve)
            v = v/v.max()*w #scaling the violin to the available space
            ax.fill_betweenx(x,p,v+p,facecolor='y',alpha=0.3)
            ax.fill_betweenx(x,p,-v+p,facecolor='y',alpha=0.3)
    if bp:
        ax.boxplot(data,notch=1,positions=pos,vert=1)


def plot(picked, single_id):
    keys = None
    for commit, results in picked:
        if keys is None:
            keys = results.viewkeys()
        else:
            keys = keys & results.viewkeys()
    for key in keys:
        if key == 'name' or (single_id and key != single_id):
            continue
        labels = []
        data = []
        for commit, results in picked:
            labels.append(_short(commit))
            data.append(results[key])
        ax = plt.axes()
        ax.set_title(key)
        if isinstance(data[0], list):
            violin_plot(ax, data)
        else:
            width = 0.6
            pos = [x - (width / 2) for x in range(len(data))]
            ax.bar(pos, data, width=width)
        ax.set_xticks(range(len(data)))
        ax.set_xticklabels(labels, rotation=30)
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--id', help='select a single metric by ID')
    parser.add_argument('metrics')
    parser.add_argument('commits', nargs='+')
    options = parser.parse_args()
    metrics = __import__(options.metrics).metrics
    results = Results.load(options.metrics)
    picked = [(commit, results.results[sha(commit)])
              for commit in options.commits]
    plot(picked, options.id)
