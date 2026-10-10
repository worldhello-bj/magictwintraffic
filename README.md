# First checkout: restore bundled data

Run `python scripts/restore_assets.py` once before Python commands. It reconstructs the exact licensed network and experiment assets from small lossless chunks, offline, with SHA-256 verification. Frontend npm commands restore automatically. Source code remains ordinary files; no repository ZIP is required.

# MagicTwinTraffic · 成都玉林交通政策实验

基于真实 OpenStreetMap 街区、SUMO/libsumo 和 Three.js 的可复算交通政策实验与离线回放原型。车辆位置来自实际仿真记录；界面不会用装饰性车辆或预设改善率替代结果。

**这是未经现场校准的情景实验系统。** 真实道路几何不等于真实当天交通。OD、配时、公交班次、临停和驾驶行为包含明确的实验假设；当前不用于真实信号机控制或现场收益保证。

![真实路网范围预览](docs/evidence/network-overview.png)

## 先看什么

- [实现计划](docs/implementation_plan.md)：研究目标与完整设计，不代表所有验收已完成。
- [方法与假设](docs/methods_and_assumptions.md)、[验收矩阵](docs/acceptance_matrix.md)、[交付边界](docs/delivery_scope.md)。
- [完整统计结论](docs/statistical_findings.md)：96 场探索 + 40 场调参 + 180 场独立验证；没有跨全部条件稳定优胜的政策。
- [下游接收鲁棒性](docs/robustness_findings.md)：另完成 24 场探索性敏感性实验，总计 340 场；不混入独立验证，也不代表全部鲁棒性已通过。
- [实际运行证据](docs/evidence/)：包括有 run ID 的基准对照、独立 TSTT 核查与阶段报告。文件名包含 `partial` 的报告是阶段快照，不能作为完整研究结论。
- [API 与任务服务](docs/api_service.md)、[前端与浏览器验证说明](web/README.md)。

默认回放目录仅发布最终 `joined_north_surface_v3` 路网的 **4 个高压 S0/S7 同需求配对回放**：早峰、晚峰各一组，固定 seed 42，每条 4,200 秒。默认从 t=1,200 秒查看已形成的拥堵，也可从头回放。前端首次开发、测试或构建只生成缺失的这四条记录；以后校验哈希后复用，不再自动生成旧 dense / internal / preview 演示。

每条回放同时提供从真实轨迹计算的逐路段热力统计：60 秒窗口和 300–4,200 秒全观察窗，支持观察速度、停止车辆和相对车道限速的速度损失。没有车辆样本的路段保持无数据；热力图不补造车辆、流量或延误。定义与限制见[高压实验和热力图说明](docs/high_pressure_demo.md)。

旧代表性回放不再出现在主目录，生产构建也会移除未发布的旧回放副本。旧 `runs/` 原始轨迹、仿真源码、历史研究和诊断证据仍保留，不改写既有结论。最终三种子政策实验共 12 次，主目录的四条 seed-42 回放不代表全部统计证据；大型轨迹由固定场景复算，不纳入 Git。

