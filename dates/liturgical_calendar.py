import datetime as dt

from dateutil.easter import easter as easter_date_for


def get_liturgical_year(date: dt.date):
    """Return the liturgical year of the date."""
    if isinstance(date, dt.datetime):
        date = date.date()  # otherwise the final comparison doesn't work

    christmas = dt.date(date.year, 12, 25)

    advent_start = christmas - dt.timedelta(days=1)
    while advent_start.weekday() != 6:
        advent_start -= dt.timedelta(days=1)
    advent_start -= dt.timedelta(weeks=3)

    if date < advent_start:
        return date.year - 1
    return date.year


default_translations = {
    "advent_sunday": "$ord dimanche de l'Avent",
    "holy_family": "La Sainte Famille",
    "epiphany": "L'Épiphanie du Seigneur",
    "lord_baptism": "Le Baptême du Seigneur",
    "ordinary_time_sunday": "$ord dimanche du Temps Ordinaire",
    "ash_wednesday": "Mercredi des Cendres",
    "lent_sunday": "$ord dimanche de Carême",
    "palm_sunday": "Dimanche des Rameaux",
    "holy_thursday": "Jeudi Saint",
    "good_friday": "Vendredi Saint",
    "holy_saturday": "Samedi Saint",
    "easter": "Résurrection du Seigneur",
    "easter_sunday": "$ord dimanche de Pâques",
    "ascension": "Ascension",
    "pentecost": "Pentecôte",
}


def get_movable_feasts_for(year: int) -> dict[dt.date, tuple[str, dict[str, str | int]]]:
    """Returns the movable feasts for the specified liturgical year."""

    # Key dates needed to calculate the other ones
    christmas = dt.date(year, 12, 25)

    advent_start = christmas - dt.timedelta(days=1)
    while advent_start.weekday() != 6:
        advent_start -= dt.timedelta(days=1)
    advent_start -= dt.timedelta(weeks=3)

    easter = easter_date_for(year + 1)
    ash_wednesday = easter - dt.timedelta(days=46)
    pentecost = easter + dt.timedelta(days=49)

    christ_king = dt.date(year + 1, 12, 24)
    while christ_king.weekday() != 6:
        christ_king -= dt.timedelta(days=1)
    christ_king -= dt.timedelta(weeks=4)

    mobile_dates = {}
    current_date = advent_start

    advent_sunday_n = 1
    while current_date < christmas:
        assert advent_sunday_n < 5
        mobile_dates[current_date] = ("advent_sunday", {"n": advent_sunday_n})
        current_date += dt.timedelta(weeks=1)
        advent_sunday_n += 1

    if current_date == christmas:
        # Add Holy Family on December 30th (otherwise it would overflow on January 1st)
        mobile_dates[dt.date(year, 12, 30)] = ("holy_family", {})
        # Skip January 1st
        current_date += dt.timedelta(weeks=1)
    else:
        # Holy Family is the Sunday after Christmas
        mobile_dates[current_date] = ("holy_family", {})

    # Move to Epiphany
    current_date += dt.timedelta(weeks=1)

    assert current_date.year == year + 1
    assert current_date.month == 1
    assert 2 <= current_date.day <= 8
    assert current_date.weekday() == 6
    mobile_dates[current_date] = ("epiphany", {})

    if current_date.day in (7, 8):
        current_date += dt.timedelta(days=1)
    else:
        current_date += dt.timedelta(weeks=1)
    mobile_dates[current_date] = ("lord_baptism", {})

    # Move to the 1st Sunday of Ordinary Time (that might be the Lord Baptism)
    if current_date.weekday() == 0:
        # Lord Baptism was a Monday => go back
        current_date -= dt.timedelta(days=1)
    else:
        assert current_date.weekday() == 6

    # Go to the 2nd Sunday of Ordinary Time
    current_date += dt.timedelta(weeks=1)
    ordinary_sunday_n = 2

    while current_date < ash_wednesday:
        mobile_dates[current_date] = ("ordinary_time_sunday", {"n": ordinary_sunday_n})
        current_date += dt.timedelta(weeks=1)
        ordinary_sunday_n += 1

    mobile_dates[current_date - dt.timedelta(days=4)] = ("ash_wednesday", {})

    lent_sunday_n = 1
    while current_date < easter:
        mobile_dates[current_date] = ("lent_sunday", {"n": lent_sunday_n})
        current_date += dt.timedelta(weeks=1)
        lent_sunday_n += 1

    # this will override the previously defined Sunday
    mobile_dates[current_date - dt.timedelta(weeks=1)] = ("palm_sunday", {})
    mobile_dates[current_date - dt.timedelta(days=3)] = ("holy_thursday", {})
    mobile_dates[current_date - dt.timedelta(days=2)] = ("good_friday", {})
    mobile_dates[current_date - dt.timedelta(days=1)] = ("holy_saturday", {})
    mobile_dates[current_date] = ("easter", {})

    current_date += dt.timedelta(weeks=1)
    easter_sunday_n = 2  # we're already on Easter
    while current_date < pentecost:
        mobile_dates[current_date] = ("easter_sunday", {"n": easter_sunday_n})
        current_date += dt.timedelta(weeks=1)
        easter_sunday_n += 1

    mobile_dates[current_date - dt.timedelta(weeks=1, days=3)] = ("ascension", {})
    mobile_dates[current_date] = ("pentecost", {})

    # The week after Pentecost is counted as an Ordinary Week
    ordinary_sunday_n += 1
    # Move to next Sunday
    current_date += dt.timedelta(weeks=1)

    # Christ King is the last Sunday of the liturgical year
    tmp = {}
    while current_date <= christ_king:
        tmp[current_date] = ordinary_sunday_n
        current_date += dt.timedelta(weeks=1)
        ordinary_sunday_n += 1

    # Get the last Ordinary Time Sunday number
    # (or the total number of Ordinary Time Sundays)
    ordinary_sunday_n -= 1

    # There must be 34 Ordinary Time Sundays so we skip one during Lent
    if ordinary_sunday_n == 33:
        to_add = 1
    else:
        to_add = 0
        assert ordinary_sunday_n == 34

    for date, n in tmp.items():
        mobile_dates[date] = ("ordinary_time_sunday", {"n": n + to_add})

    return dict(sorted(mobile_dates.items(), key=lambda item: item[0]))
