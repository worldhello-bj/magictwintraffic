# 实施与交付边界

本仓库按 implementation_plan.md v4 开发。目标是具有可重复实验、真实路网和同源三维回放的离线情景实验系统。现场观测尚未提供；合成 OD、实验配时与行为假设均在输入与结果中标识。

## 本次授权与交付

- 在独立云端项目目录开发，不访问用户本机。
- 以源码分支和 Pull Request 交付 worldhello-bj/magictwintraffic，不直接合并。
- 一期 SUMO/libsumo + Python/FastAPI + Three.js/WebGL2。
- MOSS、UNsim、GPU 租赁和真实交管信号控制不进入一期执行。
- 缺少道路空间或安全参数证据的政策需报告不可行原因，不以改一个指标系数替代真实机制。
- 模型试验、现场校准、浏览器性能分别记录，不能互相替代。

## 官方技术依据

2026-10-09 核查：
- SUMO OSM 导入：https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html
- libsumo：https://sumo.dlr.de/docs/Libsumo.html
- 统计输出：https://sumo.dlr.de/docs/Simulation/Output/StatisticOutput.html
- OSM 数据许可：https://www.openstreetmap.org/copyright

OSM 数据及其派生数据库保留 OpenStreetMap contributors 署名和 ODbL 许可；代码沿用仓库 Apache-2.0。导入工具推导的连接、配时、默认属性不自动成为现场观测值。
