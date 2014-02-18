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

    def compare(self, start, end, single_id):
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

    def run(self, metrics, force, single_id):
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
        with open(path, 'wb') as f:
            json.dump(self.results, f, indent=4)

    def summary(self, single_id):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('-i', '--id', help='select a single metric by ID')
    parser.add_argument('metrics')
    parser.add_argument('ref_commit', nargs='?', metavar='reference commit')
    parser.add_argument('target_commit', nargs='?', metavar='target commit')
    options = parser.parse_args()
    metrics = __import__(options.metrics).metrics
    results = Results.load(options.metrics)
    if options.target_commit is None:
        results.run(metrics, options.force, options.id)
        results.save(options.metrics)
    if options.ref_commit:
        results.compare(options.ref_commit, options.target_commit, options.id)
    else:
        results.summary(options.id)
