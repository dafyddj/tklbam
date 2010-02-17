import os
from os.path import *

class Error(Exception):
    pass

class DirIndex(dict):
    @staticmethod
    def _parse(line):
        vals = line.strip().split('\t')
        if len(vals) != 3:
            raise Error("bad index record: " + line)

        path = vals[0]
        mtime, size = int(vals[1]), int(vals[2])

        return path, mtime, size

    @staticmethod
    def _fmt(path, mtime, size):
        return "%s\t%d\t%d" % (path, mtime, size)

    @staticmethod
    def _parse_paths(paths):
        includes = []
        excludes = []

        for path in paths:
            if path[0] == '-':
                excludes.append(abspath(path[1:]))
            else:
                includes.append(abspath(path))

        return includes, excludes

    @staticmethod
    def _included(path, includes):
        for include in includes:
            if path == include or path.startswith(include + '/'):
                return True

        return False

    def __init__(self, fromfile=None):
        if fromfile:
            for line in file(fromfile).readlines():
                path, mtime, size = self._parse(line)
                self[path] = (mtime, size)

    def walk(self, *paths):
        """walk paths and add files to index"""
        includes, excludes = self._parse_paths(paths)

        def excluded(path):
            for exclude in excludes:
                if path == exclude or path.startswith(exclude + '/'):
                    return True

            return False

        def _walk(dir):
            fnames = []

            for dentry in os.listdir(dir):
                path = join(dir, dentry)
                if islink(path) or not isdir(path):
                    fnames.append(dentry)
                else:
                    for val in _walk(path):
                        yield val

            yield dir, fnames

        for path in includes:
            if islink(path) or not isdir(path):
                continue

            for dpath, fnames in _walk(path):
                for fname in fnames:
                    path = join(dpath, fname)

                    if self._included(path, excludes):
                        continue
                    
                    st = os.lstat(path)
                    self[path] = (int(st.st_mtime), int(st.st_size))

    def prune(self, *paths):
        """prune index down to paths that are included AND not excluded"""

        includes, excludes = self._parse_paths(paths)

        for path in self.keys():
            if not self._included(path, includes) or self._included(path, excludes):
                del self[path]

    def save(self, tofile):
        fh = file(tofile, "w")
        paths = self.keys()
        paths.sort()
        for path in paths:
            print >> fh, self._fmt(path, *self[path])

    def new_or_changed(self, other):
        a = set(self)
        b = set(other)

        delta = list(b - a)
        samepaths = b & a

        # add to delta files with different sizes / timestamps
        for path in samepaths:
            if self[path] != other[path]:
                delta.append(path)
        
        return delta

def create(path_index, paths):
    """create index from paths"""
    di = DirIndex()
    di.walk(*paths)
    di.save(path_index)

def sorted(method):
    def wrapper(*args, **kws):
        retval = list(method(*args, **kws))
        retval.sort()
        return retval

    return wrapper

@sorted
def new_or_changed(path_index, paths):
    """compare index with paths and return list of new or changed files"""
    di_saved = DirIndex(path_index)
    di_fs = DirIndex()
    di_fs.walk(*paths)

    return di_saved.new_or_changed(di_fs)

@sorted
def deleted(path_index, paths):
    """return a list of paths which are in index but not in paths"""
    di_saved = DirIndex(path_index)
    di_saved.prune(*paths)

    di_fs = DirIndex()
    di_fs.walk(*paths)

    return set(di_saved) - set(di_fs)
