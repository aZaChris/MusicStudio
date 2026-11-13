"""The API is for the app, not for search engines: every response says "do not index"."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


def noindex_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    def middleware(request: HttpRequest) -> HttpResponse:
        response = get_response(request)
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    return middleware
