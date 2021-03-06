#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals

from perceptionmd.utils import gc_after
import threading
import numpy as np

from abc import abstractmethod
import cachetools
from collections import defaultdict


class VolumeReader(object):

    lock = threading.RLock()

    def __init__(self, lock=None,
                 cache=None,
                 dtype=np.float32,
                 shape='auto',
                 *args, **kwargs):
        self.cache = cachetools.LRUCache(maxsize=1)
        self.dtype = dtype
        self.volume_shapes = {}
        self.volume_types = {}
        self.cache = cache
#        self.lock = lock
        self.threads = []
        self.UID2dir_cache = defaultdict(str)

    def UID2dir(self, UID):
        return self.UID2dir_cache[UID]

    @gc_after
    def clear(self):
        self.cleanup()
        self.UID2dir_cache = defaultdict(str)
        del self.threads[:]
        self.cache = {}
        self.UID2dir_cache.clear()
        self.volume_shapes.clear()
        self.volume_types.clear()

    @gc_after
    def cleanup(self):
        result = []
        with self.lock:
            for thread in self.threads:
                if thread.is_alive():
                    result.append(thread)
        self.threads = result

    def preload_volume(self, UID):
        with self.lock:
            caching_thread = threading.Thread(target=self.volume, args=(UID,))
            self.threads.append(caching_thread)
        caching_thread.start()

    @abstractmethod
    def volume_iterator(self, directory):   # pragma: no cover
        yield None

    @abstractmethod
    def volume(self, UID):   # pragma: no cover
        return None, defaultdict(lambda: None)
