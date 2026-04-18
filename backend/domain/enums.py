"""Domain enums for the plant lifecycle system."""

from enum import StrEnum


class TaskType(StrEnum):
    """Allowed task types in the lifecycle system."""

    SOW = "sow"
    TRANSPLANT = "transplant"
    HARVEST = "harvest"
    PRUNE_MAINTENANCE = "prune_maintenance"
    PRUNE_STRUCTURAL = "prune_structural"
    CUT_BACK = "cut_back"
    DEADHEAD = "deadhead"
    THIN_FRUIT = "thin_fruit"
    REMOVE_DEADWOOD = "remove_deadwood"


class WeatherEventType(StrEnum):
    """Weather events computed from forecast + history data."""

    FROST_RISK_ACTIVE = "frost_risk_active"
    FROST_RISK_PASSED = "frost_risk_passed"
    SUSTAINED_MILD_NIGHTS = "sustained_mild_nights"
    WARM_SPELL = "warm_spell"
    HEATWAVE = "heatwave"
    DRY_SPELL = "dry_spell"
    PERSISTENT_RAIN = "persistent_rain"


class Season(StrEnum):
    """Meteorological seasons for planning windows."""

    EARLY_SPRING = "early_spring"  # Feb-Mar
    SPRING = "spring"  # Apr-May
    EARLY_SUMMER = "early_summer"  # Jun
    SUMMER = "summer"  # Jul-Aug
    LATE_SUMMER = "late_summer"  # Sep
    AUTUMN = "autumn"  # Oct-Nov
    WINTER = "winter"  # Dec-Jan


class TaskStatus(StrEnum):
    """Lifecycle status of a task."""

    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class Priority(StrEnum):
    """Task priority level (static importance)."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Urgency(StrEnum):
    """Computed urgency level (time pressure)."""

    ACUTE = "acute"       # Do it now or miss the window
    SOON = "soon"         # In window, no immediate pressure
    RELAXED = "relaxed"   # Plenty of time


# Month-to-season mapping (meteorological)
MONTH_TO_SEASON: dict[int, Season] = {
    1: Season.WINTER,
    2: Season.EARLY_SPRING,
    3: Season.EARLY_SPRING,
    4: Season.SPRING,
    5: Season.SPRING,
    6: Season.EARLY_SUMMER,
    7: Season.SUMMER,
    8: Season.SUMMER,
    9: Season.LATE_SUMMER,
    10: Season.AUTUMN,
    11: Season.AUTUMN,
    12: Season.WINTER,
}