物理积分步长为 0.5 秒；发布时每秒选一个已有原始记录帧，抽帧不改变仿真或指标。本组 S7 不预设优于 S0，实际政策差异见[最终 v3 结果摘要](docs/high_pressure_demo.md#最终v3结果摘要12次运行已冻结)。

## 快速启动

推荐 Python 3.12、Node.js 22。后端按 Linux 的进程隔离、资源限制和取消机制实现；Windows 请使用 WSL 或 Docker Desktop。纯静态回放可在支持现代浏览器与本地 HTTP 服务的平台运行。

### 1. 安装依赖并构建前端

在仓库根目录执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
cd web
npm ci
npm run build
cd ..
```

依赖锁包含 SUMO/libsumo 1.28.0、PyArrow 23.0.1；不要随意更换其中一个后沿用旧结果。首次安装需要联网，构建后的回放不依赖 CDN、在线瓦片或外部字体。

### 2A. 只看离线回放

```sh
.venv/bin/python -m http.server 8080 --bind 127.0.0.1 --directory web/dist
```

打开 **http://127.0.0.1:8080**。没有后端时，已有回放和对照仍可使用，新增计算不可用。请通过 HTTP 打开，不能直接双击 `index.html`；Worker、校验和与压缩解码需要正常浏览器上下文。

### 2B. 启用可编辑实验

```sh
bash scripts/start_backend.sh
```

打开 **http://127.0.0.1:8000**；API 文档位于 **http://127.0.0.1:8000/docs**。同一进程提供已构建前端和实验 API。可编辑 OD、选择政策及其适用参数，提交、查看进度、取消，成功后打开本次真实结果。

开发前端可另开终端执行 `cd web && npm run dev -- --host 127.0.0.1`，Vite 将 `/api` 代理到端口 8000。

也提供 `docker compose up --build` 和 Windows 启动脚本。容器与 Windows 运行情况应单独验收；提供配置文件本身不等于已通过对应平台测试。

### 安全与运行约束

- 默认仅绑定本机。公开部署前配置 `TRAFFIC_API_TOKEN`、TLS 与认证反向代理；不把密钥写入仓库。
- 后端只运行 **一个 Uvicorn 进程**，不要增加 `--workers`；SQLite 队列由单一调度器拥有。
- `TRAFFIC_STATE_DIR` 可指定管理员控制的结果目录，默认 `var/`。客户端不能指定服务器文件路径或命令。
- 长批次期间不要修改源码、依赖锁、网络、规范化数据或场景文件。任务指纹变化会使旧排队任务失效。
- 中断、取消与失败保留日志，不会作为成功回放；失败任务需明确重新提交。

## 真实地理数据与范围

中心为 WGS84 **104.0600°E、30.6270°N**，采用 **EPSG:32648 / UTM 48N** 米制投影。

- 核心治理区：投影坐标下严格 **1,000 × 1,000 m**；对应地表边长约 1,000.30 m，投影尺度差已记录。
- 外层请求范围：2,000 × 2,000 m。保留完整相交道路和路口后，实际包络约 **2.624 × 2.728 km**；包络包含空白边缘，不应称为完整铺满的 4 km² 仿真区。
- 当前生成数据：**1,525 条非内部边、5,976 条车道、689 个路口、44 个实验信号、33 个外边界源汇、2,198 个建筑轮廓**。车道数包含内部连接和非机动车/步行权限车道，并非机动车道路条数。
- 原始下载、来源日期、哈希与转换命令见 [`data/raw/provenance.json`](data/raw/provenance.json)；坐标检查、边界延续证据与缺失项见 [`data/canonical/validation.json`](data/canonical/validation.json) 和 [`gate_audit.json`](data/canonical/gate_audit.json)。
- 道路、建筑轮廓来自 OSM。建筑缺失高度使用注明为假设的示意高度；高架展示高程根据 OSM bridge/layer 推导，不是测量高程。
- 44 个信号是实验控制，不能解释为当地现行配时。缺失城市限速采用按道路等级明确列出的 20/30/40/50 km/h 假设；其他导入属性和连接仍需核查。

## 实际实现的八类政策

| 方案 | 当前机制 | 解释边界 |
|---|---|---|
| S0 | 固定实验配时、固定合成公交时刻与实际车辆临停 | 未经实测校准的基准 |
| S1 | 核心玉林走廊信号的有界绿灯延长 | 有限信号疏导近似，不模拟完整交警行为 |
| S2 | 人民南路四段既有 OSM 标记多车道路段的一条车道限制 passenger/private 车型，保留公交等其他类别通行 | 保持原宽度和几何；研究空间再分配，不声称可物理拓宽 |
| S3 | 玉林北/中/南路走廊共同周期、实验相位差及考虑下游占用的有界延长 | 原有黄灯/清空阶段保留；未验证现场最优性 |
| S4 | 指定核心住宅支路的小汽车穿行限制与合法路径重算 | 存在真实权限差异；当前 OD 下可以没有明显收益 |
| S5 | 将实际占道停靠车辆的停留时间缩短 | 不用任意容量系数，不模拟停车搜索收益 |
| S6 | 有真实停站行为的合成公交，满足条件时延长绿灯 | 没有乘客活动、候车或方式转移模型 |
| S7 | S3 + S5 + S6 | 组合可能相互抵消，不预设优于基准 |

可编辑的政策参数为绿灯延长秒数、下游占用阈值、治理后临停秒数，按方案检查适用性与范围。外部接收敏感性可在指定出口设置限速时窗，产生真实跟驰、排队和上游回溢。未知参数、不可达 OD 和不支持的配置不得静默忽略。

## 复算

### 从已归档 OSM 重建网络

```sh
.venv/bin/python scripts/build_network.py
```

默认使用仓库内原始快照；重复重建已验证产生相同网络哈希。`--download` 会重新获取官方 OSM 数据，可能改变网络与所有实验身份；不要在冻结批次中执行。

### 复算最终默认回放

```sh
# 校验已有导出；只在缺少有效记录时计算最终 v3 的四条 seed-42 回放。
.venv/bin/python scripts/ensure_high_pressure_demo.py

# 单独重建热力统计：只读已有真实轨迹，不运行 SUMO。
.venv/bin/python scripts/export_heatmaps.py
cd web && npm run build
```

需要完整三种子证据时，运行 `scripts/run_high_pressure_demo.py --seeds 42,43,44`；网页仍只发布四条 seed-42 配对。缺少主目录或热力统计时，已验证的回放可直接复用；不会为修复目录重新计算物理。已有但配置或路网不匹配的完成运行拒绝覆盖。仅四条回放的复算不会覆盖更完整的十二次研究报告，而会另存阶段证据。

历史 preview、dense 和 internal 场景的脚本和配置继续保留，显式执行时可复核旧结果；下一次前端生命周期会恢复最终四条主目录，不把旧版网络和不同观察窗混作政策对照。`--policies`、`--seeds`、`--periods`、`--scales`、`--rate` 是通用 `run_experiments.py` 批次参数；不需要回放的研究运行不要加 `--trajectory`。所有政策配对须使用相同外生需求、路网和评价窗口。直接 CLI 不受 API 队列的全部资源限制约束，应控制并发与磁盘。

### 正式研究与报告

```sh
.venv/bin/python scripts/report_results.py --write-plan reports/exploration-plan.json
.venv/bin/python scripts/run_study.py --plan reports/exploration-plan.json \
  --phase exploration --state var/exploration --workers 2
.venv/bin/python scripts/report_results.py --runs var/exploration/runs \
  --plan reports/exploration-plan.json --output reports/exploration.json
```

已完成并归档 **96 场探索、40 场调参和 180 场独立验证**。结果与限制见[完整统计结论](docs/statistical_findings.md)，阶段计划、逐次运行数据、执行台账和独立 TSTT 核查见 `docs/evidence/`。上面的命令用于重建探索阶段；参数选择、冻结及独立种子的完整步骤见[统计方法与完整命令](docs/methods_and_assumptions.md)。研究报告只读取真实文件，缺失运行保持缺失，不按计划填造结果。更广泛鲁棒性与现场校准仍未完成。

## 架构与结果口径

```text
data/raw + canonical → GIS / SUMO network
                    → immutable OD inventory → policy compiler
                    → isolated libsumo worker → evaluator + recorder
                    → SQLite scheduler / FastAPI → Three.js or same-data Canvas fallback
```

核心模块位于 `src/traffic_twin/`：`gis.py`、`demand.py`、`policies.py`、`simulation.py`、`evaluator.py`、`recorder.py`、`scheduler.py`、`api.py`、`analysis.py`。静态前端位于 `web/`。

每次运行保留 manifest、需求清单、政策与网络身份、行程摘要、指标、事件、审计、日志和可选轨迹。轨迹按 20 秒分块，32 字节小端记录，gzip 压缩、SHA-256 校验。`run_id / network_hash / demand_hash / policy_hash` 阻止不同运行或拓扑混播；前端最多缓存每个播放器四块数据。

- 每步检查已到出发时刻的需求 = 外部等待 + 在网 + 完成 + 明确失败；未来需求不计等待。
- 系统时间包含尚未进入路网的目标需求。完成车辆均值不能掩盖入口积压或未完成出行。
- 到达、插入事件按步末记录，存在步长级时间量化；核心/外围时间采用步末积分。
- 队列展示是低速车辆数量代理，不是已经核验的连续物理排队长度。
- 高峰后仍有积压则标记截尾。只展示有限窗口累计量、完成率和积压，不虚构最终旅行时间或全局赢家。

## 测试与尚未完成的验收

```sh
.venv/bin/python -m pytest -q
cd web && npm test && npm run build
```

交通测试覆盖真实网络八政策运行、OD 与队列守恒、真实下游阻塞、gzip/哈希、0.25/0.5 秒积分且保持 0.5 秒行为间隔，以及隔离小测试网络上的单车红灯停车。测试用小网络从不替代交付路网。API 测试覆盖排队、缓存、取消、失败、身份检查与实际 worker；前端包含实际发布文件与界面交互测试。

以下不能由代码测试替代：全部关键转向和信号的现场核查、同日观测校准、独立现场验证、行人/骑行者行为与人员门到门收益、现场校准的内部活动/停车容量、动态导航、完整客户端 GPU/FPS 验收，以及另一台干净机器/容器运行验证。WebGL 不可用时可退回相同数据的 Canvas；这不等于已完成 WebGL 性能测试。MOSS、UNsim、强化学习及 RTX 5090 加速未作为已交付能力宣称。

## 许可

代码沿用 [Apache-2.0](LICENSE)。地图及派生数据库 © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)，按 **ODbL 1.0** 使用；代码许可不替代地图许可。原始快照与派生数据应保留署名、来源和适用的数据库许可义务。SUMO、Three.js 及其依赖遵循各自许可。

## 建筑 OD、初始停车与高峰信号演示

最终高压回放包含建筑片区初始库存、内部产生/吸引、可下载 OD 表、真实 SUMO 信号与逐路段统计。所有库存和需求参数明确标记为未校准假设，边界流量不会复制，两层守恒逐步检查。[建筑 OD 说明](docs/internal_building_od.md)保留早期方法和诊断；旧演示不再由前端启动自动生成。
