# 成都玉林路网尽端逐点核查

审计日期：2026-10-10。范围：joined_north_surface_v3 全部单支道路尽端，另外检查小客车过滤边界。

## 结论与边界

发现 159 个单支尽端：51个边界裁切、108个源图尽端。源图尽端不能直接称为现场真实断头路。
其中 60 个允许小客车、99 个仅其他模式；另有 5 处小客车尽端仍接步行等道路。
源图继续且位于请求范围之外的点才标记边界裁切；不是把所有边界附近点都当裁切。两处二环高架缺失续段由已归档节点-道路API回复补证，层级不同不连接地面道路。
在单支尽端核查中未发现几何导入断裂或渲染漏段证据；北侧地面交叉口另发现多个0.20m外部段参与交叉占位闭环，详见north_lock_diagnostic及north_surface_review，不能将此处旧网长时间静止当成已验证真实容量过载。此前在v1确认2条源图motor_vehicle=yes道路在SUMO中仍排除passenger（1491845448玉林五巷、1033678581首航欣程附近path）；这是权限不一致，不是几何断路。service默认只允许delivery/pedestrian/bicycle，不能把此模型默认值当成现场禁止小客车。已在独立joined_nijiaqiao_access_v2中修复这两条源图显式允许的权限，保留原网和所有几何/宽度/速度/信号/连接。2条车行测试67秒全部完成、零碰撞/瞬移。原始OSM、baseline、joined变体和网站发布几何逐级对照。

北侧修正后（joined_north_surface_v3）保留全部旧网客车/公交进出动作及33条桥隧/异层道路；同4042行程对照完成2916→3984，4200秒仍余58辆但持续消散。此为模型拓扑修正，不是交通控制政策收益或现场信号验证。

## 独立现实资料

