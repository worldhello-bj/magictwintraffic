#!/usr/bin/env python3
"""Package exact recorded states, deduplicate networks, optionally reduce display sample rate.
Physics and evaluation are never rerun or altered. Original high-rate run stays in runs/.
"""
import argparse,json,gzip,struct,hashlib,shutil,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')))
def package(source,destination,sample_seconds=None):
 manifest=json.loads((source/'manifest.json').read_text());network=json.loads((source/'network.json').read_text());run_id=manifest['run_id'];target=destination/'runs'/run_id;target.mkdir(parents=True,exist_ok=True)
 baseline=json.loads((destination/'network.json').read_text())
 if network['network_hash']==baseline['network_hash']:manifest['network']='../../network.json'
 else:
  asset=destination/'networks'/(network['network_hash']+'.json');write(asset,network);manifest['network']='../../networks/'+asset.name
 obsolete=target/'network.json'
 if obsolete.exists():obsolete.unlink()
 for filename in ['metrics.json','timeseries.json','signals.json','events.json','audit.json','signal_topology.json','queue_hotspots.json','stock_timeseries.json','internal_zones.json','od_matrix.json']:
  if (source/filename).exists():write(target/filename,json.loads((source/filename).read_text()))
 if (source/'od_matrix.csv').exists():shutil.copyfile(source/'od_matrix.csv',target/'od_matrix.csv')
 if (target/'trajectory').exists():shutil.rmtree(target/'trajectory')
 (target/'trajectory').mkdir()
 chunks=[]
 for chunk in manifest['chunks']:
  raw_path=source/chunk['file'];compressed=raw_path.read_bytes()
  if hashlib.sha256(compressed).hexdigest()!=chunk['sha256']:raise ValueError('Source chunk checksum mismatch')
  raw=gzip.decompress(compressed) if chunk.get('compression')=='gzip' else compressed
  if sample_seconds:
   raw=b''.join(raw[offset:offset+32] for offset in range(0,len(raw),32) if abs(struct.unpack_from('<f',raw,offset)[0]/sample_seconds-round(struct.unpack_from('<f',raw,offset)[0]/sample_seconds))<1e-6)
  packed=gzip.compress(raw,compresslevel=9,mtime=0);filename='trajectory/'+Path(chunk['file']).name.removesuffix('.gz')+'.gz';(target/filename).write_bytes(packed)
  updated={**chunk,'file':filename,'compression':'gzip','sha256':hashlib.sha256(packed).hexdigest(),'records':len(raw)//32,'record_count':len(raw)//32,'bytes':len(packed),'uncompressed_bytes':len(raw)}
  if sample_seconds:
   updated['start']=updated['start_time']=math.ceil(chunk['start_time']/sample_seconds)*sample_seconds
   updated['end']=updated['end_time']=math.floor(chunk['end_time']/sample_seconds)*sample_seconds
  chunks.append(updated)
 manifest['chunks']=chunks;manifest['trajectory_step_seconds']=sample_seconds or manifest['step_seconds'];manifest['recording_export']=dict(source_run_id=run_id,source_physics_step_seconds=manifest['step_seconds'],display_sample_seconds=manifest['trajectory_step_seconds'],method='Exact recorded-frame subsampling; no interpolated or fabricated states; evaluator unchanged',network_deduplicated=True)
 write(target/'manifest.json',manifest)
 label=f"{manifest['policy']} · {manifest['duration_seconds']:g}s / {1/manifest['trajectory_step_seconds']:g}Hz回放"
 if manifest.get('config',{}).get('demo_scenario'):label=f"{manifest['policy']} · 合成高需求演示 / 预热{manifest['config']['warmup_seconds']:g}s / {1/manifest['trajectory_step_seconds']:g}Hz"
 return dict(run_id=run_id,label=label,policy=manifest['policy'],manifest=f'runs/{run_id}/manifest.json',metrics=f'runs/{run_id}/metrics.json',duration_seconds=manifest['duration_seconds'],trajectory_step_seconds=manifest['trajectory_step_seconds'])
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--previews',default='preview');parser.add_argument('--full',default='replay_S0_am_42_d1');args=parser.parse_args();dest=ROOT/'web/public/data';dest.mkdir(parents=True,exist_ok=True);write(dest/'network.json',json.loads((ROOT/'data/canonical/network.json').read_text()))
 runs=[]
 for policy in range(8):runs.append(package(ROOT/'runs'/f'{args.previews}_S{policy}_am_42_d1',dest))
 if args.full:runs.append(package(ROOT/'runs'/args.full,dest,sample_seconds=1.))
 write(dest/'catalog.json',dict(schema_version='1.0',runs=runs));print(json.dumps(dict(runs=len(runs),bytes=sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()))))
