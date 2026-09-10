from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TableViewSet, ValidateTableView

app_name = 'restaurant'

router = DefaultRouter()
router.register('tables', TableViewSet, basename='table')

urlpatterns = [
    path('tables/validate/', ValidateTableView.as_view(), name='table-validate'),
    path('', include(router.urls)),
]
