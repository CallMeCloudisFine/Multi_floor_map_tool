"""PCD loading, independent of Qt; source files are never modified."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import open3d as o3d


@dataclass(frozen=True)
class LoadedCloud:
    path: Path
    cloud: o3d.geometry.PointCloud
    count: int
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]


def load_pcd(path: str | Path) -> LoadedCloud:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"文件不存在：{path}")
    if path.suffix.lower() != '.pcd':
        raise ValueError('请选择 .pcd 点云文件')
    cloud = o3d.io.read_point_cloud(str(path))
    points = np.asarray(cloud.points)
    if not len(points):
        raise ValueError('PCD 为空或无法解析')
    if not np.isfinite(points).all():
        raise ValueError('点云包含 NaN/Inf 坐标，请清理源文件的副本后加载')
    return LoadedCloud(path, cloud, len(points), tuple(points.min(axis=0)),
                       tuple(points.max(axis=0)))
