"""Original editable Python boundary adapter, standard library only. MIT walker512."""
import hashlib,importlib.metadata,json,platform,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo,TZPATH,ZoneInfoNotFoundError
r=json.load(sys.stdin);zone=r['zone'];tz=ZoneInfo(zone);fingerprint=None
for base in TZPATH:
    p=Path(base)/zone
    if p.is_file():fingerprint=hashlib.sha256(p.read_bytes()).hexdigest();break
try:package=importlib.metadata.version('tzdata')
except importlib.metadata.PackageNotFoundError:package=None
runtime={'engine':'python','version':platform.python_version(),'icu':None,'tz_version':None,'zone_resolved':zone,'tzfile_sha256':fingerprint,'tzdata_package_version':package}
fields=('utc','epoch_ms','wall','roundtrip_wall','offset_seconds','roundtrip_offset_seconds','fold','wall_fields')
try:
    d=datetime.fromisoformat(r['local']).replace(tzinfo=tz);op=r['operation']
    if op=='construct':pass
    elif op=='replace_month':d=d.replace(month=r['argument'])
    elif op=='replace_year':d=d.replace(year=r['argument'])
    elif op=='calendar_day':d=d+timedelta(days=r['argument'])
    elif op=='native_24h':d=d+timedelta(hours=24)
    elif op=='elapsed_24h':d=(d.astimezone(timezone.utc)+timedelta(hours=24)).astimezone(tz)
    else:raise RuntimeError('Unsupported declared operation')
    utc=d.astimezone(timezone.utc);rt=utc.astimezone(tz)
    observation={'status':'ok','error':None,'utc':utc.strftime('%Y-%m-%dT%H:%M:%SZ'),'epoch_ms':int(utc.timestamp())*1000,'wall':d.replace(tzinfo=None).isoformat(timespec='seconds'),'roundtrip_wall':rt.replace(tzinfo=None).isoformat(timespec='seconds'),'offset_seconds':int(d.utcoffset().total_seconds()),'roundtrip_offset_seconds':int(rt.utcoffset().total_seconds()),'fold':d.fold,'wall_fields':[d.year,d.month,d.day,d.hour,d.minute,d.second]}
except ValueError:observation={'status':'domain_error','error':'invalid_calendar_date',**{k:None for k in fields}}
print(json.dumps({'observation':observation,'adapter_runtime':runtime},ensure_ascii=True))
