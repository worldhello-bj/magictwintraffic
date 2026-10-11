import json,hashlib,pathlib,collections,sys
ROOT=pathlib.Path(__file__).resolve().parent
base=ROOT/'site-v10/story-data'
cat=json.loads((base/'catalog.json').read_text()); runs=cat['runs']; byid={r['id']:r for r in runs}; problems=[]; finals=[]
assert len(runs)==len(byid)==40
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/cat['network']['file'])==cat['network']['sha256']
expected={(period,seed,policy) for period in ['am','pm'] for seed in [42,43,44] for policy in ['baseline','stagger','walk','bus','combined','priority']}
expected|={(period,42,policy) for period in ['am','pm'] for policy in ['combined_0.5','combined_1.5']}
assert expected=={(r['period'],r['seed'],r['policy']) for r in runs}
for r in runs:
 d=json.loads((base/r['file']).read_text());ref=byid[r['reference_id']]
 assert sha(base/r['file'])==r['sha256']
 assert r['network_hash']==ref['network_hash']==d['network_hash']==cat['network']['network_hash']
 assert r['inventory_hash']==ref['inventory_hash']==d['inventory_hash']
 assert (r['period'],r['seed'],r['cohort'])==(ref['period'],ref['seed'],ref['cohort'])
 assert r['completed']==r['status_counts']['completed']
 assert sum(r['status_counts'].values())==r['cohort']==sum(r['mode_counts'].values())
 assert d['horizon_s']==7200 and len(d['windows'])==24 and len(d['series'])==240
 assert [row[0] for row in d['series']]==list(range(30,7201,30))
 assert all(len(row)==len(d['series_columns']) for row in d['series'])
 f=dict(zip(d['series_columns'],d['series'][-1]));unfinished=r['cohort']-r['completed']
 if f['completed_people']!=r['completed'] or f['due_unfinished_people']!=unfinished:problems.append({'id':r['id'],'series_final':f,'catalog_completed':r['completed'],'catalog_all_unfinished':unfinished})
 finals.append({'id':r['id'],'cohort':r['cohort'],'completed':r['completed'],'all_unfinished':unfinished,'status_counts':r['status_counts'],'restricted_mean_s':r['restricted_mean_s']})
assert not problems, f'Final catalog/series mismatches: {problems}'
files=[{'path':str(p.relative_to(ROOT/'site-v10')),'bytes':p.stat().st_size,'sha256':sha(p),'preservation':('tracked_aggregate_export' if p.relative_to(ROOT/'site-v10').parts[0]=='story-data' else 'local_only_legacy_site_asset')} for p in sorted((ROOT/'site-v10').rglob('*')) if p.is_file()]
result={'source_site_commit':'77306a89fc4d89b5f7477df62696ae0bef82547d','run_count':40,'core_run_count':36,'sensitivity_run_count':4,'catalog_and_network_hashes_verified':True,'all_run_file_hashes_verified':True,'all_reference_pair_network_inventory_and_cohort_checks_passed':True,'each_run_windows':24,'each_run_series_samples':240,'series_time_range_seconds':[30,7200],'catalog_final_status_conservation_passed':True,'series_vs_catalog_final_mismatches':problems,'safety_note':'Person event snapshot columns are preserved for provenance only and should not be displayed until corrected against unavailable original persons records. Use catalog completed and cohort-completed for final 120-minute people results. status_counts.unfinished excludes not_inserted and waiting_for_bus.','final_results':finals,'preserved_files':files}
manifest=ROOT/'site-v10-verification.json'
if '--write-manifest' in sys.argv:
 manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
else:
 saved=json.loads(manifest.read_text())
 for item in saved['preserved_files']:
  path=ROOT/'site-v10'/item['path']
  if item['preservation']=='tracked_aggregate_export' or path.exists():
   assert path.is_file() and path.stat().st_size==item['bytes'] and sha(path)==item['sha256'], item['path']
 print('Saved preservation manifest verified; unavailable local-only legacy assets are not required.')
print(json.dumps({k:v for k,v in result.items() if k not in ['preserved_files','final_results']},ensure_ascii=False,indent=2));print('Files preserved:',len(files),'bytes:',sum(x['bytes'] for x in files))
