# 楼层高度与机器人索引

本次新增每层地面与天花板高度保存，不实现工程恢复和机器人判层程序。

## 使用

选中楼层，在右侧「楼层高度」填写：

- 地面基准 Z：该层地面在完整源 PCD 坐标系中的高度，单位米；允许地下层负值。
- 天花板 Z：天花板下表面在同一坐标系中的高度，必须高于地面；两者之差为层内净高，不是楼板到楼板的建筑层高。
- 地面高度容差：正数，用于描述地面参考带；默认 0.3 m，可人工调整。
- 坐标系：默认 `source_map`，应填写实际源地图坐标系名称。修改名称不变换点坐标。
- 人工确认：新楼层未勾选，避免初始候选范围被误认作实际地面/天花板；未确认不能保存楼层。

地面基准高度不是裁切下限、点云最小 Z、机器人机身高度或 PGM 的 origin 第三项。即使只保留墙面，地面高度仍可以低于实际保存点云的最低点。

填写高度后保存会生成：

```text
output/
├── floor_1.pcd
├── floor_1.rules.yaml
├── floor_2.pcd
├── floor_2.rules.yaml
└── floors.yaml
```

## floors.yaml 示例（说明用数据）

```yaml
schema_version: 2
source_pcd: /maps/building.pcd
coordinate_frame: source_map
units: meters
height_reference: ground_surface
floors:
  - floor_key: stable-internal-key
    floor_id: floor_2
    map_id: 2
    map_name: floor_2
    ground_z: 3.5
    ceiling_z: 6.2
    height_range: [3.5, 6.2]
    clear_height: 2.7
    height_range_complete: true
    ground_z_tolerance: 0.25
    ground_z_band: [3.25, 3.75]
    crop_z_range: [3.7, 5.0]
    point_cloud_z_range: [3.7, 4.2]
    pcd: floor_2.pcd
    rules: floor_2.rules.yaml
```

- `ground_z` / `ground_z_band`：人工确认的地面参考；不能直接与未经转换的雷达或 base_link 高度比较。
- `crop_z_range`：切分规则的闭区间；未启用裁切时为 null。
- `point_cloud_z_range`：处理后点云实际最小/最大 Z，包含降采样和去噪的影响。
- `pcd` / `rules`：相对于索引所在目录的文件名。尚未生成 PGM，不输出虚构的栅格文件路径。

`rules.yaml` 升级为 schema_version 3，保留完整编辑参数并增加坐标系/高度信息。当前没有规则文件导入 UI。

## 一致性与保存行为

同一导出目录自动合并已导出楼层。同一个内部 key 的再次保存更新该条目，其他楼层不受影响。新的会话重新创建逻辑楼层时，只有 floor_id/map_id/map_name/目标文件都匹配且明确同意覆盖，才能替换该记录。不同源地图、坐标系或身份冲突会拒绝写入。

不同输出目录各自维护索引。删除工作区楼层不删除磁盘文件，索引仍保留已导出记录。索引不是工程文件，也不包含未保存的草稿。

只修改高度元数据会保留有效点云预览；处理参数变化仍使预览失效。Reset 保留高度元数据并重置滤波参数，恢复上次保存会恢复高度和参数。

三个文件先暂存，再按顺序替换。普通异常回滚已替换目标；不保证断电时三个文件跨文件原子一致。新规则和索引成功写入后才提交内存中的保存状态。

## 文件变化与验证

- `models/floor.py`：地面/天花板、容差、坐标系、显式确认状态与导出前校验。
- `gui/height_range_slider.py`：双端点浮点滑块、鼠标拖动、键盘微调及防交叉。
- `gui/preprocessing_panel.py`：高度编辑和人工确认 UI。
- `core/edit_session.py`：高度元数据变化不使处理预览失效。
- `core/floor_index.py`：独立索引构建、合并与冲突校验。
- `core/export_manager.py`：保存 PCD、rules 和索引，失败回滚。
- `application/workspace_controller.py`：未确认提示与保存状态。
- `tests/test_floor_height.py`：高度与裁切区分、未确认/无效值、合并/重命名、源/坐标系冲突、损坏索引保护、写入回滚、元数据恢复。
- `scripts/smoke_workspace.py`：真实桌面确认高度、保留预览、保存两层并检查索引、切换与撤销。

运行：

```bash
.venv/bin/python main.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/smoke_workspace.py
```

已完成真实桌面流程验证；楼层独立处理、去噪、视角和原文件保护回归通过。原始 PCD 及其他工作区项目不受影响。

## 双滑块验证

23 项核心测试通过，新增旧版索引迁移且不推断天花板测试；真实桌面覆盖两个滑块拖动、防交叉、键盘微调、数值同步、非法范围保护、窄窗口无横向溢出，以及原有保存/去噪/独立楼层回归。

高度只作为元数据，不自动驱动裁切。`height_range` 表示地面到天花板的几何范围，`clear_height` 是差值，不保证中间没有障碍物，也不代替机器人判层逻辑。
