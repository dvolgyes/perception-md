#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals

import numpy as np
import os
import pydicom as dicom
from . import VolumeReader
from collections import defaultdict
from perceptionmd.utils import at_least_3d
from perceptionmd.utils import gc_after


class DICOMDIR(VolumeReader.VolumeReader):

    def __init__(self, *args, **kwargs):
        super(DICOMDIR, self).__init__(*args, **kwargs)
        self.filename_cache = defaultdict(list)

    def volume_iterator(self, dirname):
        volnames = []
        for root, _, filenames in os.walk(dirname, followlinks=True):
            for f in filenames:
                p = os.path.join(root, f)
                try:
                    ds = dicom.read_file(p)
                    series = ds.SeriesInstanceUID
                    self.filename_cache[series].append(p)
                    self.UID2dir_cache[series] = root
                    volnames.append((series, root))
                except Exception:  # pragma: no cover
                    pass
        for volname, _ in sorted(list(set(volnames)), key=lambda x: x[1]):
            yield volname

    @gc_after
    def volume(self, UID):
        meta = defaultdict(lambda: None)
        with self.lock:
            if UID in self.cache and self.cache[UID] is not None:
                return self.cache[UID]
            zpos = []
            for f in self.filename_cache[UID]:
                slope, intercept = 1, 0
                pixel_size = [1., 1., 1.]
                ds = dicom.read_file(f)
                z = ds.SliceLocation if 'SliceLocation' in ds else 0
                if 'RescaleIntercept' in ds:
                    intercept = ds.RescaleIntercept
                if 'RescaleSlope' in ds:
                    slope = ds.RescaleSlope
                if 'SliceThickness' in ds:
                    pixel_size[0] = float(ds.SliceThickness)
                if 'PixelSpacing' in ds:
                    y, x = ds.PixelSpacing
                    pixel_size[1], pixel_size[2] = float(y), float(x)

                vol = ds.pixel_array.astype(self.dtype) * slope + intercept
                zpos.append((z, vol))
            zpos = sorted(zpos, key=lambda x: x[0])
            _, volumes = zip(*zpos)
            volume = np.stack(volumes)
            meta['pixel_size'] = pixel_size
            self.cache[UID] = volume, meta
        return at_least_3d(volume), meta
