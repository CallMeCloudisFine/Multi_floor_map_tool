from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os
import numpy as np
import open3d as o3d
import yaml
from models.floor import Floor
from core.pointcloud_processor import PreprocessingParams
from core.pointcloud_io import LoadedCloud
from core.edit_session import EditSession
from core.export_manager import export_pcd


class HeightTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / 'source.pcd'
        self.cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector([[0,0,3.7],[1,1,4.2]]))
        o3d.io.write_point_cloud(str(self.source), self.cloud)
        self.params = PreprocessingParams(crop_min=(-1,-1,3.7),crop_max=(2,2,5))
        self.floor = Floor('floor_2',2,'floor_2',params=self.params,ground_z=3.5,ground_z_tolerance=.25,ceiling_z=6.5,height_confirmed=True)
        self.output = self.root / 'floor_2.pcd'

    def save(self, floor=None, output=None, overwrite=False):
        return export_pcd(self.source,self.cloud,self.params,floor or self.floor,output or self.output,overwrite)

    def test_ground_crop_and_actual_heights_are_distinct(self):
        self.save()
        rules = yaml.safe_load(self.output.with_suffix('.rules.yaml').read_text())
        index = yaml.safe_load((self.root/'floors.yaml').read_text())
        entry = index['floors'][0]
        self.assertEqual(rules['floor']['ground_z'],3.5)
        self.assertEqual(entry['ground_z_band'],[3.25,3.75])
        self.assertEqual(entry['height_range'],[3.5,6.5])
        self.assertEqual(entry['clear_height'],3.0)
        self.assertEqual(rules['floor']['ceiling_z'],6.5)
        self.assertTrue(rules['floor']['height_confirmed'])
        self.assertEqual(entry['crop_z_range'],[3.7,5])
        self.assertEqual(entry['point_cloud_z_range'],[3.7,4.2])
        self.assertEqual(entry['pcd'],'floor_2.pcd')
        self.assertEqual(index['height_reference'],'ground_surface')
        np.testing.assert_allclose(np.asarray(o3d.io.read_point_cloud(str(self.output)).points),np.asarray(self.cloud.points))

    def test_missing_and_invalid_heights(self):
        for fields in [{'ceiling_z':None},{'ceiling_z':3.5},{'ceiling_z':3.0},{'ceiling_z':float('nan')},{'height_confirmed':False},{'ground_z':None},{'ground_z':float('nan')},{'ground_z':float('inf')},
                       {'ground_z':True},{'ground_z_tolerance':0},{'ground_z_tolerance':-1},
                       {'coordinate_frame':''},{'coordinate_frame':'map frame'}]:
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                self.save(replace(self.floor,**fields))
        self.assertFalse(self.output.exists())
        # Negative heights are valid for basements.
        replace(self.floor,ground_z=-3.0).validate_for_export()

    def test_merge_rename_and_restart_overwrite(self):
        self.save()
        other = Floor('floor_3',3,'floor_3',ground_z=7,ceiling_z=10,height_confirmed=True)
        self.save(other,self.root/'floor_3.pcd')
        renamed = replace(self.floor,map_name='upper_lobby',ground_z=3.6)
        self.save(renamed,overwrite=True)
        entries = yaml.safe_load((self.root/'floors.yaml').read_text())['floors']
        self.assertEqual(len(entries),2)
        self.assertEqual(entries[0]['map_name'],'upper_lobby')
        recreated = replace(renamed,key='new-session-key')
        self.save(recreated,overwrite=True)
        self.assertEqual(len(yaml.safe_load((self.root/'floors.yaml').read_text())['floors']),2)
        with self.assertRaises(ValueError):
            self.save(replace(other,map_id=2),self.root/'collision.pcd')
        self.assertFalse((self.root/'collision.pcd').exists())

    def test_frame_and_source_conflicts_preserve_outputs(self):
        self.save()
        original = (self.root/'floors.yaml').read_bytes()
        with self.assertRaises(ValueError): self.save(replace(self.floor,coordinate_frame='another_map'),overwrite=True)
        other_source = self.root/'other.pcd'
        other_source.write_bytes(self.source.read_bytes())
        with self.assertRaises(ValueError):
            export_pcd(other_source,self.cloud,self.params,self.floor,self.output,True)
        self.assertEqual((self.root/'floors.yaml').read_bytes(),original)

    def test_index_failure_rolls_back_all_outputs(self):
        self.save()
        paths = [self.output,self.output.with_suffix('.rules.yaml'),self.root/'floors.yaml']
        before = [p.read_bytes() for p in paths]
        real_replace = os.replace
        def fail_index(src,dst):
            if Path(src).name == 'index.yaml': raise OSError('index write failed')
            return real_replace(src,dst)
        with patch('core.export_manager.os.replace',side_effect=fail_index),self.assertRaises(OSError):
            self.save(replace(self.floor,ground_z=3.8),overwrite=True)
        self.assertEqual([p.read_bytes() for p in paths],before)

    def test_metadata_edits_keep_preview_and_cancel_restore_height(self):
        session = EditSession()
        session.load(LoadedCloud(self.source,self.cloud,2,(0,0,3.7),(1,1,4.2)))
        floor = session.add_floor()
        session.stage(self.cloud,PreprocessingParams())
        with self.assertRaises(ValueError): session.export_ready()
        session.edit(PreprocessingParams(),replace(floor,ground_z=3.5,ceiling_z=6.5,height_confirmed=True))
        self.assertIs(session.current.preview,self.cloud)
        session.commit_saved(self.output)
        session.edit(PreprocessingParams(),replace(session.current.identity,ground_z=3.6))
        self.assertTrue(session.current.dirty)
        session.cancel()
        self.assertEqual(session.current.identity.ground_z,3.5)

    def test_full_map_export_needs_no_floor_height(self):
        export_pcd(self.source,self.cloud,PreprocessingParams(),None,self.root/'full_copy.pcd')
        self.assertFalse((self.root/'floors.yaml').exists())

    def test_legacy_ground_only_index_does_not_invent_ceiling(self):
        self.save()
        path=self.root/'floors.yaml'
        old=yaml.safe_load(path.read_text())
        old['schema_version']=1
        for field in ('ceiling_z','height_range','clear_height','height_range_complete'):
            old['floors'][0].pop(field)
        path.write_text(yaml.safe_dump(old))
        third=Floor('floor_3',3,'floor_3',ground_z=7,ceiling_z=10,height_confirmed=True)
        self.save(third,self.root/'floor_3.pcd')
        upgraded=yaml.safe_load(path.read_text())
        self.assertEqual(upgraded['schema_version'],2)
        self.assertIsNone(upgraded['floors'][0]['ceiling_z'])
        self.assertFalse(upgraded['floors'][0]['height_range_complete'])
        self.assertEqual(upgraded['floors'][1]['height_range'],[7,10])
        self.save(overwrite=True)
        self.assertTrue(yaml.safe_load(path.read_text())['floors'][0]['height_range_complete'])

    def test_malformed_existing_index_is_not_overwritten(self):
        self.save()
        index = self.root/'floors.yaml'
        original = yaml.safe_load(index.read_text())
        output_before = self.output.read_bytes()
        for field, value in [('map_id','2'), ('ground_z',None)]:
            import copy
            broken = copy.deepcopy(original)
            broken['floors'][0][field] = value
            index.write_text(yaml.safe_dump(broken))
            before = index.read_bytes()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.save(overwrite=True)
            self.assertEqual(index.read_bytes(),before)
            self.assertEqual(self.output.read_bytes(),output_before)
