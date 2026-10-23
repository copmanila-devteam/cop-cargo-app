from django.db.models import Case, IntegerField, Q, Value, When, F
from django.utils import timezone
from .models import Event

def events_for_campus(campus_id=None):
    """Active events for a campus, plus events with no campus (shown for every campus)."""
    today = timezone.localdate()

    # Case 3: Dated events only show within their range; undated events are always active
    qs = Event.objects.filter(
        Q(start_date__lte=today) | Q(start_date__isnull=True),
        Q(end_date__gte=today)   | Q(end_date__isnull=True),
    )

    # Case 1 & 2: No campus = every campus; specific campus = that campus only
    if campus_id:
        qs = qs.filter(Q(campus_id=campus_id) | Q(campus__isnull=True))
    else:
        qs = qs.filter(campus__isnull=True)

    # Case 4: Special events are always shown on top of the selection, regardless of date.
    qs = qs.annotate(
        special_rank=Case(
            When(name__icontains='Special Event', then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    )

    # Special Events (dated) on top, ongoing events (no dates) below. Priority is ignored.
    return qs.order_by('special_rank', F('start_date').asc(nulls_last=True), 'pk')