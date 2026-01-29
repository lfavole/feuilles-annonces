import datetime as dt
from itertools import chain

from fpdf.fonts import FontFace

from . import PDF
from ..models import Date, FixedFeast, MovableFeast, Week
from ..utils import format_date_or_time, striptags


class FeuilleAnnonces(PDF):
    def __init__(self, *args, **kwargs):
        super().__init__("L")

    def get_longest_hour_string_width(self):
        return max(self.get_string_width(digit) for digit in "0123456789") * 4 + self.get_string_width("h - h ")

    def render(self, week=""):
        self.add_page()

        try:
            offset = int(week)
        except ValueError:
            week = Week(week, True)
        else:
            week = Week.get_current()
            week += dt.timedelta(weeks=offset)

        dates = Date.objects.get_for_week(week)
        fixed_feasts = FixedFeast.objects.all()
        movable_feasts = MovableFeast.objects.all()

        feasts: list[Date] = list(
            chain.from_iterable(
                feast.get_occurrences(week) for feast in chain(fixed_feasts, movable_feasts)
            )
        )

        self.start_columns(ncols=2)

        self.draw_header(
            format_date_or_time(week.start, week.end, weekday=False, year=True, natural=True)
            .replace("1<sup>er</sup>", "1er")
        )

        line_height = self.font_size * 1.25

        day = week.start
        while day in week:
            with self.use_font_face(FontFace(emphasis="BU")):
                self.write(line_height, striptags(format_date_or_time(day)).capitalize())
            with self.use_font_face(FontFace(size_pt=0.85 * self.font_size_pt)):
                old_l_margin = self.l_margin
                x = None
                for feast in feasts:
                    if feast.start_date == day:
                        self.write(line_height, " - ")
                        if x is None:
                            x = self.x
                            self.l_margin = x
                        self.write(line_height, striptags(feast.title))
                self.l_margin = old_l_margin
            self.ln()
            for date in dates:
                if date.start_date == day:
                    self.cell(self.get_longest_hour_string_width(), line_height, format_date_or_time(date.start_time, date.end_time, natural_time=True))
                    self.cell(0, line_height, striptags(date.title))
                    self.ln()
            self.ln()
            day += dt.timedelta(days=1)
