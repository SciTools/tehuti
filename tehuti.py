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
from abc import ABCMeta, abstractmethod
import argparse
import importlib
import json
import os
import subprocess
import sys
import timeit


class Metric(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def id(self):
        pass

    @abstractmethod
    def run(self):
        pass


class TimeMetric(Metric):
    class Context(object):
        pass

    def __init__(self, body, setup=None, repeat=100, number=1, name=None):
        self.body = body
        self.setup = setup
        self.repeat = repeat
        self.number = number
        self.name = name

    def id(self):
        return 'timeit-{}'.format(self.name or self.body.func_name)

    def run(self):
        context = TimeMetric.Context()
        body = lambda: self.body(context)
        if self.setup:
            setup = lambda: self.setup(context)
        else:
            setup = 'pass'
        t = timeit.Timer(body, setup)
        values = t.repeat(self.repeat, self.number)
        return [value / self.number for value in values]


class LineCountMetric(Metric):
    def __init__(self, path):
        self.path = path

    def id(self):
        return 'linecount-{}'.format(self.path)

    def run(self):
        count, _ = subprocess.check_output(['wc', '-l', self.path]).split()
        return int(count)


class PylintMetric(Metric):
    def __init__(self, module):
        self.module = module

    def id(self):
        return 'pylint-{}'.format(self.module)

    def run(self):
        # Turn off production of the import graph.
        cmd = ['pylint', '--disable=RP0402']
        pylint = subprocess.Popen(cmd + [self.module], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        output, _ = pylint.communicate()
        if pylint.returncode == 0:
            output = output.split('\n')
            rating = [line for line in output
                      if 'code has been rated at' in line]
            rating = float(rating[0].split()[6].split('/')[0])
        else:
            # Possibly this should raise some sort of metric-failure
            # error, or just return a failure token which can be recorded
            # in the results cache.
            rating = 0
        return rating


def sha(name):
    output = subprocess.check_output(['git', 'log', '-1', '--format=%H', name])
    return output.strip()


def working_tree_id():
    try:
        id = sha('HEAD')
        status = subprocess.check_output('git status --porcelain -uno'.split())
        if status.strip():
            id += '-dirty'
    except subprocess.CalledProcessError:
        id = 'unknown'
    return id


def describe_working_tree():
    output = subprocess.check_output(['git', 'describe', '--abbrev=40',
                                      '--dirty'])
    return output.strip()


class Results(object):
    @staticmethod
    def pkl_path(name):
        return os.path.join(PKL_DIR, name + '.json')

    @staticmethod
    def load(name):
        path = Results.pkl_path(name)
        print 'Loading cache from', path
        try:
            with open(path, 'rb') as f:
                r = json.load(f)
        except IOError:
            r = {}
        results = Results(r)
        return results

    def __init__(self, results):
        self.results = results

    def compare(self, start, end=None, single_id=None):
        """
        Compare one commit to another, printing a % difference for each case.

        Parameters
        ----------
        start : str
            The commit from where to start the comparison
        end : str or None, optional
            The commit to compare against ``start``. If None, the commit
            of the current working tree will be used
            (from :func:`working_tree_id`).
        single_id : str or None, optional
            The ID of a single case to compare.

        """
        start_sha = sha(start)
        if end is None:
            end_sha = working_tree_id()
        else:
            end_sha = sha(end)
        start_results = self.results[start_sha]
        end_results = self.results[end_sha]
        for key in start_results.viewkeys() & end_results.viewkeys():
            if key == 'name' or (single_id and key != single_id):
                continue
            print key
            if start_results[key] == end_results[key]:
                print '    no change'
            else:
                v1, v2 = start_results[key], end_results[key]
                if isinstance(v1, list):
                    v1, v2 = min(v1), min(v2)
                ratio = float(v2) / v1
                print '    {} -> {} ({:.0f}%)'.format(v1, v2, ratio * 100)

    def run(self, metrics, force=False, single_id=None):
        code_id = working_tree_id()
        run = False
        if force:
            print 'Forced run of metrics'
            run = True
        if not run and code_id not in self.results:
            print 'First run of metrics'
            run = True
        if code_id.endswith('-dirty'):
            print 'Working tree is dirty - re-running metrics'
            run = True
        if run:
            results = {'name': describe_working_tree()}
            for metric in metrics:
                if single_id and metric.id() != single_id:
                    continue
                sys.stdout.write(metric.id() + ' ...')
                sys.stdout.flush()
                results[metric.id()] = metric.run()
                print ' done'
            self.results[code_id] = results

    def save(self, name):
        path = Results.pkl_path(name)
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, 'wb') as f:
            json.dump(self.results, f, indent=4)

    def summary(self, single_id=None):
        """
        Print a summary of the test results.

        Parameters
        ----------
        single_id - str
            The ID of the metric to summarise.

        """
        code_id = working_tree_id()
        results = self.results[code_id]
        for key, value in results.iteritems():
            if single_id and key != single_id:
                continue
            if isinstance(value, list):
                value = min(value)
            print '{}\n    = {}'.format(key, value)


PKL_DIR = os.path.join(os.environ.get('XDG_DATA_HOME',
                                      os.path.join(os.path.expanduser('~'),
                                                   '.local', 'share')),
                       'tehuti')


def list_metrics(metrics_module_name, out=None):
    """
    Prints the available metrics within the named metrics module.

    Args:

    * metrics_module_name (string):
        The importable name of the module being measured. The module must
        contain a ``metrics`` list.

    * out:
        The file-like object to which the output is written. Defaults
        to sys.stdout.

    """
    if out is None:
        out = sys.stdout
    metrics = importlib.import_module(metrics_module_name).metrics
    out.write('Metrics in {!r}:\n'.format(metrics_module_name))
    for metric in metrics:
        out.write('    {}\n'.format(metric.id()))


def main(metrics_module_name, ref_commit=None, target_commit=None,
         force=False, single_id=None, repo_root=None):
    """
    Implements the command line interface for tehuti.

    Parameters
    ----------
    metrics_module_name : str
        The importable name of the module being measured. The module must
        contain a ``metrics`` list.
    ref_commit : str or None
        The commit name of the reference commit. If None, the results for
        target_commit will be outputted, rather than comparing with the
        ``ref_commit``.
    target_commit : str or None
        The commit name of the . If None, the :meth:`Results.run` method
        will be called, potentially re-computing the timings if they don't
        already exist.
    force : bool
        Whether to force the re-running of the results, if target_commit is
        not None.
    single_id : str or None
        The ID of a single case within the metrics to run the timings and/or
        comparison for.
    repo_root : str or None
        The path of the repository being measured. If None the CWD will be
        used.

    """
    metrics = importlib.import_module(metrics_module_name).metrics

    if single_id is not None and single_id not in (metric.id() for
                                                   metric in metrics):
        raise ValueError('Unknown metric {!r}.'.format(single_id))

    try:
        if repo_root is not None:
            pwd = os.getcwd()
            os.chdir(repo_root)

        results = Results.load(metrics_module_name)
        if target_commit is None:
            results.run(metrics, force, single_id)
            results.save(metrics_module_name)
    
        if ref_commit is not None:
            results.compare(ref_commit, target_commit, single_id)
        else:
            results.summary(single_id)

    finally:
        if repo_root is not None:
            os.chdir(pwd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list', action='store_true', default=False,
                        help='list the metrics in the specified module')
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('-i', '--id', help='select a single metric by ID')
    parser.add_argument('metrics_module')
    parser.add_argument('ref_commit', nargs='?', metavar='reference commit')
    parser.add_argument('target_commit', nargs='?', metavar='target commit')
    options = parser.parse_args()

    if options.list:
        list_metrics(options.metrics_module)
    else:
        main(options.metrics_module, options.ref_commit, options.target_commit,
             options.force, options.id)
