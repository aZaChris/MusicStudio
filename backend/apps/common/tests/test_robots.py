"""Every API response carries X-Robots-Tag: the API must never show up in search results."""

import pytest
from rest_framework.test import APIClient


@pytest.mark.parametrize("path", ["/health/live/", "/api/schema/", "/does-not-exist/"])
def test_responses_are_marked_noindex(path):
    # A 200, a generated page and a 404 all get the header: it is not tied to a view.
    response = APIClient().get(path)

    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
