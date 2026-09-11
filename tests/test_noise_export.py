from dataclasses import replace
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import open3d as o3d
import yaml
from core.pointcloud_processor import PointCloudProcessor, PreprocessingParams
from core.export_manager import export_pcd
from models.floor import Floor


class NoiseExportTests(unittest.TestCase):
    def setUp(self):
        self.points=np.vstack((np.random.default_rng(7).normal(0,.02,(150,3)),[[5,5,5],[10,10,10]]))
        self.cloud=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(self.points))

    def test_statistical_and_radius_remove_isolated_points(self):
        for params in (PreprocessingParams(statistical_enabled=True),
                       PreprocessingParams(radius_enabled=True,radius=.2,min_neighbors=3),
                       PreprocessingParams(statistical_enabled=True,radius_enabled=True)):
            with self.subTest(params=params):
                result=PointCloudProcessor.process(self.cloud,params)
                self.assertGreater(len(result.points),100)
                self.assertLessEqual(len(result.points),150)
                self.assertLess(np.asarray(result.points).max(),1)
        np.testing.assert_array_equal(np.asarray(self.cloud.points),self.points)

    def test_invalid_and_small_neighborhoods(self):
        for params in (PreprocessingParams(statistical_enabled=True,std_ratio=0),
                       PreprocessingParams(radius_enabled=True,radius=-1),
                       PreprocessingParams(radius_enabled=True,min_neighbors=0)):
            with self.assertRaises(ValueError): PointCloudProcessor.process(self.cloud,params)
        tiny=self.cloud.select_by_index([0,1])
        with self.assertRaises(ValueError): PointCloudProcessor.process(tiny,PreprocessingParams(statistical_enabled=True))

    def test_export_roundtrip_and_source_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            source=folder/'source.pcd'
            o3d.io.write_point_cloud(str(source),self.cloud)
            digest=hashlib.sha256(source.read_bytes()).digest()
            params=PreprocessingParams(statistical_enabled=True)
            result=PointCloudProcessor.process(self.cloud,params)
            floor=Floor('floor_1',1,'floor_1',params=params,ground_z=0.0,ceiling_z=3.0,height_confirmed=True)
            out=export_pcd(source,result,params,floor,folder/'floor_1.pcd')
            loaded=o3d.io.read_point_cloud(str(out))
            np.testing.assert_allclose(np.asarray(loaded.points),np.asarray(result.points),atol=1e-7)
            rules=yaml.safe_load(out.with_suffix('.rules.yaml').read_text())
            self.assertEqual(rules['floor']['map_id'],1)
            self.assertTrue(rules['preprocessing']['statistical_enabled'])
            with self.assertRaises(FileExistsError): export_pcd(source,result,params,floor,out)
            with self.assertRaises(ValueError): export_pcd(source,result,params,floor,source,True)
            alias=folder/'alias.pcd'
            os.link(source,alias)
            with self.assertRaises(ValueError): export_pcd(source,result,params,floor,alias,True)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),digest)

    def test_failed_rules_replace_rolls_back_existing_pcd(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            source=folder/'source.pcd'
            source.write_text('original')
            output=folder/'floor.pcd'
            rules=output.with_suffix('.rules.yaml')
            output.write_bytes(b'old-pcd')
            rules.write_bytes(b'old-rules')
            real_replace=os.replace
            def fail_rules(src,dst):
                if Path(src).name=='rules.yaml': raise OSError('simulated rules failure')
                return real_replace(src,dst)
            with patch('core.export_manager.os.replace',side_effect=fail_rules),self.assertRaises(OSError):
                export_pcd(source,self.cloud,PreprocessingParams(),None,output,True)
            self.assertEqual(output.read_bytes(),b'old-pcd')
            self.assertEqual(rules.read_bytes(),b'old-rules')
            self.assertFalse(list(folder.glob('.strata-export-*')))
