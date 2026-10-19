from django.urls import path

from . import remarks_views

urlpatterns = [
    path('remarks/<int:pk>/submit/', remarks_views.submit_remark, name='submit-remark'),
]
