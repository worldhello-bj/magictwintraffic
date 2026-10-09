"""32-byte little-endian trajectory records with hash-bound chunk manifest."""
import struct,hashlib,gzip
from pathlib import Path
from .gis import write_json
RECORD=struct.Struct('<fIffffII')
class Recorder:
 def __init__(self,output,vehicles,lanes,chunk_seconds=20):
  self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True);self.vehicles={v:i for i,v in enumerate(vehicles)};self.lanes={v:i for i,v in enumerate(lanes)};self.chunk_seconds=chunk_seconds;self.chunks=[];self.current=None;self.buffer=bytearray();self.start=None;self.end=None
 def frame(self,time,rows):
  index=int((time-1e-7)//self.chunk_seconds)
  if self.current is not None and index!=self.current:self.flush()
  self.current=index
  if self.start is None:self.start=time
  self.end=time
  for vehicle,x,y,angle,speed,lane,flags in rows:self.buffer.extend(RECORD.pack(time,self.vehicles[vehicle],x,y,angle,speed,self.lanes.get(lane,0),flags))
 def flush(self):
  if self.current is None:return
  name=f'chunk_{self.current:05d}.bin.gz';raw=bytes(self.buffer);data=gzip.compress(raw,compresslevel=6,mtime=0);(self.output/name).write_bytes(data);self.chunks.append(dict(id=self.current,file='trajectory/'+name,sha256=hashlib.sha256(data).hexdigest(),records=len(raw)//32,record_count=len(raw)//32,start=self.start,end=self.end,start_time=self.start,end_time=self.end,bytes=len(data),uncompressed_bytes=len(raw),compression='gzip'))
  self.buffer.clear();self.start=None;self.end=None
 def close(self):
  self.flush();return self.chunks
