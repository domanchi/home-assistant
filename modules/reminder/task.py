from dataclasses import dataclass

from .cadence import Cadence


@dataclass
class Task:
    description: str
    """This is the task that needs to be done."""

    cadence: Cadence
    """This is how often the task should be run."""


tasklist = [
    Task(
        description="Send Rosie into the bedroom",
        cadence=Cadence.WEEKLY(5),
    ),
    Task(
        description="Clean pipes",
        cadence=Cadence.FORTNIGHTLY(4),
    ),

    Task(
        description="Wash bedsheets",
        cadence=Cadence.MONTHLY(1),
    ),
    Task(
        description="Clean the humidifier",
        cadence=Cadence.MONTHLY(1),
    ),
    Task(
        description="Clean the bathroom",
        cadence=Cadence.MONTHLY(10),
    ),

    # Every two months.
    Task(
        description="Replace baking soda in fridge",
        cadence=Cadence.for_period(
            date=5,
            month_divisible_by=2,
        ),
    ),
    Task(
        description="Replace baking soda in trash",
        cadence=Cadence.for_period(
            date=5,
            month_divisible_by=2,
        ),
    ),

    Task(
        description="Clean the washer/dryer",
        cadence=Cadence.QUARTERLY(),
    ),

    Task(
        description="Wash Plushies",

        # NOTE: Target Thanksgiving, so that there's additional time.
        cadence=Cadence.for_period(
            date=24,
            month_divisible_by=6,
            month_quotient=5,
        ),
    ),
    Task(
        description="Clean out fridge",
        cadence=Cadence.YEARLY(month=12, date=17),
    ),
]
