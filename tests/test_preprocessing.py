import unittest
import numpy as np
import open3d as o3d
from pathlib import Path
from core.pointcloud_io import LoadedCloud
from core.pointcloud_processor import PointCloudProcessor, PreprocessingParams
from core.edit_session import EditSession


class PreprocessingTests(unittest.TestCase):
    def setUp(self):
        self.points = np.array([[0,0,0], [.01,.01,.01], [1,1,1], [2,2,2], [3,3,3]], dtype=float)
        self.cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(self.points))
        self.cloud.paint_uniform_color([.3,.5,.7])
        self.repo = EditSession()
        self.repo.load(LoadedCloud(Path('original.pcd'), self.cloud, 5, (0,0,0), (3,3,3)))

    def test_crop_closed_boundaries_and_empty(self):
        cropped = PointCloudProcessor.process(self.cloud, PreprocessingParams(0, (1,1,1), (2,2,2)))
        np.testing.assert_array_equal(np.asarray(cropped.points), [[1,1,1],[2,2,2]])
        empty = PointCloudProcessor.process(self.cloud, PreprocessingParams(0, (9,9,9), (10,10,10)))
        self.assertEqual(len(empty.points), 0)

    def test_preview_save_reset_and_no_cumulative_loss(self):
        params = PreprocessingParams(.1, (0,0,0), (1,1,1))
        result = PointCloudProcessor.process(self.repo.source.cloud, params)
        self.assertEqual(len(result.points), 2)
        self.repo.edit(params)
        self.repo.stage(result, params)
        self.assertEqual(len(self.repo.source.cloud.points), 5)
        self.repo.commit_saved('/tmp/result.pcd')
        self.assertEqual(len(self.repo.current.saved_cloud.points), 2)
        repeated = PointCloudProcessor.process(self.repo.source.cloud, params)
        np.testing.assert_array_equal(np.asarray(repeated.points), np.asarray(result.points))
        wide = PointCloudProcessor.process(self.repo.source.cloud, PreprocessingParams())
        self.repo.edit(PreprocessingParams())
        self.repo.stage(wide, PreprocessingParams())
        self.repo.commit_saved('/tmp/result.pcd')
        self.assertEqual(len(self.repo.source.cloud.points), 5)
        self.repo.reset()
        self.assertEqual(self.repo.current.draft, PreprocessingParams())
        np.testing.assert_array_equal(np.asarray(self.cloud.points), self.points)
        np.testing.assert_allclose(np.asarray(self.cloud.colors), np.tile([.3,.5,.7], (5,1)))

    def test_empty_preview_cannot_save(self):
        self.repo.stage(o3d.geometry.PointCloud(), PreprocessingParams())
        with self.assertRaises(ValueError):
            self.repo.commit_saved('/tmp/result.pcd')
        self.assertEqual(len(self.repo.source.cloud.points), 5)

    def test_invalid_params(self):
        for params in [PreprocessingParams(-1), PreprocessingParams(float('nan')),
                       PreprocessingParams(0, (2,0,0), (1,1,1)),
                       PreprocessingParams(0, (0,0,0)),
                       PreprocessingParams(0, (0,0,0), (1,float('inf'),1))]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                PointCloudProcessor.process(self.cloud, params)

    def test_cancel_preserves_original(self):
        self.repo.edit(PreprocessingParams(.1))
        self.repo.stage(PointCloudProcessor.process(self.cloud, PreprocessingParams(.1)), PreprocessingParams(.1))
        self.repo.cancel()
        self.assertIsNone(self.repo.current.preview)
        self.assertEqual(len(self.repo.source.cloud.points), 5)


if __name__ == '__main__':
    unittest.main()
