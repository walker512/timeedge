// Original editable JavaScript Date boundary adapter. MIT walker512. No network/packages.
const fs = require('node:fs');
const r = JSON.parse(fs.readFileSync(0, 'utf8'));
const parts = r.local.split(/[-T:]/).map(Number);
let d = new Date(parts[0], parts[1]-1, parts[2], parts[3], parts[4], parts[5]);
if (r.operation === 'replace_month') d.setMonth(r.argument-1);
else if (r.operation === 'replace_year') d.setFullYear(r.argument);
else if (r.operation === 'calendar_day') d.setDate(d.getDate()+r.argument);
else if (r.operation === 'native_24h' || r.operation === 'elapsed_24h') d = new Date(d.getTime()+86400000);
else if (r.operation !== 'construct') throw new Error('Unsupported declared operation');
const pad = x => String(x).padStart(2,'0');
const fields = [d.getFullYear(),d.getMonth()+1,d.getDate(),d.getHours(),d.getMinutes(),d.getSeconds()];
const wall = `${fields[0]}-${pad(fields[1])}-${pad(fields[2])}T${pad(fields[3])}:${pad(fields[4])}:${pad(fields[5])}`;
// Derive second-resolution offset from actual wall fields and epoch; getTimezoneOffset is minute-resolution.
const offsetSeconds = (Date.UTC(...[fields[0],fields[1]-1,...fields.slice(2)])-d.getTime())/1000;
const runtime = {engine:'node',version:process.version,icu:process.versions.icu??null,tz_version:process.versions.tz??null,zone_resolved:Intl.DateTimeFormat().resolvedOptions().timeZone,tzfile_sha256:null,tzdata_package_version:null};
let observation;
if (!Number.isFinite(d.getTime())) observation = {status:'domain_error',error:'invalid_calendar_date',utc:null,epoch_ms:null,wall:null,roundtrip_wall:null,offset_seconds:null,roundtrip_offset_seconds:null,fold:null,wall_fields:null};
else observation={status:'ok',error:null,utc:d.toISOString().replace('.000Z','Z'),epoch_ms:d.getTime(),wall,roundtrip_wall:wall,offset_seconds:offsetSeconds,roundtrip_offset_seconds:offsetSeconds,fold:null,wall_fields:fields};
process.stdout.write(JSON.stringify({observation,adapter_runtime:runtime}));
