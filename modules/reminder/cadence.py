class Cadence:
    @classmethod
    def WEEKLY(cls, day: int) -> "Cadence":
        return cls.for_period(day=day)

    @classmethod
    def FORTNIGHTLY(cls, day: int) -> "Cadence":
        return cls(
            template="{}.isoweekday() == {} and {}.isocalendar().week % 2 == 0".format(
                "{now}",
                day,
                "{now}",
            ),
        )

    @classmethod
    def MONTHLY(cls, date: int) -> "Cadence":
        """
        Runs an event every month.

        If a date is specified, it will trigger on the same date every month.
        """
        return cls.for_period(date=date)

    @classmethod
    def QUARTERLY(cls) -> "Cadence":
        # NOTE: This currently causes "thundering herd" problems, but we can make it more
        # intelligent at a future date if necessary.
        return cls.for_period(month_divisible_by=3)

    @classmethod
    def YEARLY(cls, month: int, date: int) -> "Cadence":
        return cls(
            template="{}.month == {} and {}.day == {}".format(
                "{now}",
                month,
                "{now}",
                date,
            ),
        )

    @classmethod
    def for_period(
        cls,
        day: int = 5,
        date: int = 0,
        month_divisible_by: int = 1,
        month_quotient: int = 0,
    ) -> "Cadence":
        """
        :param day: Python's numerical representation of weekday (see datetime.datetime.isoweekday()).
            Monday == 1; Sunday == 7.
            Defaults to Friday, so chores can be discovered before the weekend.

        :param date: The current date. Should be used with month_divisible_by and month_quotient,
            so as not to trigger the same event for all weeks for a given month. If set to a
            positive integer, this will ignore `day`.

        :param month_divisible_by: Mechanism to cause recurring events. Combined with
            `month_quotient`, these parameters will control how often the event gets run.

        :param month_quotient: The formula for calculating whether an event should be triggered
            on a specific month is `current_month % month_divisible_by == month_quotient`
        """
        format = []
        if month_divisible_by > 1 or month_quotient > 0:
            format.append("{}.month % {} == {}".format("{now}", month_divisible_by, month_quotient))

        if date:
            format.append("{}.day == {}".format("{now}", date))
        else:
            format.append("{}.isoweekday() == {}".format("{now}", day))

        return cls(template=" and ".join(format))

    def __init__(self, template: str) -> None:
        self._template = template

    def render(self, now: str) -> str:
        """
        :param now: string representation of current date object
        :returns: HomeAssistant's Jinja-compatible template string to represent the
            trigger date that represents the specified cadence.
        """
        return "{{ %s }}" % self._template.format(now=now)
