import pytest

from modules.reminder.cadence import Cadence


@pytest.mark.parametrize(
    "cadence, expected",
    (
        (
            Cadence.WEEKLY(5),
            "{{ now.isoweekday() == 5 }}",
        ),
        (
            Cadence.FORTNIGHTLY(2),
            "{{ now.isoweekday() == 2 and now.isocalendar().week % 2 == 0 }}",
        ),
        (
            Cadence.MONTHLY(10),
            "{{ now.day == 10 }}",
        ),
        (
            Cadence.QUARTERLY(),
            "{{ now.month % 3 == 0 and now.isoweekday() == 5 }}",
        ),
        (
            Cadence.YEARLY(month=12, date=17),
            "{{ now.month == 12 and now.day == 17 }}",
        ),
    ),
)
def test_render_cadence(cadence, expected):
    assert cadence.render("now") == expected
