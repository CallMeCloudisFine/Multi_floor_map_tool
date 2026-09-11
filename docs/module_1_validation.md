# 模块 1 验证记录

日期：2026-09-11。

环境：Python 3.10.12、PySide6 6.11.2、Open3D 0.19.0、NumPy 2.2.6，Linux Wayland 桌面通过 XWayland 运行。

通过的检查：

- Python compileall 语法检查。
- 三楼层样例：5,043 点，XYZ 范围分别为 [0,10]、[0,7.5]、[0,8]。
- 两项 unittest：异常输入拒绝、统计正确、显示副本修改不影响原始点坐标/颜色/源文件字节。
- 真实桌面 smoke_gui.py，退出码 0：异步加载、Qt 容器创建、Open3D 渲染帧非空、显示/隐藏、重置视角和关闭。

已解决的环境问题：

- ROS 的 scripts 包与本地脚本目录重名：增加显式 __init__.py。
- 缺少 libxcb-cursor0：Ubuntu 软件源下载至 .runtime 并本地加载，没有安装系统包。
- GLFW 自动选择 Wayland 导致 GLEW 初始化失败：在导入 Open3D 前仅修改当前进程环境，统一 Qt/GLFW 为 X11。

尚未人工验证：鼠标旋转/平移/缩放手感、长时间使用和超大 PCD 的性能。当前测试使用生成的 XYZ 样例，不代表所有 PCD 自定义字段兼容性。

本模块未修改已有项目；后续预处理、Floor/ROI、保存和导出尚未实现。
