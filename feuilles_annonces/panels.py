import sys

from debug_toolbar.decorators import render_with_toolbar_language, require_show_toolbar
from debug_toolbar.panels import Panel
from debug_toolbar.toolbar import DebugToolbar
from django.core.handlers import exception
from django.core.handlers.exception import response_for_exception
from django.http import Http404, HttpRequest, HttpResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _
from django.views.debug import ExceptionReporter, technical_404_response
from django.views.decorators.clickjacking import xframe_options_exempt


class ErrorPanel(Panel):
    """
    A panel that displays debug information about 404 or 500 errors.
    """

    title = _("Error")  # type: ignore
    template = "debug_toolbar/panels/error.html"  # type: ignore

    @property
    def nav_subtitle(self):
        exc_info = self.get_stats().get("exc_info")
        if exc_info is None:
            return _("No error")
        try:
            return f"{exc_info[0].__name__}: {exc_info[1]}"
        except AttributeError:
            return f"{exc_info[0]}: {exc_info[1]}"

    @property
    def has_content(self):
        return self.get_stats().get("exc_info") is not None

    def generate_stats(self, request, response):
        self.toolbar.init_store()  # ensure that request_id exists
        td = self.toolbar.__dict__
        self.record_stats(
            {
                "request": request,
                "request_id": self.toolbar.request_id,
            }
        )

    def enable_instrumentation(self):
        exception._old_response_for_exception = response_for_exception  # type: ignore

        def new_response_for_exception(request: HttpRequest, exc: Exception):
            """
            Saves the exception and continues normal processing.
            """
            self.record_stats({"exc_info": sys.exc_info()})
            return exception._old_response_for_exception(request, exc)  # type: ignore

        exception.response_for_exception = new_response_for_exception

    def disable_instrumentation(self):
        exception.response_for_exception = exception._old_response_for_exception  # type: ignore

    @property
    def error_content(self):
        """
        Returns the content of the `<iframe>` that contains the error.
        """
        stats = self.get_stats()
        exc_info = stats.get("exc_info")
        request = stats.get("request")

        if exc_info is None:
            return ""

        if isinstance(stats["exc_info"][1], Http404):
            return technical_404_response(request, exc_info[1])

        reporter = ExceptionReporter(request, *exc_info)
        return reporter.get_traceback_html()

    @classmethod
    def get_urls(cls):
        return [path("error-panel", error_panel_view, name="error_panel")]


@require_show_toolbar
@render_with_toolbar_language
@xframe_options_exempt
def error_panel_view(request):
    """
    Render the contents of the error.
    """
    toolbar = DebugToolbar.fetch(request.GET["request_id"])
    if toolbar is None:
        return HttpResponse()

    panel = toolbar.get_panel_by_id("ErrorPanel")
    return HttpResponse(panel.error_content)
