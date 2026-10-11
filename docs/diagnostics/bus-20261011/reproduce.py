#!/usr/bin/env python3
"""Read preserved aggregates only; write small diagnostic evidence beside this script."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'recovery/site-v10/story-data'
OUT=Path(__file__).resolve().parent
cat=json.loads((SRC/'catalog.json').read_text());runs={r['id']:r for r in cat['runs']}
net=json.loads((SRC/'network.json').read_text());edges=net['edges']
load=lambda rid:json.loads((SRC/(rid+'.json')).read_text())
for r in runs.values():
 assert hashlib.sha256((SRC/r['file']).read_bytes()).hexdigest()==r['sha256']
pairs=[]
for period in ['am','pm']:
 for seed in [42,43,44]:
  a,b=[runs[f'{period}_{seed}_{p}'] for p in ['baseline','bus']]
  assert a['cohort']==b['cohort'] and a['inventory_hash']==b['inventory_hash'] and a['network_hash']==b['network_hash']
  pairs.append(dict(period=period,seed=seed,cohort=b['cohort'],bus_people=b['mode_counts']['bus'],bus_share_pct=100*b['mode_counts']['bus']/b['cohort'],baseline_completed=a['completed'],bus_completed=b['completed'],completed_difference=b['completed']-a['completed'],restricted_mean_difference_s=b['restricted_mean_s']-a['restricted_mean_s'],stopped_vehicle_seconds_difference=b['stopped_vehicle_s']-a['stopped_vehicle_s'],stopped_vehicle_seconds_difference_pct=100*(b['stopped_vehicle_s']/a['stopped_vehicle_s']-1)))
rid='pm_43_bus';d=load(rid);r=runs[rid]
late=[row for row in d['series'] if row[0]>=6330]
assert len(late)==30 and all(row[1:]==late[0][1:] for row in late)
road_evidence=[]
for idx in [1115,1113,213,967,964,1021,281,770,166]:
 rows=[next((x for x in w if x[0]==idx),None) for w in d['windows']]
 final=rows[-1]
 start=next(j for j in range(24) if all(x==final for x in rows[j:]))
 assert final[2]==0 and final[1]==final[3]
 road_evidence.append(dict(edge_index=idx,edge_id=edges[idx]['id'],road_name=edges[idx]['name'],constant_zero_speed_window_start_min=start*5,end_min=120,mean_vehicles=final[3],mean_stopped_vehicles=final[1],observed_mean_speed_kmh=final[2]))
last=d['windows'][-1]
suspect=[dict(edge_index=x[0],edge_id=edges[x[0]]['id'],road_name=edges[x[0]]['name'],mean_stopped_vehicles=x[1],observed_mean_speed_kmh=x[2],mean_vehicles=x[3]) for x in last if x[1]==x[3] and x[2]>.36]
result=dict(scope='Read-only reanalysis of recovered historical aggregate exports; no simulation rerun or original person-record reconstruction.',source_directory=str(SRC),source_site_commit='77306a89fc4d89b5f7477df62696ae0bef82547d',catalog_sha256=hashlib.sha256((SRC/'catalog.json').read_bytes()).hexdigest(),all_40_run_hashes_verified=True,network_hash=r['network_hash'],inventory_hash=r['inventory_hash'],run_sha256=r['sha256'],historical_source_directory=r['source_directory'],historical_source_hashes_not_recovered_files=r['source_hashes'],paired_comparisons=pairs,pm43_final=dict(cohort=r['cohort'],completed=r['completed'],all_unfinished=r['cohort']-r['completed'],status_counts=r['status_counts'],mode_counts=r['mode_counts'],minimum_unfinished_car_people=r['cohort']-r['completed']-r['mode_counts']['bus']),late_exported_series=dict(start_s=6330,end_s=7200,sample_step_s=30,sample_count=len(late),constant_values=dict(zip(d['series_columns'][1:],late[0][1:])),caution='Intermediate person-event fields have known boundary sampling issues; this describes exported samples, not an independently reconstructed person event ledger.'),final_road_windows=dict(last_two_windows_identical=d['windows'][-1]==d['windows'][-2],observed_edge_count=len(last),mean_stopped_sum=sum(x[1] for x in last),zero_speed_edge_count=sum(x[2]==0 for x in last),mean_vehicles_on_zero_speed_edges=sum(x[3] for x in last if x[2]==0)),constant_zero_speed_roads=road_evidence,speed_definition_pending_verification=dict(catalog_definition=cat['definitions']['speed'],stopped_definition=cat['definitions']['stopped'],road_columns=d['road_columns'],explanation='Same-window mean stopped count equals mean vehicle count, but reported observed mean speed exceeds 0.36 km/h on 15 edges. This requires checking population/threshold/aggregation implementation; missing original source prevents declaring a confirmed calculation bug.',rows=suspect),interpretation='Persistent blockage/frozen-output anomaly is supported. Exact deadlock, bus-stop causation, or general bus policy harm is not established. Retain original evidence and qualify the graphical interpretation.',rerun_inputs_needed=['Exact 7200-second model/export source and SUMO version, or explicitly versioned new diagnostic model','Matched person inventory/assignment with OD, desired departures and mode mapping','Bus routes, vehicle schedules, stops, capacity and boarding/alighting/dwell rules','Per-person stages and per-vehicle position/speed/type/leader/conflict/signal/stop events, insertion queue and outlet throughput'],minimal_design='PM43 paired four-arm check: baseline; remove only 51 car trips; add same bus vehicles without removing cars; combined car replacement and actual bus passengers. Diagnose 15–25 min onset before single-factor mechanism changes; then repeat three seeds and AM/PM. Preserve fixed 120-minute results and extend observation without forced deletion/teleporting.')
(OUT/'diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
lines=['# 公交曲线短诊断','', '来源：已恢复的40场历史聚合导出；本次没有重新执行仿真，没有恢复逐人或逐车原始记录。40份运行文件哈希均与catalog一致。','', '## 可证实','- PM43：3829人中只有51人采用公交（1.33%）；2202人完成，1210 unfinished＋417 not_inserted，共1627人未完成。至少1576名未完成者属于汽车出行。','- 6330–7200秒共30个采样点：道路车辆1204、停等1184、导出完成数2202保持不变。人员中间事件采样有已知边界问题，不能声称重新核实了逐人吞吐事件。','- 最后两个5分钟道路窗口完全相同；83条道路停等均值合计1184，其中68条速度0。','- 这支持持续阻塞/冻结异常；不证明公交停站锁死、特定路口死锁或普遍公交政策损害。','', '## 六组配对差值（公交减原方案）','', '|时段/种子|公交人数|完成人数差|受限均时差，秒|停等车秒差，%|','|---|---:|---:|---:|---:|']
for x in pairs:lines.append(f"|{x['period'].upper()}/{x['seed']}|{x['bus_people']}|{x['completed_difference']:+d}|{x['restricted_mean_difference_s']:+.1f}|{x['stopped_vehicle_seconds_difference_pct']:+.2f}%|")
lines+=['','## 优先排查道路（连续零速且数量固定至120分钟）']
for x in road_evidence:lines.append(f"- {x['road_name']} {x['edge_id']}：从{x['constant_zero_speed_window_start_min']}分钟窗口起，平均{x['mean_vehicles']:g}辆、速度0。")
lines+=['','先查15–25分钟二环路南三段—玉林南路附近的头车、内部连接、信号、站点与出口。此顺序来自异常出现时间，不等于已证实因果链。','','## 待核','- 最末窗15条道路的平均停等数等于平均车辆数，却报告大于0.36km/h的车辆观测加权均速。例如136004880#1：平均2辆、停等2辆、30.0024km/h。这是同一窗口的口径/实现疑点；缺少原始采样、停等阈值和导出代码，暂不认定计算错误。','- 公交班次、载客率、容量、候车、上下车和停站记录均不可由现存聚合量还原。SUMO person对象数不能直接充当车内人数。','- 原GitHub代码及4200秒旧实验不是此次7200秒模型的精确源码；历史哈希也不代表原文件已恢复。','','## 重跑所需输入','- 精确7200秒模型与导出代码、SUMO版本；找不到时必须建立清楚标记的新版本实验。','- 匹配的逐人OD、计划出发、方式分配；公交路线、班次、站点、容量、上下车及停站规则。','- 逐人阶段和逐车位置/速度/头车/冲突/信号/站点事件，入口等待与出口吞吐。','- 最小四组：原方案、只减少51个汽车出行、只增加相同公交车辆、汽车替代并实际乘公交。先查PM43的15–25分钟起点，再扩展原三种子和早晚高峰。保留120分钟指标并延长观察；不通过强制移车或传送消除异常。','','## 图形处理','保留历史数据，将PM43标为待核异常案例，同时展示全部六组。撤回由此推广“增加公交导致更堵”的解读；不能改数据让公交看起来有效。','','复核：运行同目录 reproduce.py；输入只读，输出仅写入本诊断目录。完整字段与哈希见 diagnosis.json。']
(OUT/'diagnosis.md').write_text('\n'.join(lines)+'\n')
print(OUT/'diagnosis.md');print(OUT/'diagnosis.json')
