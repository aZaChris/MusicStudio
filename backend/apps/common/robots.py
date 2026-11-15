"""L'API è per l'app, non per i motori di ricerca: ogni risposta dice "non indicizzare".

Spiegazione: docs/learning/concetti/indicizzazione-e-sitemap.md.
"""

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
