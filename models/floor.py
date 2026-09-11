from dataclasses import dataclass, field
import re
import uuid
import math
from numbers import Real
from core.pointcloud_processor import PreprocessingParams


@dataclass(frozen=True)
class Floor:
    floor_id: str
    map_id: int
    map_name: str
    params: PreprocessingParams = field(default_factory=PreprocessingParams)
    color: tuple[float, float, float] = (.35, .83, .69)
    visible: bool = True
    key: str = field(default_factory=lambda: uuid.uuid4().hex)
    ground_z: float | None = None
    ground_z_tolerance: float = 0.3
    coordinate_frame: str = 'source_map'
    ceiling_z: float | None = None
    height_confirmed: bool = False

    def validate(self):
        for name, value in [('floor_id', self.floor_id), ('map_name', self.map_name)]:
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f'{name} 不能为空，也不能包含首尾空格。')
            if value in ('.', '..') or re.search(r'[/\\\x00-\x1f<>:"|?*]', value):
                raise ValueError(f'{name} 包含不允许的文件名字符。')
        if isinstance(self.map_id, bool) or not isinstance(self.map_id, int) or self.map_id < 0:
            raise ValueError('map_id 必须是非负整数。')
        self.params.validate()
        if self.ground_z is not None and (not isinstance(self.ground_z, Real) or isinstance(self.ground_z, bool) or not math.isfinite(self.ground_z)):
            raise ValueError('地面基准 Z 必须是有限数值。')
        if self.ceiling_z is not None and (not isinstance(self.ceiling_z, Real) or isinstance(self.ceiling_z, bool) or not math.isfinite(self.ceiling_z)):
            raise ValueError('天花板 Z 必须是有限数值。')
        if self.ground_z is not None and self.ceiling_z is not None and self.ceiling_z <= self.ground_z:
            raise ValueError('天花板必须高于地面。')
        if not isinstance(self.height_confirmed, bool):
            raise ValueError('高度确认状态必须为布尔值。')
        if not isinstance(self.ground_z_tolerance, Real) or isinstance(self.ground_z_tolerance, bool) or not math.isfinite(self.ground_z_tolerance) or self.ground_z_tolerance <= 0:
            raise ValueError('地面高度容差必须是大于 0 的有限数。')
        if not isinstance(self.coordinate_frame, str) or not self.coordinate_frame.strip() or self.coordinate_frame != self.coordinate_frame.strip() or re.search(r'\s', self.coordinate_frame):
            raise ValueError('坐标系名称不能为空或包含空白。')

    def validate_for_export(self):
        self.validate()
        if self.ground_z is None or self.ceiling_z is None or not self.height_confirmed:
            raise ValueError('请设置地面与天花板高度，并勾选人工确认后保存楼层。')
