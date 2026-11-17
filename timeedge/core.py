from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import calendar

UTC = timezone.utc

def candidates(local, zone):
    """Valid UTC instants, round-trip validated; zero, one, or two."""
    if local.tzinfo is not None:
        raise ValueError('local datetime must have no offset')
    valid = set()
    for fold in (0, 1):
        instant = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) == local:
            valid.add(instant)
    return sorted(valid)

def resolve(local, zone_name, ambiguous='reject', nonexistent='reject'):
    if ambiguous not in ('reject', 'earlier', 'later', 'both'):
        raise ValueError('invalid ambiguous policy')
    if nonexistent not in ('reject', 'skip', 'shift-forward'):
        raise ValueError('invalid nonexistent policy')
    zone = ZoneInfo(zone_name)
    valid = candidates(local, zone)
    kind = ('nonexistent', 'normal', 'ambiguous')[len(valid)]
    adjustment = None
    if not valid:
        if nonexistent == 'shift-forward':
            # Move by the actual transition gap, preserving minute/second.
            # Round-trip both hypothetical folds and choose the first later wall time.
            later = []
            for fold in (0, 1):
                rt = local.replace(tzinfo=zone, fold=fold).astimezone(UTC).astimezone(zone)
                if rt.replace(tzinfo=None) > local:
                    later.append(rt)
            if not later:
                raise ValueError('cannot resolve timezone transition')
            shifted = min(later, key=lambda x: x.replace(tzinfo=None))
            valid = [shifted.astimezone(UTC)]
            adjustment = str(shifted.replace(tzinfo=None) - local)
        status = 'rejected' if nonexistent == 'reject' else ('skipped' if nonexistent == 'skip' else 'adjusted')
    elif len(valid) == 2:
        status = 'rejected' if ambiguous == 'reject' else 'resolved'
        if ambiguous == 'reject': valid = []
        elif ambiguous == 'earlier': valid = valid[:1]
        elif ambiguous == 'later': valid = valid[-1:]
    else:
        status = 'resolved'
    return dict(requested=local.isoformat(), zone=zone_name, kind=kind, status=status,
                adjustment=adjustment, utc=[x.isoformat() for x in valid],
                wall=[x.astimezone(zone).isoformat() for x in valid])

def schedule(start, count, zone, recurrence='daily', month_end='reject', ambiguous='reject', nonexistent='reject'):
    if start.tzinfo is not None: raise ValueError('start must be a local time without offset')
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 366: raise ValueError('count must be 1..366')
    if recurrence not in ('daily', 'monthly', 'yearly'): raise ValueError('invalid recurrence')
    if month_end not in ('reject', 'skip', 'clamp'): raise ValueError('invalid month-end policy')
    rows = []
    for i in range(count):
        if recurrence == 'daily':
            local = start + timedelta(days=i)
            requested = local.isoformat()
            calendar_adjustment = False
        else:
            n = (start.year * 12 + start.month - 1) + i * (12 if recurrence == 'yearly' else 1)
            year, month0 = divmod(n, 12)
            if not 1 <= year <= 9999: raise ValueError('schedule exceeds supported year range')
            month = month0 + 1
            requested = f'{year:04}-{month:02}-{start.day:02}T{start.time().isoformat()}'
            last = calendar.monthrange(year, month)[1]
            calendar_adjustment = start.day > last
            if calendar_adjustment and month_end != 'clamp':
                rows.append(dict(requested=requested, zone=zone, kind='invalid-calendar-date',
                                 status='skipped' if month_end == 'skip' else 'rejected', utc=[], wall=[], adjustment=None))
                continue
            local = start.replace(year=year, month=month, day=min(start.day, last))
        row = resolve(local, zone, ambiguous, nonexistent)
        row['requested'] = requested
        row['calendar_adjusted'] = calendar_adjustment
        rows.append(row)
    return rows
