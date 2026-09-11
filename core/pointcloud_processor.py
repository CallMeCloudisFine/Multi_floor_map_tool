"""Pure preprocessing rules. Every evaluation starts from the original cloud."""
from dataclasses import dataclass
import copy
import math
import open3d as o3d


@dataclass(frozen=True)
class PreprocessingParams:
    voxel_size: float = 0.0
    crop_min: tuple[float, float, float] | None = None
    crop_max: tuple[float, float, float] | None = None
    statistical_enabled: bool = False
    nb_neighbors: int = 20
    std_ratio: float = 2.0
    radius_enabled: bool = False
    radius: float = 0.2
    min_neighbors: int = 3

    def validate(self):
        if not math.isfinite(self.voxel_size) or self.voxel_size < 0:
            raise ValueError('Voxel size 必须是有限的非负数；0 表示关闭降采样。')
        if self.statistical_enabled:
            if not isinstance(self.nb_neighbors, int) or self.nb_neighbors < 2:
                raise ValueError('统计滤波的邻居数必须是至少 2 的整数。')
            if not math.isfinite(self.std_ratio) or self.std_ratio <= 0:
                raise ValueError('标准差系数必须大于 0。')
        if self.radius_enabled:
            if not math.isfinite(self.radius) or self.radius <= 0:
                raise ValueError('邻域半径必须大于 0。')
            if not isinstance(self.min_neighbors, int) or self.min_neighbors < 1:
                raise ValueError('半径滤波的最少邻居数必须为正整数。')
        if (self.crop_min is None) != (self.crop_max is None):
            raise ValueError('裁切必须同时提供最小值和最大值。')
        if self.crop_min is not None:
            if len(self.crop_min) != 3 or len(self.crop_max) != 3:
                raise ValueError('裁切范围必须包含 XYZ 三个轴。')
            if not all(math.isfinite(v) for v in (*self.crop_min, *self.crop_max)):
                raise ValueError('裁切范围不能包含 NaN 或 Inf。')
            if any(a > b for a, b in zip(self.crop_min, self.crop_max)):
                raise ValueError('每个轴的最小值必须小于或等于最大值。')


class PointCloudProcessor:
    @staticmethod
    def process(original, params: PreprocessingParams):
        params.validate()
        # Crop before voxel averaging so rejected points cannot affect centroids.
        if params.crop_min is not None:
            result = original.crop(o3d.geometry.AxisAlignedBoundingBox(
                params.crop_min, params.crop_max))
        else:
            result = copy.deepcopy(original)
        if params.voxel_size > 0 and len(result.points):
            result = result.voxel_down_sample(params.voxel_size)
        if params.statistical_enabled and len(result.points):
            if len(result.points) <= params.nb_neighbors:
                raise ValueError(f'当前仅 {len(result.points)} 点，统计滤波邻居数必须小于点数；请降低邻居数或关闭统计滤波。')
            result, _ = result.remove_statistical_outlier(params.nb_neighbors, params.std_ratio)
        if params.radius_enabled and len(result.points):
            result, _ = result.remove_radius_outlier(params.min_neighbors, params.radius)
        return result
