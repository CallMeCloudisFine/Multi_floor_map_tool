"""Robot-facing floor metadata, separate from cloud selection rules."""
from pathlib import Path
import yaml
from models.floor import Floor


def build_floor_index(path, source, identity, params, output, actual_z, overwrite=False):
    path, source, output = Path(path), Path(source).resolve(), Path(output)
    identity.validate_for_export()
    document = {'schema_version': 2, 'source_pcd': str(source),
                'coordinate_frame': identity.coordinate_frame, 'units': 'meters',
                'height_reference': 'ground_surface', 'floors': []}
    if path.exists():
        try:
            old = yaml.safe_load(path.read_text(encoding='utf-8'))
        except (OSError, yaml.YAMLError) as exc:
            raise ValueError(f'无法读取 floors.yaml，未修改现有导出：{exc}') from exc
        if not isinstance(old, dict) or old.get('schema_version') not in (1,2) or not isinstance(old.get('floors'), list):
            raise ValueError('现有 floors.yaml 格式或版本不支持，请选择其他导出目录。')
        if old.get('source_pcd') != str(source):
            raise ValueError('此目录的 floors.yaml 属于另一张原始地图，请选择独立目录。')
        if old.get('coordinate_frame') != identity.coordinate_frame or old.get('units') != 'meters' or old.get('height_reference') != 'ground_surface':
            raise ValueError('楼层索引的坐标系或高度参考不一致，请使用同一原始坐标系。')
        entries = old['floors']
        for field in ('floor_key', 'floor_id', 'map_id', 'map_name', 'pcd'):
            values = [entry.get(field) if isinstance(entry, dict) else None for entry in entries]
            valid = (lambda v: isinstance(v,int) and not isinstance(v,bool) and v >= 0) if field == 'map_id' else (lambda v: isinstance(v,str) and bool(v))
            if any(not valid(v) for v in values) or len(set(values)) != len(values):
                raise ValueError(f'现有 floors.yaml 包含无效或重复的 {field}，请先修复索引。')
        for saved in entries:
            floor=Floor(saved['floor_id'], saved['map_id'], saved['map_name'],
                  ground_z=saved.get('ground_z'), ground_z_tolerance=saved.get('ground_z_tolerance',0),
                  ceiling_z=saved.get('ceiling_z'), coordinate_frame=old['coordinate_frame'])
            floor.validate()
            if floor.ground_z is None:
                raise ValueError('现有索引缺少地面高度。')
            if floor.ceiling_z is None:
                if old['schema_version']==2 and saved.get('height_range_complete') is not False:
                    raise ValueError('现有索引缺少天花板高度。')
                saved.update(ceiling_z=None,height_range=None,clear_height=None,height_range_complete=False)
        document = old
        document['schema_version']=2
    entry = {'floor_key': identity.key, 'floor_id': identity.floor_id,
             'map_id': identity.map_id, 'map_name': identity.map_name,
             'ground_z': identity.ground_z, 'ground_z_tolerance': identity.ground_z_tolerance,
             'ceiling_z': identity.ceiling_z,
             'height_range': [identity.ground_z,identity.ceiling_z],
             'clear_height': identity.ceiling_z-identity.ground_z,
             'height_range_complete': True,
             'ground_z_band': [identity.ground_z - identity.ground_z_tolerance,
                               identity.ground_z + identity.ground_z_tolerance],
             'crop_z_range': [params.crop_min[2], params.crop_max[2]] if params.crop_min is not None else None,
             'point_cloud_z_range': list(actual_z),
             'pcd': output.name, 'rules': output.with_suffix('.rules.yaml').name}
    remaining = []
    for existing in document['floors']:
        if existing['floor_key'] == identity.key:
            continue
        # A new app session may recreate a logical floor with a fresh internal key.
        same_logical_floor = all(existing[field] == entry[field] for field in ('floor_id','map_id','map_name','pcd'))
        if same_logical_floor and overwrite:
            continue
        for field in ('floor_id','map_id','map_name','pcd'):
            if existing[field] == entry[field]:
                raise ValueError(f'导出索引中 {field} 已属于其他楼层；请使用独立标识和文件名。')
        remaining.append(existing)
    document['floors'] = sorted([*remaining, entry], key=lambda item: item['map_id'])
    return document
