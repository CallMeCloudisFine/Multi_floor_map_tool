import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np

from core.pointcloud_io import load_pcd
from core.pointcloud_processor import PointCloudProcessor, PreprocessingParams


HEADER = '''# .PCD v0.7
VERSION 0.7
FIELDS x y z
SIZE 4 4 4
TYPE F F F
COUNT 1 1 1
WIDTH 3
HEIGHT 1
VIEWPOINT 0 0 0 1 0 0 0
POINTS 3
DATA ascii
'''


class PointCloudTests(unittest.TestCase):
    def test_statistics_and_original_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'map.pcd'
            path.write_text(HEADER + '-1 2 0\n3 -4 5\n0 1 2\n')
            digest = hashlib.sha256(path.read_bytes()).digest()
            loaded = load_pcd(path)
            self.assertEqual(loaded.count, 3)
            self.assertEqual(loaded.minimum, (-1, -4, 0))
            self.assertEqual(loaded.maximum, (3, 2, 5))
            display = PointCloudProcessor.process(loaded.cloud, PreprocessingParams(.05))
            display.translate([100, 0, 0])
            np.testing.assert_array_equal(np.asarray(loaded.cloud.points)[0], [-1, 2, 0])
            self.assertFalse(loaded.cloud.has_colors())
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), digest)

    def test_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.pcd'
            with self.assertRaises(ValueError):
                load_pcd(path)
            path.write_text('not a point cloud')
            with self.assertRaises(ValueError):
                load_pcd(path)
            path.write_text(HEADER + 'nan 0 0\n0 1 2\n0 0 0\n')
            with self.assertRaises(ValueError):
                load_pcd(path)


if __name__ == '__main__':
    unittest.main()
