"""Contextual garden tips based on season and weather events.

These are informational reminders, not tasks. They appear in the
dashboard to help with general garden awareness.
"""

from __future__ import annotations

from backend.domain.enums import Season, WeatherEventType
from backend.domain.models import EventState


class GardenTip:
    """A contextual garden tip with emoji and priority."""

    def __init__(
        self,
        icon: str,
        title: str,
        detail: str,
        priority: int = 0,
    ) -> None:
        self.icon = icon
        self.title = title
        self.detail = detail
        self.priority = priority  # lower = more important


# Season-based tips (always shown for the season)
SEASON_TIPS: dict[Season, list[GardenTip]] = {
    Season.EARLY_SPRING: [
        GardenTip(
            "🌱", "Aussaat planen",
            "Vorfrühling ist die Zeit für die Aussaatplanung. "
            "Kaltkeimer können jetzt noch ausgesät werden. "
            "Tomaten und Paprika auf der Fensterbank vorziehen.",
        ),
        GardenTip(
            "🧹", "Beete kontrollieren",
            "Nach dem Winter Beete auf Frostschäden prüfen. "
            "Hochgedrückte Pflanzen vorsichtig wieder andrücken.",
        ),
    ],
    Season.SPRING: [
        GardenTip(
            "🌿", "Jungpflanzen abhärten",
            "Vorgezogene Pflanzen tagsüber nach draußen stellen, "
            "nachts reinholen. Nach den Eisheiligen (Mitte Mai) "
            "können frostempfindliche Pflanzen raus.",
        ),
        GardenTip(
            "🐝", "Nützlinge fördern",
            "Nicht alles aufräumen! Totholzhaufen, offene "
            "Bodenstellen und Wildblumenecken bieten Nistplätze "
            "für Wildbienen und Nützlinge.",
        ),
    ],
    Season.EARLY_SUMMER: [
        GardenTip(
            "💧", "Gießrhythmus anpassen",
            "Sandiger Boden: lieber 2-3x pro Woche durchdringend "
            "gießen als täglich oberflächlich. Morgens gießen "
            "reduziert Pilzbefall und Verdunstung.",
        ),
        GardenTip(
            "🌻", "Staudenbeete kontrollieren",
            "Hohe Stauden rechtzeitig stützen, bevor sie "
            "umfallen. Verblühtes regelmäßig entfernen.",
        ),
    ],
    Season.SUMMER: [
        GardenTip(
            "☀️", "Urlaubsvorbereitung",
            "Vor dem Urlaub: Mulch erneuern, Rasen etwas "
            "höher stehen lassen (trocknet weniger aus), "
            "Nachbarn zum Gießen einweisen.",
        ),
    ],
    Season.LATE_SUMMER: [
        GardenTip(
            "🌷", "Frühjahrsblüher pflanzen",
            "Ab September Tulpen, Narzissen und Krokusse "
            "setzen. In sandigem Boden etwas tiefer pflanzen "
            "als empfohlen (2-3cm extra).",
        ),
        GardenTip(
            "✂️", "Stecklinge nehmen",
            "Jetzt ist ein guter Zeitpunkt für Stecklinge von "
            "Lavendel, Rosmarin, Hortensien und Buchsbaum.",
        ),
    ],
    Season.AUTUMN: [
        GardenTip(
            "🍂", "Laub sinnvoll nutzen",
            "Laub auf Beeten liegen lassen (natürlicher "
            "Frostschutz + Dünger). Nur auf Rasen und Wegen "
            "entfernen. Laubhaufen als Igelquartier anlegen.",
        ),
        GardenTip(
            "🌳", "Pflanzzeit für Gehölze",
            "Herbst ist die beste Pflanzzeit für Bäume und "
            "Sträucher. Der Boden ist noch warm, die Wurzeln "
            "wachsen bis zum Frühjahr an.",
        ),
    ],
    Season.WINTER: [
        GardenTip(
            "📋", "Gartenjahr planen",
            "Saatgutkataloge studieren, Beetpläne zeichnen, "
            "Fruchtfolge für Gemüsebeete planen. Werkzeuge "
            "reinigen und schärfen.",
        ),
        GardenTip(
            "🐦", "Vögel füttern",
            "Futterstellen regelmäßig befüllen und sauber "
            "halten. Wasser anbieten (Schale mit Stein gegen "
            "Einfrieren).",
        ),
    ],
}

