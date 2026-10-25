from django.db.models import Q
from django.utils import timezone
from .models import Event, ServiceSchedule

# date.weekday() -> ServiceSchedule.days code
WEEKDAY_CODES = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']


def active_events(day=None):
    """Events running on a day. No End Date = a one-day event on its Start Date; no Start Date = never."""
    day = day or timezone.localdate()
    return Event.objects.filter(
        Q(start_date__lte=day),
        Q(end_date__gte=day) | Q(end_date__isnull=True, start_date=day),
    )


def event_for_campus(campus_id, day=None):
    """The Event running on a campus on a day, or None for a regular service.
    No campus = every campus; specific campus = that campus only. Higher priority wins."""
    return (
        active_events(day)
        .filter(Q(campus_id=campus_id) | Q(campus__isnull=True))
        .order_by('-priority', 'pk')
        .first()
    )


def event_day_codes(event, day=None):
    """Weekday codes of the event's remaining days, from `day` to its End Date (or Start Date if it has none).
    e.g. a Fri-Sun event seen on Friday -> {'FRI', 'SAT', 'SUN'}"""
    day = day or timezone.localdate()
    last_day = event.end_date or event.start_date
    days_left = min((last_day - day).days, 6)  # a week or more covers every weekday
    return {WEEKDAY_CODES[(day.weekday() + offset) % 7] for offset in range(days_left + 1)}


def days_until(day_code, day=None):
    """Days from `day` to the next schedule day, 0 = today. e.g. on Saturday: SAT -> 0, SUN -> 1, FRI -> 6"""
    day = day or timezone.localdate()
    if day_code not in WEEKDAY_CODES:
        return 7  # no day set: list last
    return (WEEKDAY_CODES.index(day_code) - day.weekday()) % 7


def schedules_for_campus(campus_id=None):
    """Service Schedule options for a campus."""
    return ServiceSchedule.objects.filter(campus_id=campus_id).select_related('campus').order_by('pk')
