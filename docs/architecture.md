# 当前架构：独立楼层 + 共用预处理

用户已将原先的「WorkingCloud → Z 楼层切分」流程调整为独立楼层处理。当前权威设计如下：

```text
完整源 PCD（只读）
  ├── 完整地图对象：独立草稿 / 预览 / 另存副本
  ├── floor_1：裁切 → Voxel → 统计去噪 → 半径去噪 → floor_1.pcd
  └── floor_2：裁切 → Voxel → 统计去噪 → 半径去噪 → floor_2.pcd
```

任何对象的处理结果都不是其他对象的输入。每次预览从 source.cloud 重新计算，原始文件从不写入。

- GUI：MainWindow、一个 PreprocessingPanel、PointCloudView。
- 应用层：WorkspaceController 管理选择对象、后台任务和刷新；耗时处理不在 GUI 线程。
- Core：EditSession 管理每对象 EditState，PointCloudProcessor 执行算法，ExportManager 写入文件，FloorManager 检查标识。
- Models：Floor 拥有稳定内部 key、唯一身份、颜色和完整 PreprocessingParams。

EditState 保存草稿参数/身份、预览结果及对应参数、上次保存参数/身份/点云/路径和未保存状态。切换对象保留草稿；参数或身份改变使旧预览失效。只有有效非空预览允许保存。

保存先写 PCD 与 rules YAML 临时文件，成功替换后才提交会话状态；普通异常恢复旧输出。原始源路径和链接均受保护，工作区中不同对象不允许复用输出路径。

旧 FloorSplitter、FloorPanel 和分开的 FloorController 已移除。今后多个 ROI 可以扩展 PreprocessingParams 和 PointCloudProcessor；PGM 生成器直接消费每个楼层的已处理点云。

渲染仍使用 Linux X11/XWayland：隐藏创建 Open3D 原生窗口，再交由 Qt 嵌入。数字键 1–4 绑定标准视角，着色通过显式按钮选择。Qt 快捷键限定视图区，输入框中的数字不触发视角。
