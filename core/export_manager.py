"""Stage PCD, editing rules and floor index together; roll back ordinary errors."""
from dataclasses import asdict
import os
from pathlib import Path
import shutil
import tempfile
import numpy as np
import open3d as o3d
import yaml
from core.floor_index import build_floor_index


def export_paths(path):
    path = Path(path).expanduser().absolute()
    if path.suffix.lower() != '.pcd':
        path = path.with_suffix('.pcd')
    return path, path.with_suffix('.rules.yaml')


def export_pcd(source_path, cloud, params, identity, output_path, overwrite=False):
    params.validate()
    if identity is not None:
        identity.validate_for_export()
    if not len(cloud.points):
        raise ValueError('空点云不能保存。')
    output, rules = export_paths(output_path)
    source = Path(source_path).resolve()
    index = output.parent / 'floors.yaml' if identity is not None else None
    targets = [output, rules] + ([index] if index is not None else [])
    for target in targets:
        if target.is_symlink():
            raise ValueError('导出目标不能是符号链接，请选择独立的新文件。')
        if target.resolve() == source or (target.exists() and os.path.samefile(target, source)):
            raise ValueError('不能覆盖完整原始 PCD，请选择其他文件名。')
        if target.exists() and target != index and not overwrite:
            raise FileExistsError(f'文件已存在：{target.name}')
        if target.exists() and not target.is_file():
            raise ValueError(f'目标不是文件：{target}')
    if not output.parent.is_dir():
        raise ValueError('输出目录不存在。')
    points_z = np.asarray(cloud.points)[:, 2]
    actual_z = [float(points_z.min()), float(points_z.max())]
    index_document = build_floor_index(index, source, identity, params, output, actual_z, overwrite) if index else None
    metadata = {'schema_version': 3, 'source_pcd': str(source),
                'output_pcd': output.name, 'point_count': len(cloud.points),
                'coordinate_frame': identity.coordinate_frame if identity else None,
                'units': 'meters', 'height_reference': 'ground_surface' if identity else None,
                'point_cloud_z_range': actual_z,
                'processing_order': ['crop', 'voxel', 'statistical', 'radius'],
                'preprocessing': asdict(params),
                'floor': asdict(identity) if identity is not None else None}
    with tempfile.TemporaryDirectory(prefix='.strata-export-', dir=output.parent) as temporary:
        temporary = Path(temporary)
        pending_pcd, pending_yaml = temporary / 'cloud.pcd', temporary / 'rules.yaml'
        if not o3d.io.write_point_cloud(str(pending_pcd), cloud, write_ascii=False, compressed=True):
            raise OSError('Open3D 写入 PCD 失败。')
        pending_yaml.write_text(yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False), encoding='utf-8')
        pending = [(pending_pcd, output), (pending_yaml, rules)]
        if index_document is not None:
            pending_index = temporary / 'index.yaml'
            pending_index.write_text(yaml.safe_dump(index_document, allow_unicode=True, sort_keys=False), encoding='utf-8')
            pending.append((pending_index, index))
        backups = {}
        for i, target in enumerate(targets):
            if target.exists():
                backup = temporary / f'backup-{i}'
                shutil.copy2(target, backup)
                backups[target] = backup
        replaced = []
        try:
            for staged, target in pending:
                os.replace(staged, target)
                replaced.append(target)
        except Exception:
            for target in reversed(replaced):
                if target in backups:
                    os.replace(backups[target], target)
                else:
                    target.unlink(missing_ok=True)
            raise
    return output
