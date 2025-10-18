from math import isclose
import re

from django.http import HttpResponse
from fpdf import FPDF, FPDF_VERSION
from fpdf.enums import Align, CharVPos, XPos, YPos
from fpdf.fonts import FontFace
from fpdf.image_parsing import preload_image
from fpdf.line_break import Fragment

from .fonts import get_montserrat_font
from ..models import Config


class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.default_font = "Montserrat"
        self._in_set_font = False
        self._in_add_page = False

        self._ncols = 0

        self.set_author("Secteur paroissial de l'Embrunais et du Savinois")
        self.set_creator("Générateur de feuilles d'annonces (https://github.com/lfavole/feuilles-annonces)")
        self.set_producer(f"fpdf2 v{FPDF_VERSION} (https://github.com/py-pdf/fpdf2)")

        self.set_margin(10)
        self.set_auto_page_break(True, 10)

        self.font_styles = [
            (r"((?<=[IVX]|\d)(?:e|er|ère|ème|nde)s?\b)", self._superscript),
            (r"(\+\d[\d ]{5,}\d|0\d(?: \d\d){4,})", self._phone_link),
            (r"([\w.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", self._email_link),
            # https://stackoverflow.com/a/3809435
            (
                r"(https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\b[-a-zA-Z0-9@:%_\+.~#?&//=]*)",
                self._link,
            ),
        ]

    def _superscript(self, frag: Fragment):
        frag.graphics_state["char_vpos"] = CharVPos.SUP

    def _phone_link(self, frag: Fragment):
        self._link(frag)
        frag.link = "tel:" + frag.string.replace(" ", "")

    def _email_link(self, frag: Fragment):
        self._link(frag)
        frag.link = "mailto:" + frag.string

    def _link(self, frag: Fragment):
        frag.link = frag.string
        frag.graphics_state["underline"] = True
        if self.MARKDOWN_LINK_COLOR:
            frag.graphics_state["text_color"] = self.MARKDOWN_LINK_COLOR

    def _preload_font_styles(self, txt, markdown):
        """
        Apply all the font styles defined above (superscripts, phone numbers and email links).
        """
        frags: list[Fragment] = super()._preload_font_styles(txt, markdown)
        if len(frags) == 1 and not frags[0].characters:
            return frags

        for regexp, function in self.font_styles:
            ret = []
            for frag in frags:
                parts = re.split(regexp, frag.string)
                for i, part in enumerate(parts):
                    if not part:
                        continue
                    new_frag = Fragment(part, frag.graphics_state.copy(), frag.k, frag.link)
                    if i % 2 == 1:  # group captured by the split regex
                        function(new_frag)
                    ret.append(new_frag)
            frags = ret  # re-process the fragments

        return frags

    # These 2 properties are used to check the current font
    @property
    def current_font(self):
        ret = super().current_font
        if ret or self._in_set_font:
            return ret
        self.set_font()
        return super().current_font

    @current_font.setter
    def current_font(self, value):
        self._GraphicsStateMixin__statestack[-1]["current_font"] = value  # type: ignore

    @property
    def font_family(self):
        ret = super().font_family
        if ret or self._in_set_font or self._in_add_page:
            return ret
        self.set_font()
        return super().font_family

    @font_family.setter
    def font_family(self, value):
        self._GraphicsStateMixin__statestack[-1]["font_family"] = value  # type: ignore

    def add_page(self, *args, **kwargs):
        self._in_add_page = True
        try:
            return super().add_page(*args, **kwargs)
        finally:
            self._in_add_page = False

    def set_font(self, family=None, style="", size=0) -> None:
        self._in_set_font = True

        key_style = "".join(c for c in str(style).upper() if c in "BI")
        key_family = (family or self.font_family or self.default_font).lower()  # don't use the property above

        if not size:
            size = self.font_size_pt

        # Test if font is already selected
        if (
            self.font_family == family
            and self.font_style == style
            and isclose(self.font_size_pt, size)
        ):
            return

        if key_family == "montserrat":
            key = key_family + key_style
            if key not in self.fonts:
                self.add_font(
                    key_family,
                    key_style,  # type: ignore
                    get_montserrat_font(key_style),
                )

        super().set_font(key_family, style, size)
        self._in_set_font = False

    def draw_header(self, title=""):
        config = Config.objects.get()

        logo_width = self.epw - self.get_string_width(config.official_name) - 10
        l_margin = self.l_margin
        y = self.y

        info = self.image(config.logo, w=logo_width)
        height = info.rendered_height

        end_y = self.y

        self.l_margin += logo_width + 2 * self.c_margin
        self.x = self.l_margin
        self.y = y

        text_line_height = self.font_size * 1.35
        if text_line_height * 4 > height:
            text_line_height = height / 4
        else:
            self.y += (height - text_line_height * 4) / 2
        self.cell(w=0, h=text_line_height, text=config.official_name, align=Align.C, new_x=XPos.LEFT, new_y=YPos.NEXT)
        with self.use_font_face(FontFace(size_pt=self.font_size_pt * 2)):
            self.cell(w=0, h=text_line_height * 2, text="Sous nos clochers", align=Align.C, new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.cell(w=0, h=text_line_height, text=title, align=Align.C, new_x=XPos.LEFT, new_y=YPos.NEXT)

        self.l_margin = l_margin
        self.x = l_margin
        self.y = end_y

    def start_columns(self, ncols: int, gutter: float | None = None):
        if gutter is None:
            gutter = (self.l_margin + self.r_margin) / 2

        self._col_n = 0
        self._ncols = ncols
        self._gutter = gutter
        self._old_l_margin = self.l_margin
        self._old_r_margin = self.r_margin
        self._fix_cols_margin()

    @property
    def _col_width(self):
        return (
            self.w - self._old_l_margin - self._old_r_margin - self._gutter * (self._ncols - 1)
        ) / self._ncols

    def _fix_cols_margin(self):
        self.l_margin = self._old_l_margin + (self._col_width + self._gutter) * self._col_n
        self.r_margin = self.w - self.l_margin - self._col_width

    @property
    def accept_page_break(self) -> bool:
        if not self._ncols:
            return super().accept_page_break

        self._col_n += 1

        if self._col_n == self._ncols:
            self._col_n = 0
            return True

        self._fix_cols_margin()
        self.x = self.l_margin
        self.y = self.t_margin
        return False

    def end_columns(self):
        self._ncols = 0
        self.l_margin = self._old_l_margin
        self.r_margin = self._old_r_margin

    @classmethod
    def as_view(cls, *args, **kwargs):
        def view(request, *args, **kwargs):
            pdf = cls()
            pdf.render(*args, **kwargs)
            return HttpResponse(bytes(pdf.output()), content_type="application/pdf")

        return view