- [武侯社区发展基金会案例集，印刷页43–44](https://www.cwcdf.net/uploadfile/202203/b10aa77159ddb1f.pdf)：玉寿巷为近200米、连接6个院落的消防通道。仅支持用途，不证明今天的端点/门禁/车行连通。检索索引可读到该页内容，已下载原PDF并用pdftotext核对；印刷页46另描述门卫指挥车辆进出，不证明今天的合法通行权限。
- [红星新闻网2026-06-17引述成都轨道集团](https://news.chengdu.cn/2026/0617/6a324642cfd50212c36de349.shtml)：倪家桥站周边道路退围、部分恢复通行。不能据此推导精确转向关系或把旧施工交通组织作为现状。

## 可复现方法

运行 `.venv/bin/python scripts/audit_deadends.py`。对双向路段去除反向前缀后统计支路；排除8个仅连接同一邻居的小环/平行段误报。原OSM相邻节点、SUMO外部边、canonical及发布资产对照；小客车与步行分开。

补充5处多支单向边界源/汇（B编号），不混入159个单支尽端。SUMO步行交叉节点即使type=dead_end也不等于真实断路。

## 逐点清单

### D001 · 人民南路三段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0640515, 30.6397694；节点 1445484327。
- 道路类型：highway.primary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：459143638#0；原图相邻节点数：4。
- 来源：[OSM 100288873](https://www.openstreetmap.org/way/100288873)；[OSM 459143638](https://www.openstreetmap.org/way/459143638)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D002 · 人民南路三段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0639521, 30.6397672；节点 4794975945。
- 道路类型：highway.primary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：115625972#1；原图相邻节点数：4。
- 来源：[OSM 100288873](https://www.openstreetmap.org/way/100288873)；[OSM 115625972](https://www.openstreetmap.org/way/115625972)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D003 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0593883, 30.6374360；节点 13869892526。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-576684245#2, 576684245#2；原图相邻节点数：3。
- 来源：[OSM 1520242789](https://www.openstreetmap.org/way/1520242789)；[OSM 576684245](https://www.openstreetmap.org/way/576684245)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D004 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0571378, 30.6374145；节点 5478294504。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-569688450, 569688450；原图相邻节点数：3。
- 来源：[OSM 1348666270](https://www.openstreetmap.org/way/1348666270)；[OSM 569688450](https://www.openstreetmap.org/way/569688450)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D005 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0636286, 30.6372536；节点 13766510027。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1504427093#2；原图相邻节点数：1。
- 来源：[OSM 1504427093](https://www.openstreetmap.org/way/1504427093)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D006 · 小天西街 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0536959, 30.6371346；节点 432429376。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-37127682#3, 37127682#3；原图相邻节点数：4。
- 来源：[OSM 265592588](https://www.openstreetmap.org/way/265592588)；[OSM 37127682](https://www.openstreetmap.org/way/37127682)；[OSM 463252780](https://www.openstreetmap.org/way/463252780)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D007 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0680967, 30.6370752；节点 11775522772。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：1267914189#0；原图相邻节点数：3。
- 来源：[OSM 1267914188](https://www.openstreetmap.org/way/1267914188)；[OSM 1267914189](https://www.openstreetmap.org/way/1267914189)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D008 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0681823, 30.6370746；节点 11775516165。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：1267914187#1；原图相邻节点数：3。
- 来源：[OSM 1267914187](https://www.openstreetmap.org/way/1267914187)；[OSM 1267914188](https://www.openstreetmap.org/way/1267914188)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D009 · 电信南街 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0583902, 30.6368784；节点 1916386495。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：181190803#0；原图相邻节点数：3。
- 来源：[OSM 1348666270](https://www.openstreetmap.org/way/1348666270)；[OSM 181190803](https://www.openstreetmap.org/way/181190803)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D010 · 一环路南三段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0498629, 30.6367738；节点 5628750476。
- 道路类型：highway.primary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：538608173#0；原图相邻节点数：4。
- 来源：[OSM 538608173](https://www.openstreetmap.org/way/538608173)；[OSM 589463599](https://www.openstreetmap.org/way/589463599)；[OSM 890791642](https://www.openstreetmap.org/way/890791642)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D011 · 小天东街 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0560210, 30.6367129；节点 671587213。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-1446010549#0, 1446010549#0；原图相邻节点数：3。
- 来源：[OSM 1446010549](https://www.openstreetmap.org/way/1446010549)；[OSM 463252780](https://www.openstreetmap.org/way/463252780)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D012 · 一环路南三段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0514344, 30.6361409；节点 5514165381。
- 道路类型：highway.primary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：1505070688#3；原图相邻节点数：3。
- 来源：[OSM 1505070688](https://www.openstreetmap.org/way/1505070688)；[OSM 574483191](https://www.openstreetmap.org/way/574483191)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D013 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0677841, 30.6361507；节点 13275518521。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1446888290#0；原图相邻节点数：1。
- 来源：[OSM 1446888290](https://www.openstreetmap.org/way/1446888290)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D014 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0659722, 30.6361252；节点 3562117106。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1558886071#1；原图相邻节点数：1。
- 来源：[OSM 350464163](https://www.openstreetmap.org/way/350464163)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D015 · 一环路南二段辅路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0704318, 30.6361351；节点 5213238518。
- 道路类型：highway.secondary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：538608185#5；原图相邻节点数：3。
- 来源：[OSM 30549871](https://www.openstreetmap.org/way/30549871)；[OSM 538608185](https://www.openstreetmap.org/way/538608185)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D016 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0699565, 30.6361265；节点 3562117104。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：350464161；原图相邻节点数：3。
- 来源：[OSM 350464161](https://www.openstreetmap.org/way/350464161)；[OSM 785085436](https://www.openstreetmap.org/way/785085436)；[OSM 785085439](https://www.openstreetmap.org/way/785085439)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D017 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0726807, 30.6360812；节点 7334966723。
- 道路类型：highway.primary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：785085443；原图相邻节点数：2。
- 来源：[OSM 785085441](https://www.openstreetmap.org/way/785085441)；[OSM 785085443](https://www.openstreetmap.org/way/785085443)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D018 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0726784, 30.6360337；节点 7334966736。
- 道路类型：highway.primary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：785085440；原图相邻节点数：2。
- 来源：[OSM 785085440](https://www.openstreetmap.org/way/785085440)；[OSM 785085444](https://www.openstreetmap.org/way/785085444)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D019 · 一环路南二段辅路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0708465, 30.6359344；节点 1159173786。
- 道路类型：highway.secondary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：844894037#0；原图相邻节点数：3。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 844894037](https://www.openstreetmap.org/way/844894037)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D020 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0703160, 30.6358493；节点 7334966731。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：785085437；原图相邻节点数：1。
- 来源：[OSM 785085437](https://www.openstreetmap.org/way/785085437)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D021 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0697702, 30.6358297；节点 7334966732。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：785085438；原图相邻节点数：1。
- 来源：[OSM 785085438](https://www.openstreetmap.org/way/785085438)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D022 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0677991, 30.6358114；节点 13275518522。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1446888290#2；原图相邻节点数：1。
- 来源：[OSM 1446888290](https://www.openstreetmap.org/way/1446888290)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D023 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0663281, 30.6357541；节点 14181086053。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1558886071#0；原图相邻节点数：1。
- 来源：[OSM 1558886071](https://www.openstreetmap.org/way/1558886071)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D024 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0590788, 30.6356831；节点 13991663392。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1535753887；原图相邻节点数：1。
- 来源：[OSM 1535753887](https://www.openstreetmap.org/way/1535753887)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D025 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0707532, 30.6356458；节点 4693610132。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：475633281；原图相邻节点数：1。
- 来源：[OSM 475633281](https://www.openstreetmap.org/way/475633281)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D026 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0688162, 30.6356278；节点 4693610141。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633285, 475633285；原图相邻节点数：1。
- 来源：[OSM 475633285](https://www.openstreetmap.org/way/475633285)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D027 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0695083, 30.6356200；节点 4693610135。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：475633283；原图相邻节点数：1。
- 来源：[OSM 475633283](https://www.openstreetmap.org/way/475633283)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D028 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0672545, 30.6355715；节点 4693610143。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633286, 475633286；原图相邻节点数：1。
- 来源：[OSM 475633286](https://www.openstreetmap.org/way/475633286)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D029 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0706597, 30.6354109；节点 4693610134。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：475633282；原图相邻节点数：1。
- 来源：[OSM 475633282](https://www.openstreetmap.org/way/475633282)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D030 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0684007, 30.6353523；节点 4693610144。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633287#0, 475633287#0；原图相邻节点数：1。
- 来源：[OSM 475633287](https://www.openstreetmap.org/way/475633287)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D031 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0672745, 30.6353390；节点 4693610145。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633287#1, 475633287#1；原图相邻节点数：1。
- 来源：[OSM 475633287](https://www.openstreetmap.org/way/475633287)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D032 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0707540, 30.6352162；节点 4693610097。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：475633270；原图相邻节点数：1。
- 来源：[OSM 475633270](https://www.openstreetmap.org/way/475633270)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D033 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0691101, 30.6352040；节点 5141328840。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：529212267；原图相邻节点数：1。
- 来源：[OSM 529212267](https://www.openstreetmap.org/way/529212267)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D034 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0676448, 30.6351452；节点 4693610150。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633289#1, 475633289#1；原图相邻节点数：1。
- 来源：[OSM 475633289](https://www.openstreetmap.org/way/475633289)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D035 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0708772, 30.6348710；节点 4693609813。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-475633217#2, 475633217#2；原图相邻节点数：3。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 475633217](https://www.openstreetmap.org/way/475633217)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D036 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0483050, 30.6344804；节点 5514165383。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-574483192#0, 574483192#0；原图相邻节点数：3。
- 来源：[OSM 574483192](https://www.openstreetmap.org/way/574483192)；[OSM 589463599](https://www.openstreetmap.org/way/589463599)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D037 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0636188, 30.6344680；节点 13766510038。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1504427094#0；原图相邻节点数：1。
- 来源：[OSM 1504427094](https://www.openstreetmap.org/way/1504427094)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D038 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0499784, 30.6343219；节点 5514165398。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-574483194, 574483194；原图相邻节点数：1。
- 来源：[OSM 574483194](https://www.openstreetmap.org/way/574483194)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D039 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0681102, 30.6343400；节点 4693610161。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633228#3, 475633228#3；原图相邻节点数：1。
- 来源：[OSM 475633228](https://www.openstreetmap.org/way/475633228)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D040 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0701769, 30.6341448；节点 4693609815。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633218#5, 475633218#5；原图相邻节点数：1。
- 来源：[OSM 475633218](https://www.openstreetmap.org/way/475633218)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D041 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0709003, 30.6340733；节点 4693610170。
- 道路类型：highway.service；权限分类：public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-475633298, 475633298；原图相邻节点数：3。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 475633298](https://www.openstreetmap.org/way/475633298)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D042 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0703572, 30.6340601；节点 4693610171。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633298, 475633298；原图相邻节点数：1。
- 来源：[OSM 475633298](https://www.openstreetmap.org/way/475633298)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D043 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0678179, 30.6340006；节点 4693610148。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633288#3, 475633288#3；原图相邻节点数：1。
- 来源：[OSM 475633288](https://www.openstreetmap.org/way/475633288)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D044 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0709077, 30.6338147；节点 4693610168。
- 道路类型：highway.service；权限分类：public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-475633297, 475633297；原图相邻节点数：3。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 475633297](https://www.openstreetmap.org/way/475633297)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D045 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0702621, 30.6337975；节点 4693610169。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633297, 475633297；原图相邻节点数：1。
- 来源：[OSM 475633297](https://www.openstreetmap.org/way/475633297)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D046 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0692412, 30.6337544；节点 4693610160。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633294#1, 475633294#1；原图相邻节点数：1。
- 来源：[OSM 475633294](https://www.openstreetmap.org/way/475633294)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D047 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0679451, 30.6337372；节点 4693610158。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633294#0, 475633294#0；原图相邻节点数：1。
- 来源：[OSM 475633294](https://www.openstreetmap.org/way/475633294)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D048 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0709158, 30.6335370；节点 11073271156。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-475633216#4, 475633216#4；原图相邻节点数：4。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 475633216](https://www.openstreetmap.org/way/475633216)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D049 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0663287, 30.6333539；节点 5162173344。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633299#1, 475633299#1；原图相邻节点数：1。
- 来源：[OSM 475633299](https://www.openstreetmap.org/way/475633299)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D050 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0490138, 30.6327338；节点 4972899578。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-507865708, 507865708；原图相邻节点数：3。
- 来源：[OSM 345684193](https://www.openstreetmap.org/way/345684193)；[OSM 507865708](https://www.openstreetmap.org/way/507865708)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D051 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0589742, 30.6325237；节点 13991721008。
- 道路类型：highway.service；权限分类：explicit_private_access；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1535755975#0, 1535755975#0；原图相邻节点数：1。
- 来源：[OSM 1535755975](https://www.openstreetmap.org/way/1535755975)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D052 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0675906, 30.6323588；节点 4693609824。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633219#1, 475633219#1；原图相邻节点数：1。
- 来源：[OSM 475633219](https://www.openstreetmap.org/way/475633219)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D053 · 成科西路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0709596, 30.6320212；节点 1159173784。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-528151332#2, 528151332#2；原图相邻节点数：4。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 528151331](https://www.openstreetmap.org/way/528151331)；[OSM 528151332](https://www.openstreetmap.org/way/528151332)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D054 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0677981, 30.6314234；节点 4693646378。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475635974, 475635974；原图相邻节点数：1。
- 来源：[OSM 475635974](https://www.openstreetmap.org/way/475635974)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D055 · 芳草西一街 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0482285, 30.6311598；节点 3523298659。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-345684191#1, 345684191#1；原图相邻节点数：3。
- 来源：[OSM 345684191](https://www.openstreetmap.org/way/345684191)；[OSM 345684192](https://www.openstreetmap.org/way/345684192)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D056 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0633047, 30.6309561；节点 5478294732。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688455#1, 569688455#1；原图相邻节点数：1。
- 来源：[OSM 569688455](https://www.openstreetmap.org/way/569688455)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D057 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0557298, 30.6308697；节点 13330278257。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1352895555#1, 1352895555#1；原图相邻节点数：1。
- 来源：[OSM 1352895555](https://www.openstreetmap.org/way/1352895555)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D058 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0625322, 30.6303284；节点 5478294729。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688454, 569688454；原图相邻节点数：1。
- 来源：[OSM 569688454](https://www.openstreetmap.org/way/569688454)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D059 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0568620, 30.6302170；节点 11799932040。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651057, 1270651057；原图相邻节点数：1。
- 来源：[OSM 1270651057](https://www.openstreetmap.org/way/1270651057)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D060 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0620333, 30.6302360；节点 5478294744。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688458#0, 569688458#0；原图相邻节点数：1。
- 来源：[OSM 569688458](https://www.openstreetmap.org/way/569688458)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D061 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0561602, 30.6301358；节点 11799932038。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651056, 1270651056；原图相邻节点数：1。
- 来源：[OSM 1270651056](https://www.openstreetmap.org/way/1270651056)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D062 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0710104, 30.6301996；节点 3761409984。
- 道路类型：highway.unclassified；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-372587455, 372587455；原图相邻节点数：3。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 372587455](https://www.openstreetmap.org/way/372587455)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D063 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0561442, 30.6298702；节点 11799932036。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651055, 1270651055；原图相邻节点数：1。
- 来源：[OSM 1270651055](https://www.openstreetmap.org/way/1270651055)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D064 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0593059, 30.6298706；节点 12518091671。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1352895544#0, 1352895544#0；原图相邻节点数：1。
- 来源：[OSM 1352895544](https://www.openstreetmap.org/way/1352895544)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D065 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0622050, 30.6298714；节点 5478294738。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688458#1, 569688458#1；原图相邻节点数：1。
- 来源：[OSM 569688458](https://www.openstreetmap.org/way/569688458)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D066 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0550907, 30.6294684；节点 12501198709。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1351251334, 1351251334；原图相邻节点数：1。
- 来源：[OSM 1351251334](https://www.openstreetmap.org/way/1351251334)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D067 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0639035, 30.6294540；节点 9863913518。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1075530375；原图相邻节点数：1。
- 来源：[OSM 1075530375](https://www.openstreetmap.org/way/1075530375)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D068 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0636795, 30.6293986；节点 9863913520。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：1075530376；原图相邻节点数：1。
- 来源：[OSM 1075530376](https://www.openstreetmap.org/way/1075530376)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D069 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0686324, 30.6294274；节点 4693609966。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-475633246, 475633246；原图相邻节点数：1。
- 来源：[OSM 475633246](https://www.openstreetmap.org/way/475633246)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D070 · 玉林五巷 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0575386, 30.6291625；节点 13671760148。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1491845448, 1491845448；原图相邻节点数：1。
- 来源：[OSM 1491845448](https://www.openstreetmap.org/way/1491845448)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D071 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0710436, 30.6289435；节点 4693609981。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-475633249, 475633249；原图相邻节点数：3。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 475633249](https://www.openstreetmap.org/way/475633249)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D072 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0626341, 30.6287958；节点 5478294734。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688456, 569688456；原图相邻节点数：1。
- 来源：[OSM 569688456](https://www.openstreetmap.org/way/569688456)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D073 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0549634, 30.6286500；节点 12501198707。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1351251333, 1351251333；原图相邻节点数：1。
- 来源：[OSM 1351251333](https://www.openstreetmap.org/way/1351251333)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D074 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0615581, 30.6284988；节点 11799932062。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651065#1, 1270651065#1；原图相邻节点数：1。
- 来源：[OSM 1270651065](https://www.openstreetmap.org/way/1270651065)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D075 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0613937, 30.6281619；节点 11799932059。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651064#1, 1270651064#1；原图相邻节点数：1。
- 来源：[OSM 1270651064](https://www.openstreetmap.org/way/1270651064)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D076 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0551540, 30.6281082；节点 11799930366。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651036, 1270651036；原图相邻节点数：1。
- 来源：[OSM 1270651036](https://www.openstreetmap.org/way/1270651036)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D077 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0557773, 30.6280577；节点 12501198710。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651026#0, 1270651026#0；原图相邻节点数：1。
- 来源：[OSM 1270651026](https://www.openstreetmap.org/way/1270651026)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D078 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0710645, 30.6281489；节点 4693609979。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-475633248, 475633248；原图相邻节点数：3。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 475633248](https://www.openstreetmap.org/way/475633248)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D079 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0661931, 30.6281061；节点 7743230959。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-829607564, 829607564；原图相邻节点数：1。
- 来源：[OSM 829607564](https://www.openstreetmap.org/way/829607564)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D080 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0615234, 30.6279985；节点 11799932056。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651063#1, 1270651063#1；原图相邻节点数：1。
- 来源：[OSM 1270651063](https://www.openstreetmap.org/way/1270651063)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D081 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0617040, 30.6278251；节点 11799932053。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651062#1, 1270651062#1；原图相邻节点数：1。
- 来源：[OSM 1270651062](https://www.openstreetmap.org/way/1270651062)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D082 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0614562, 30.6276497；节点 11799932050。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1270651061#1, 1270651061#1；原图相邻节点数：1。
- 来源：[OSM 1270651061](https://www.openstreetmap.org/way/1270651061)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D083 · 锦绣路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0710702, 30.6275768；节点 1159173779。
- 道路类型：highway.secondary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-337493840#0, 337493840#0；原图相邻节点数：3。
- 来源：[OSM 100288869](https://www.openstreetmap.org/way/100288869)；[OSM 337493840](https://www.openstreetmap.org/way/337493840)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D084 · 二环高架路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0454218, 30.6271897；节点 8329831281。
- 道路类型：highway.trunk；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：441574379；原图相邻节点数：2。
- 来源：[OSM 441574379](https://www.openstreetmap.org/way/441574379)；[OSM 570975763](https://www.openstreetmap.org/way/570975763)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D085 · 二环高架路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0453946, 30.6267829；节点 8329831280。
- 道路类型：highway.trunk；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：824625838；原图相邻节点数：2。
- 来源：[OSM 824625838](https://www.openstreetmap.org/way/824625838)；[OSM 896111036](https://www.openstreetmap.org/way/896111036)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D086 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0657990, 30.6268150；节点 7743076419。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-829589783#1, 829589783#1；原图相邻节点数：1。
- 来源：[OSM 829589783](https://www.openstreetmap.org/way/829589783)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D087 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0663306, 30.6267355；节点 7743076363。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-829589773#0, 829589773#0；原图相邻节点数：1。
- 来源：[OSM 829589773](https://www.openstreetmap.org/way/829589773)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D088 · 玉寿巷 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0592672, 30.6264031；节点 11925713590。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1285599800, 1285599800；原图相邻节点数：1。
- 来源：[OSM 1285599800](https://www.openstreetmap.org/way/1285599800)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D089 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0666509, 30.6263946；节点 7743240186。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：829607568；原图相邻节点数：1。
- 来源：[OSM 829607568](https://www.openstreetmap.org/way/829607568)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D090 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0614683, 30.6263302；节点 11925713500。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1285599775#1, 1285599775#1；原图相邻节点数：1。
- 来源：[OSM 1285599775](https://www.openstreetmap.org/way/1285599775)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D091 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0656740, 30.6262976；节点 7743061381。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-829589752#2, 829589752#2；原图相邻节点数：1。
- 来源：[OSM 829589752](https://www.openstreetmap.org/way/829589752)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D092 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0663535, 30.6262562；节点 7743076364。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-829589773#2, 829589773#2；原图相邻节点数：1。
- 来源：[OSM 829589773](https://www.openstreetmap.org/way/829589773)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D093 · 二环路南三段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0473225, 30.6261084；节点 4548211609。
- 道路类型：highway.secondary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：441579299#28；原图相邻节点数：6。
- 来源：[OSM 126463203](https://www.openstreetmap.org/way/126463203)；[OSM 1433226082](https://www.openstreetmap.org/way/1433226082)；[OSM 441579299](https://www.openstreetmap.org/way/441579299)；[OSM 571017082](https://www.openstreetmap.org/way/571017082)；[OSM 611514007](https://www.openstreetmap.org/way/611514007)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D094 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0624500, 30.6260917；节点 11925713504。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1285599777, 1285599777；原图相邻节点数：1。
- 来源：[OSM 1285599777](https://www.openstreetmap.org/way/1285599777)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D095 · 二环路南三段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0474454, 30.6258538；节点 5789411072。
- 道路类型：highway.secondary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：458891623#2；原图相邻节点数：4。
- 来源：[OSM 458891623](https://www.openstreetmap.org/way/458891623)；[OSM 611514007](https://www.openstreetmap.org/way/611514007)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D096 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0616293, 30.6259209；节点 11925713502。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1285599776, 1285599776；原图相邻节点数：1。
- 来源：[OSM 1285599776](https://www.openstreetmap.org/way/1285599776)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D097 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0686761, 30.6259161；节点 6262777755。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-668773494, 668773494；原图相邻节点数：1。
- 来源：[OSM 668773494](https://www.openstreetmap.org/way/668773494)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D098 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0684125, 30.6258027；节点 6262777872。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-668773505, 668773505；原图相邻节点数：1。
- 来源：[OSM 668773505](https://www.openstreetmap.org/way/668773505)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D099 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0668696, 30.6254164；节点 6262777746。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-668773493#2, 668773493#2；原图相邻节点数：1。
- 来源：[OSM 668773493](https://www.openstreetmap.org/way/668773493)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D100 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0528676, 30.6248507；节点 10811766225。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1162533786, 1162533786；原图相邻节点数：1。
- 来源：[OSM 1162533786](https://www.openstreetmap.org/way/1162533786)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D101 · 棕南西街 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0715928, 30.6246772；节点 1159175447。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-100288857#0, 100288857#0；原图相邻节点数：3。
- 来源：[OSM 100288857](https://www.openstreetmap.org/way/100288857)；[OSM 100288903](https://www.openstreetmap.org/way/100288903)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D102 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0638600, 30.6245631；节点 11925713560。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1285599791, 1285599791；原图相邻节点数：1。
- 来源：[OSM 1285599791](https://www.openstreetmap.org/way/1285599791)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D103 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0632270, 30.6245584；节点 11925713562。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1285599792, 1285599792；原图相邻节点数：1。
- 来源：[OSM 1285599792](https://www.openstreetmap.org/way/1285599792)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D104 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0566642, 30.6243589；节点 13173736923。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1433368767, 1433368767；原图相邻节点数：1。
- 来源：[OSM 1433368767](https://www.openstreetmap.org/way/1433368767)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D105 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0624280, 30.6240873；节点 5478294764。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688467#1, 569688467#1；原图相邻节点数：1。
- 来源：[OSM 569688467](https://www.openstreetmap.org/way/569688467)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D106 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0565899, 30.6240437；节点 13173736920。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1433368766#2, 1433368766#2；原图相邻节点数：1。
- 来源：[OSM 1433368766](https://www.openstreetmap.org/way/1433368766)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D107 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0555140, 30.6240300；节点 13173736919。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1433368766#0, 1433368766#0；原图相邻节点数：1。
- 来源：[OSM 1433368766](https://www.openstreetmap.org/way/1433368766)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D108 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0521842, 30.6238797；节点 3523314179。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：345685009#1；原图相邻节点数：1。
- 来源：[OSM 345685009](https://www.openstreetmap.org/way/345685009)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D109 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0495915, 30.6237876；节点 4972899565。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-507865705, 507865705；原图相邻节点数：1。
- 来源：[OSM 507865705](https://www.openstreetmap.org/way/507865705)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D110 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0685674, 30.6237649；节点 6262777620。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-668773474, 668773474；原图相邻节点数：1。
- 来源：[OSM 668773474](https://www.openstreetmap.org/way/668773474)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D111 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0518409, 30.6235780；节点 8329831287。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：896111038#0；原图相邻节点数：1。
- 来源：[OSM 896111038](https://www.openstreetmap.org/way/896111038)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D112 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0674249, 30.6236854；节点 9523120706。
- 道路类型：highway.path；权限分类：foot_cycle_path；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-1033678581, 1033678581；原图相邻节点数：1。
- 来源：[OSM 1033678581](https://www.openstreetmap.org/way/1033678581)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D113 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0529057, 30.6235450；节点 3523314181。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：345685009#0；原图相邻节点数：1。
- 来源：[OSM 345685009](https://www.openstreetmap.org/way/345685009)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D114 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0689061, 30.6235924；节点 6262777611。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-668773472#0, 668773472#0；原图相邻节点数：1。
- 来源：[OSM 668773472](https://www.openstreetmap.org/way/668773472)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D115 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0526080, 30.6232196；节点 3523314176。
- 道路类型：highway.footway；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：345685010#0；原图相邻节点数：1。
- 来源：[OSM 345685010](https://www.openstreetmap.org/way/345685010)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D116 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0657785, 30.6232842；节点 6258805266。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-668355786, 668355786；原图相邻节点数：1。
- 来源：[OSM 668355786](https://www.openstreetmap.org/way/668355786)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D117 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0699313, 30.6231803；节点 6262777671。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773481；原图相邻节点数：1。
- 来源：[OSM 668773481](https://www.openstreetmap.org/way/668773481)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D118 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0700601, 30.6231807；节点 6262777674。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773482；原图相邻节点数：1。
- 来源：[OSM 668773482](https://www.openstreetmap.org/way/668773482)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D119 · 二环路南三段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0721344, 30.6229405；节点 4548142591。
- 道路类型：highway.secondary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：441579299#8；原图相邻节点数：3。
- 来源：[OSM 100288855](https://www.openstreetmap.org/way/100288855)；[OSM 441579299](https://www.openstreetmap.org/way/441579299)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D120 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0680809, 30.6229031；节点 6262777590。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773465#0；原图相邻节点数：1。
- 来源：[OSM 668773465](https://www.openstreetmap.org/way/668773465)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D121 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0677067, 30.6228962；节点 6262777591。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773465#1；原图相邻节点数：1。
- 来源：[OSM 668773465](https://www.openstreetmap.org/way/668773465)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D122 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0682052, 30.6226600；节点 6262777601。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773469#1；原图相邻节点数：1。
- 来源：[OSM 668773469](https://www.openstreetmap.org/way/668773469)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D123 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0675786, 30.6226466；节点 6262777599。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773469#0；原图相邻节点数：1。
- 来源：[OSM 668773469](https://www.openstreetmap.org/way/668773469)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D124 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0682056, 30.6226457；节点 6262777598。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773468#1；原图相邻节点数：1。
- 来源：[OSM 668773468](https://www.openstreetmap.org/way/668773468)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D125 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0675800, 30.6226296；节点 6262777596。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773468#0；原图相邻节点数：1。
- 来源：[OSM 668773468](https://www.openstreetmap.org/way/668773468)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D126 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0680701, 30.6223584；节点 6262777593。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773466#1；原图相邻节点数：1。
- 来源：[OSM 668773466](https://www.openstreetmap.org/way/668773466)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D127 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0677389, 30.6223549；节点 6262777592。
- 道路类型：highway.steps；权限分类：foot_cycle_path；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：668773466#0；原图相邻节点数：1。
- 来源：[OSM 668773466](https://www.openstreetmap.org/way/668773466)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D128 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0659788, 30.6216180；节点 6252596024。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-667773070#2, 667773070#2；原图相邻节点数：1。
- 来源：[OSM 667773070](https://www.openstreetmap.org/way/667773070)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D129 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0649998, 30.6216065；节点 6252596023。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-667773070#0, 667773070#0；原图相邻节点数：1。
- 来源：[OSM 667773070](https://www.openstreetmap.org/way/667773070)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D130 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0566421, 30.6215023；节点 5478294815。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688482#3, 569688482#3；原图相邻节点数：1。
- 来源：[OSM 569688482](https://www.openstreetmap.org/way/569688482)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D131 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0489497, 30.6209499；节点 4972899561。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-507865704, 507865704；原图相邻节点数：1。
- 来源：[OSM 507865704](https://www.openstreetmap.org/way/507865704)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D132 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0616417, 30.6209599；节点 5478294867。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688493, 569688493；原图相邻节点数：1。
- 来源：[OSM 569688493](https://www.openstreetmap.org/way/569688493)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D133 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0557408, 30.6208052；节点 5478294813。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688481, 569688481；原图相邻节点数：1。
- 来源：[OSM 569688481](https://www.openstreetmap.org/way/569688481)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D134 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0534318, 30.6205503；节点 4972899570。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-507865706#1, 507865706#1；原图相邻节点数：1。
- 来源：[OSM 507865706](https://www.openstreetmap.org/way/507865706)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D135 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0634984, 30.6203895；节点 6252596083。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-667773084, 667773084；原图相邻节点数：1。
- 来源：[OSM 667773084](https://www.openstreetmap.org/way/667773084)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D136 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0661424, 30.6203364；节点 6252595990。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-667773058, 667773058；原图相邻节点数：1。
- 来源：[OSM 667773058](https://www.openstreetmap.org/way/667773058)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D137 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0690124, 30.6203158；节点 480012052。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-39962835#1, 39962835#1；原图相邻节点数：1。
- 来源：[OSM 39962835](https://www.openstreetmap.org/way/39962835)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D138 · 紫荆北路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0494920, 30.6196592；节点 2727022877。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：266163676#0；原图相邻节点数：3。
- 来源：[OSM 266163676](https://www.openstreetmap.org/way/266163676)；[OSM 267232753](https://www.openstreetmap.org/way/267232753)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D139 · 紫竹西路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0493543, 30.6194413；节点 3266784227。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：267232475#0；原图相邻节点数：3。
- 来源：[OSM 266163676](https://www.openstreetmap.org/way/266163676)；[OSM 267232475](https://www.openstreetmap.org/way/267232475)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D140 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0654517, 30.6189584；节点 6252594535。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-667773049, 667773049；原图相邻节点数：1。
- 来源：[OSM 667773049](https://www.openstreetmap.org/way/667773049)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D141 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0595952, 30.6188894；节点 5478294840。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688487, 569688487；原图相邻节点数：1。
- 来源：[OSM 569688487](https://www.openstreetmap.org/way/569688487)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D142 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0588790, 30.6188571；节点 5478294839。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-569688486#0, 569688486#0；原图相邻节点数：1。
- 来源：[OSM 569688486](https://www.openstreetmap.org/way/569688486)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D143 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0683016, 30.6183859；节点 6256896577。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-668156790, 668156790；原图相邻节点数：1。
- 来源：[OSM 668156790](https://www.openstreetmap.org/way/668156790)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D144 · 未命名道路 · source_terminal_unverified
- 坐标（WGS84经度、纬度）：104.0692940, 30.6181320；节点 6256896570。
- 道路类型：highway.service；权限分类：parking_or_driveway；SUMO允许小客车：False。
- 原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。
- SUMO边：-668156788, 668156788；原图相邻节点数：1。
- 来源：[OSM 668156788](https://www.openstreetmap.org/way/668156788)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D145 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0683870, 30.6178527；节点 6256896578。
- 道路类型：highway.service；权限分类：parking_or_driveway / service_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-668156779#5, 668156779#5；原图相邻节点数：3。
- 来源：[OSM 668156779](https://www.openstreetmap.org/way/668156779)；[OSM 668156791](https://www.openstreetmap.org/way/668156791)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D146 · 新希望路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0694556, 30.6177512；节点 6256896543。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-37132262#8, 37132262#8；原图相邻节点数：3。
- 来源：[OSM 37132262](https://www.openstreetmap.org/way/37132262)；[OSM 668156781](https://www.openstreetmap.org/way/668156781)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D147 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0693116, 30.6177478；节点 6256896560。
- 道路类型：highway.service；权限分类：parking_or_driveway / service_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-668156787, 668156787；原图相邻节点数：3。
- 来源：[OSM 668156781](https://www.openstreetmap.org/way/668156781)；[OSM 668156787](https://www.openstreetmap.org/way/668156787)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D148 · 紫竹中街 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0521665, 30.6176195；节点 432452888。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：267232478；原图相邻节点数：3。
- 来源：[OSM 1363075939](https://www.openstreetmap.org/way/1363075939)；[OSM 266164016](https://www.openstreetmap.org/way/266164016)；[OSM 267232478](https://www.openstreetmap.org/way/267232478)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D149 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0666118, 30.6176567；节点 6256896544。
- 道路类型：highway.service；权限分类：service_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-668156782#0, 668156782#0；原图相邻节点数：3。
- 来源：[OSM 668156779](https://www.openstreetmap.org/way/668156779)；[OSM 668156782](https://www.openstreetmap.org/way/668156782)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D150 · 紫竹中街 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0520443, 30.6174952；节点 432452886。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：267232477；原图相邻节点数：3。
- 来源：[OSM 1363075939](https://www.openstreetmap.org/way/1363075939)；[OSM 267232477](https://www.openstreetmap.org/way/267232477)；[OSM 37132252](https://www.openstreetmap.org/way/37132252)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D151 · 人民南路四段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0648373, 30.6175326；节点 6257575017。
- 道路类型：highway.tertiary；权限分类：public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：1448610360#9；原图相邻节点数：3。
- 来源：[OSM 1448610360](https://www.openstreetmap.org/way/1448610360)；[OSM 668220101](https://www.openstreetmap.org/way/668220101)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D152 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0661132, 30.6175319；节点 6256896534。
- 道路类型：highway.unclassified；权限分类：public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-265385902#0, 265385902#0；原图相邻节点数：3。
- 来源：[OSM 265385902](https://www.openstreetmap.org/way/265385902)；[OSM 668156778](https://www.openstreetmap.org/way/668156778)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D153 · 人民南路四段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0644830, 30.6173918；节点 4701464385。
- 道路类型：highway.tertiary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：1442743827#3；原图相邻节点数：3。
- 来源：[OSM 1442743827](https://www.openstreetmap.org/way/1442743827)；[OSM 476647760](https://www.openstreetmap.org/way/476647760)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D154 · 未命名道路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0550044, 30.6171519；节点 13985142888。
- 道路类型：highway.cycleway；权限分类：foot_cycle_path / public_road_class_access_unverified；SUMO允许小客车：False。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：1534837204#6；原图相邻节点数：4。
- 来源：[OSM 1534837204](https://www.openstreetmap.org/way/1534837204)；[OSM 266164016](https://www.openstreetmap.org/way/266164016)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D155 · 新光路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0550456, 30.6171451；节点 2717452481。
- 道路类型：highway.secondary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-267226974#2, 267226974#2；原图相邻节点数：3。
- 来源：[OSM 266164016](https://www.openstreetmap.org/way/266164016)；[OSM 267226974](https://www.openstreetmap.org/way/267226974)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D156 · 人民南路四段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0646336, 30.6164206；节点 7618649237。
- 道路类型：highway.primary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：136004881#4；原图相邻节点数：3。
- 来源：[OSM 136004891](https://www.openstreetmap.org/way/136004891)；[OSM 1442743826](https://www.openstreetmap.org/way/1442743826)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D157 · 桐梓林东路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0602255, 30.6163733；节点 432452898。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-276196015#0, 276196015#0；原图相邻节点数：4。
- 来源：[OSM 276196015](https://www.openstreetmap.org/way/276196015)；[OSM 37132257](https://www.openstreetmap.org/way/37132257)；[OSM 37132259](https://www.openstreetmap.org/way/37132259)；[OSM 815758060](https://www.openstreetmap.org/way/815758060)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D158 · 桐梓林路 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0578544, 30.6163087；节点 432452894。
- 道路类型：highway.residential；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：-37132255#3, 37132255#3；原图相邻节点数：4。
- 来源：[OSM 37132255](https://www.openstreetmap.org/way/37132255)；[OSM 37132257](https://www.openstreetmap.org/way/37132257)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### D159 · 人民南路四段 · boundary_clip
- 坐标（WGS84经度、纬度）：104.0647909, 30.6151599；节点 1493146458。
- 道路类型：highway.primary；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。
- SUMO边：136069028#0；原图相邻节点数：2。
- 来源：[OSM 136064112](https://www.openstreetmap.org/way/136064112)；[OSM 136069028](https://www.openstreetmap.org/way/136069028)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### M01 · 未命名道路 · passenger_mode_boundary
- 坐标（WGS84经度、纬度）：104.0635586, 30.6341028；节点 13766510045。
- 道路类型：highway.service / highway.unclassified；权限分类：public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：True。
- 小客车只有一条接入支路，但其他模式道路仍接续；不是全道路断头。排除小客车可能是SUMO默认权限，不能等同现场禁行。
- SUMO边：-1504427097#4, -1504766983, 1504427097#4, 1504766983；原图相邻节点数：2。
- 来源：[OSM 1504427097](https://www.openstreetmap.org/way/1504427097)；[OSM 1504766983](https://www.openstreetmap.org/way/1504766983)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### M02 · 火烧堰巷 · passenger_mode_boundary
- 坐标（WGS84经度、纬度）：104.0522612, 30.6283677；节点 11799930353。
- 道路类型：highway.pedestrian / highway.residential；权限分类：foot_cycle_path / public_road_class_access_unverified；SUMO允许小客车：True。
- 小客车只有一条接入支路，但其他模式道路仍接续；不是全道路断头。排除小客车可能是SUMO默认权限，不能等同现场禁行。
- SUMO边：-1270651031, 1270651031, 265833231#0, 265833231#1；原图相邻节点数：3。
- 来源：[OSM 1270651031](https://www.openstreetmap.org/way/1270651031)；[OSM 265833231](https://www.openstreetmap.org/way/265833231)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### M03 · 白云街 · passenger_mode_boundary
- 坐标（WGS84经度、纬度）：104.0530858, 30.6282773；节点 13888813828。
- 道路类型：highway.footway / highway.residential / highway.service；权限分类：foot_cycle_path / public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：True。
- 小客车只有一条接入支路，但其他模式道路仍接续；不是全道路断头。排除小客车可能是SUMO默认权限，不能等同现场禁行。
- SUMO边：-1523624124#0, -1523624124#1, -345684188#0, 1523624124#0, 1523624124#1, 1523624125, 345684188#0；原图相邻节点数：4。
- 来源：[OSM 1523624124](https://www.openstreetmap.org/way/1523624124)；[OSM 1523624125](https://www.openstreetmap.org/way/1523624125)；[OSM 345684188](https://www.openstreetmap.org/way/345684188)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### M04 · 蓓蕾中巷 · passenger_mode_boundary
- 坐标（WGS84经度、纬度）：104.0544456, 30.6280419；节点 13888813829。
- 道路类型：highway.footway / highway.residential / highway.service；权限分类：foot_cycle_path / public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：True。
- 小客车只有一条接入支路，但其他模式道路仍接续；不是全道路断头。排除小客车可能是SUMO默认权限，不能等同现场禁行。
- SUMO边：-1270651035#1, -1523624124#1, 1270651035#1, 1523624124#1, 1523624126；原图相邻节点数：3。
- 来源：[OSM 1270651035](https://www.openstreetmap.org/way/1270651035)；[OSM 1523624124](https://www.openstreetmap.org/way/1523624124)；[OSM 1523624126](https://www.openstreetmap.org/way/1523624126)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### M05 · 航空路 · passenger_mode_boundary
- 坐标（WGS84经度、纬度）：104.0714431, 30.6187925；节点 1159175700。
- 道路类型：highway.residential / highway.service；权限分类：public_road_class_access_unverified / service_access_unverified；SUMO允许小客车：True。
- 小客车只有一条接入支路，但其他模式道路仍接续；不是全道路断头。排除小客车可能是SUMO默认权限，不能等同现场禁行。
- SUMO边：-100288911, -37132261#8, 100288911, 37132261#8；原图相邻节点数：4。
- 来源：[OSM 100288911](https://www.openstreetmap.org/way/100288911)；[OSM 37132261](https://www.openstreetmap.org/way/37132261)；[OSM 476664224](https://www.openstreetmap.org/way/476664224)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### B01 · 人民南路三段 · directed_boundary_clip
- 坐标（WGS84经度、纬度）：104.0642794, 30.6361885；节点 11699319252。
- 道路类型：highway.tertiary / highway.tertiary_link；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 多支单向道路在模型外部边界汇入或发出；不是单支几何尽端。原图有续路，未把该点解释为真实断头路。
- SUMO边：136005112#0, 564190177；原图相邻节点数：3。
- 来源：[OSM 136005112](https://www.openstreetmap.org/way/136005112)；[OSM 564190177](https://www.openstreetmap.org/way/564190177)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### B02 · 二环高架路 / 人南立交 · directed_boundary_clip
- 坐标（WGS84经度、纬度）：104.0727498, 30.6226718；节点 4548141015。
- 道路类型：highway.trunk / highway.trunk_link；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 多支单向道路在模型外部边界汇入或发出；不是单支几何尽端。原图有续路，未把该点解释为真实断头路。
- SUMO边：221951480, 458883922#3；原图相邻节点数：3。
- 来源：[OSM 221951480](https://www.openstreetmap.org/way/221951480)；[OSM 458883925](https://www.openstreetmap.org/way/458883925)；[OSM 871604767](https://www.openstreetmap.org/way/871604767)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### B03 · 二环高架路 / 人南立交 · directed_boundary_clip
- 坐标（WGS84经度、纬度）：104.0728431, 30.6228560；节点 4548141029。
- 道路类型：highway.trunk / highway.trunk_link；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 多支单向道路在模型外部边界汇入或发出；不是单支几何尽端。原图有续路，未把该点解释为真实断头路。
- SUMO边：441574380, 458883907；原图相邻节点数：3。
- 来源：[OSM 441574380](https://www.openstreetmap.org/way/441574380)；[OSM 458883907](https://www.openstreetmap.org/way/458883907)；[OSM 458883912](https://www.openstreetmap.org/way/458883912)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### B04 · 二环路南三段 · directed_boundary_clip
- 坐标（WGS84经度、纬度）：104.0707044, 30.6225909；节点 2333187912。
- 道路类型：highway.secondary / highway.secondary_link；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 多支单向道路在模型外部边界汇入或发出；不是单支几何尽端。原图有续路，未把该点解释为真实断头路。
- SUMO边：458891623#20, 896111031#1；原图相邻节点数：3。
- 来源：[OSM 458891623](https://www.openstreetmap.org/way/458891623)；[OSM 896111031](https://www.openstreetmap.org/way/896111031)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。

### B05 · 人民南路三段 · directed_boundary_clip
- 坐标（WGS84经度、纬度）：104.0639306, 30.6362659；节点 5436607846。
- 道路类型：highway.tertiary / highway.tertiary_link；权限分类：public_road_class_access_unverified；SUMO允许小客车：True。
- 多支单向道路在模型外部边界汇入或发出；不是单支几何尽端。原图有续路，未把该点解释为真实断头路。
- SUMO边：459143617#4, 564190179；原图相邻节点数：3。
- 来源：[OSM 459143617](https://www.openstreetmap.org/way/459143617)；[OSM 564190179](https://www.openstreetmap.org/way/564190179)
- 现场核实状态：未现场核实；没有把近邻道路擅自接通。
