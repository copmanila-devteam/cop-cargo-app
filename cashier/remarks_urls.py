from django.urls import path

from . import remarks_views

urlpatterns = [
    path('remarks/<int:pk>/', remarks_views.get_remarks, name='get-remarks'),
    path('remarks/<int:pk>/submit/', remarks_views.submit_remark, name='submit-remark'),
]
