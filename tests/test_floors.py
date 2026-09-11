from dataclasses import replace
from pathlib import Path
import unittest
import numpy as np
import open3d as o3d
from core.floor_manager import FloorManager
from core.edit_session import EditSession
from core.pointcloud_io import LoadedCloud
from core.pointcloud_processor import PointCloudProcessor, PreprocessingParams


class FloorTests(unittest.TestCase):
    def test_identity_uniqueness(self):
        manager = FloorManager()
        a,b = manager.create(),manager.create()
        for field in ('floor_id','map_id','map_name'):
            with self.subTest(field=field),self.assertRaises(ValueError):
                manager.put(replace(b,**{field:getattr(a,field)}))
        manager.put(replace(a,map_name='大厅',map_id=11))
        self.assertEqual(manager.floors[a.key].map_id,11)

    def test_independent_floor_source_drafts_and_saved_states(self):
        points = np.array([[0,0,0],[.01,.01,0],[0,0,3],[1,1,3]],float)
        cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
        session = EditSession()
        session.load(LoadedCloud(Path('source.pcd'),cloud,4,(0,0,0),(1,1,3)))
        # Processing Full Map must not become the source of a subsequently created floor.
        params = PreprocessingParams(.1,(-1,-1,-1),(2,2,1))
        session.edit(params)
        session.stage(PointCloudProcessor.process(session.source.cloud,params),params)
        first = session.add_floor()
        self.assertEqual(session.current.draft,PreprocessingParams())
        session.edit(params,replace(first,params=params,ground_z=0.0,ceiling_z=3.0,height_confirmed=True))
        result = PointCloudProcessor.process(session.source.cloud,params)
        self.assertEqual(len(result.points),1)
        session.stage(result,params)
        session.commit_saved('/tmp/floor1.pcd')
        second = session.add_floor()
        params2 = PreprocessingParams(0,(-1,-1,2),(2,2,4))
        session.edit(params2,replace(second,params=params2))
        result2 = PointCloudProcessor.process(session.source.cloud,params2)
        self.assertEqual(len(result2.points),2)
        session.stage(result2,params2)
        session.selected = first.key
        self.assertEqual(session.current.draft,params)
        self.assertEqual(len(session.current.saved_cloud.points),1)
        session.reset()
        self.assertEqual(len(session.current.preview.points),4)
        self.assertEqual(session.states[second.key].draft,params2)
        session.cancel()
        self.assertEqual(len(session.current.preview.points),1)
        np.testing.assert_array_equal(np.asarray(cloud.points),points)

    def test_stale_preview_and_invalid_identity(self):
        session=EditSession()
        cloud=o3d.geometry.PointCloud(o3d.utility.Vector3dVector([[0,0,0]]))
        session.load(LoadedCloud(Path('a.pcd'),cloud,1,(0,0,0),(0,0,0)))
        floor=session.add_floor()
        session.stage(cloud,PreprocessingParams())
        session.edit(PreprocessingParams(.1),floor)
        with self.assertRaises(ValueError): session.export_ready()
        session.edit(PreprocessingParams(),replace(floor,map_name='../bad'))
        with self.assertRaises(ValueError): session.validate()
        session.edit(PreprocessingParams(),floor)
        session.stage(o3d.geometry.PointCloud(),PreprocessingParams())
        with self.assertRaises(ValueError): session.export_ready()