# Weather-event-triggered tips (shown when specific events are active)
EVENT_TIPS: dict[WeatherEventType, list[GardenTip]] = {
    WeatherEventType.FROST_RISK_ACTIVE: [
        GardenTip(
            "🥶", "Frostwarnung!",
            "Empfindliche Pflanzen heute Abend abdecken (Vlies, "
            "Eimer). Kübelpflanzen an die Hauswand rücken. "
            "Frisch gepflanzte Stauden mit Laub schützen.",
            priority=-10,
        ),
    ],
    WeatherEventType.HEATWAVE: [
        GardenTip(
            "🔥", "Hitzeschutz",
            "Bei 30°C+ nur morgens vor 9 Uhr oder abends nach "
            "19 Uhr gießen. Empfindliche Pflanzen schattieren. "
            "Kein Rasen mähen bei Hitze. Sandiger Boden heizt "
            "sich besonders auf – Mulch hilft!",
            priority=-8,
        ),
    ],
    WeatherEventType.DRY_SPELL: [
        GardenTip(
            "💧", "Trockenheit – tief gießen!",
            "Sandiger Boden: Wasser versickert schnell. "
            "20 Liter pro m² auf einmal, dafür seltener. "
            "Flachwurzler und Neuanpflanzungen zuerst. "
            "Rasen nicht bewässern – er erholt sich nach Regen.",
            priority=-5,
        ),
    ],
    WeatherEventType.PERSISTENT_RAIN: [
        GardenTip(
            "🐌", "Schneckenalarm",
            "Nach Dauerregen sind Schnecken sehr aktiv. "
            "Abends kontrollieren, besonders Salat, Hostas "
            "und frische Aussaaten. Hochbeete sind weniger "
            "betroffen.",
            priority=-5,
        ),
        GardenTip(
            "🍄", "Pilzkrankheiten beobachten",
            "Feuchtigkeit fördert Mehltau, Rost und Grauschimmel. "
            "Befallene Blätter sofort entfernen (NICHT kompostieren). "
            "Pflanzen nicht von oben gießen.",
            priority=-3,
        ),
    ],
    WeatherEventType.WARM_SPELL: [
        GardenTip(
            "🌡️", "Wärmephase nutzen",
            "Guter Zeitpunkt zum Auspflanzen vorgezogener "
            "Jungpflanzen. Warmer Boden fördert Wurzelwachstum. "
            "Auf sandigem Boden nach dem Pflanzen gut angießen.",
            priority=0,
        ),
    ],
    WeatherEventType.SUSTAINED_MILD_NIGHTS: [
        GardenTip(
            "🌙", "Milde Nächte",
            "Frostempfindliche Pflanzen können jetzt sicher "
            "nach draußen. Tomaten, Gurken und Basilikum "
            "brauchen Nachttemperaturen über 8°C.",
            priority=0,
        ),
    ],
}


def get_tips(
    season: Season,
    event_state: EventState,
) -> list[GardenTip]:
    """Get contextual garden tips for current conditions.

    Returns season tips + event-triggered tips, sorted by priority.
    """
    tips: list[GardenTip] = []

    # Season tips
    tips.extend(SEASON_TIPS.get(season, []))

    # Event-triggered tips
    for event_type in WeatherEventType:
        if event_state.is_active(event_type):
            tips.extend(EVENT_TIPS.get(event_type, []))

    tips.sort(key=lambda t: t.priority)
    return tips
