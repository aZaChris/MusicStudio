from django.urls import path

from .views import ConsentListView, ConsentWithdrawView, EraseView, ExportView

urlpatterns = [
    path("export/", ExportView.as_view(), name="privacy-export"),
    path("erase/", EraseView.as_view(), name="privacy-erase"),
    path("consents/", ConsentListView.as_view(), name="privacy-consents"),
    path("consents/<int:pk>/withdraw/", ConsentWithdrawView.as_view(), name="privacy-withdraw"),
]
