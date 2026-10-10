"""Finite-window full-demand evaluator; no completed-trip selection hiding queues."""
import math

def percentile(values,p):
    if not values:return None
    a=sorted(values);v=(len(a)-1)*p;lo=int(v);return a[lo]+(a[min(lo+1,len(a)-1)]-a[lo])*(v-lo)

def conservation(due,waiting,inside,completed,failed=0):
    residual=due-waiting-inside-completed-failed
    if residual:raise RuntimeError(f'Demand conservation violation: residual={residual}')
    return residual

class Evaluator:
    def __init__(self,trips):
        self.trips=trips;self.by_id={t['persistent_trip_id']:t for t in trips};self.inserted={};self.arrived={};self.distance={};self.tstt=0.;self.external=0.;self.core=0.;self.periphery=0.;self.max_queue=0;self.series=[];self.audit=[];self.sorted_trips=sorted(trips,key=lambda t:t['desired_departure']);self.due_index=0;self.pending=set();self.target_due=0;self.target_pending=0;self.target_arrived=0;self.outstanding=0
    def step(self,time,dt,active,departed,arrived,positions,queues):
        # Event-based exact elapsed-time integral; O(new departures + active), not O(all trips) each step.
        self.tstt+=self.outstanding*dt
        while self.due_index<len(self.sorted_trips) and self.sorted_trips[self.due_index]['desired_departure']<=time:
            trip=self.sorted_trips[self.due_index];self.due_index+=1;self.pending.add(trip['persistent_trip_id'])
            if trip['cohort_id']=='peak':
                self.target_due+=1;self.target_pending+=1;self.outstanding+=1;self.tstt+=max(0,time-trip['desired_departure'])
        for v in departed:
            self.inserted[v]=time
            if v in self.pending:
                self.pending.remove(v)
                if self.by_id[v]['cohort_id']=='peak':self.target_pending-=1
        for v in arrived:
            self.arrived[v]=time
            if self.by_id[v]['cohort_id']=='peak':self.target_arrived+=1;self.outstanding-=1
        conservation(self.due_index,len(self.pending),len(active),len(self.arrived))
        target_active=[v for v in active if self.by_id[v]['cohort_id']=='peak']
        core=sum(1 for v in target_active if v in positions and abs(positions[v][0])<=500 and abs(positions[v][1])<=500)
        self.core+=core*dt;self.periphery+=(len(target_active)-core)*dt;self.max_queue=max(self.max_queue,queues)
        if abs(time/5-round(time/5))<1e-6:
            all_core=sum(1 for v in active if v in positions and abs(positions[v][0])<=500 and abs(positions[v][1])<=500)
            self.series.append(dict(all_cohort_inside=len(active),all_cohort_core_vehicles=all_core,all_cohort_periphery_vehicles=len(active)-all_core,all_cohort_external_waiting=len(self.pending),all_cohort_due=self.due_index,all_cohort_completed=len(self.arrived),time=time,due=self.target_due,inside=len(target_active),external_waiting=self.target_pending,completed=self.target_arrived,core_vehicles=core,periphery_vehicles=len(target_active)-core,queue_vehicles=queues,tstt_vehicle_seconds=self.tstt))
    def finish(self,time,teleports=0,collisions=0):
        summaries=[]
        for trip in self.trips:
            v=trip['persistent_trip_id'];end=self.arrived.get(v)
            summaries.append({**{k:x for k,x in trip.items() if k!='route'},'inserted_at':self.inserted.get(v),'arrived_at':end,'travel_time_seconds':None if end is None else end-trip['desired_departure'],'distance_m':self.distance.get(v),'status':'completed' if end is not None else 'inside' if v in self.inserted else 'external_waiting' if trip['desired_departure']<=time else 'future'})
        peak=[t for t in summaries if t['cohort_id']=='peak'];due=[t for t in peak if t['desired_departure']<=time];completed=[t for t in due if t['status']=='completed'];times=[t['travel_time_seconds'] for t in completed]
        metrics=dict(generated=len(peak),due=len(due),completed=len(completed),inside=sum(t['status']=='inside' for t in due),external_waiting=sum(t['status']=='external_waiting' for t in due),explicit_failure=0,completion_rate=len(completed)/len(due) if due else 0,tstt_vehicle_seconds=self.tstt,mean_travel_time_seconds=sum(times)/len(times) if times else None,p95_travel_time_seconds=percentile(times,.95),median_travel_time_seconds=percentile(times,.5),external_wait_vehicle_seconds=self.external,core_vehicle_seconds=self.core,periphery_vehicle_seconds=self.periphery,max_queue_vehicles=self.max_queue,teleports=teleports,collisions=collisions,duration_seconds=time,cohort='peak',interpretation='Finite-window cumulative time including due but uninserted target trips. Incomplete trips are right-censored; completed-only mean is secondary.',all_cohort_generated=len(summaries),all_cohort_completed=len(self.arrived),all_cohort_inserted=len(self.inserted))
        return metrics,summaries
