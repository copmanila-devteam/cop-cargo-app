from django.urls import path, include

from django.contrib.auth.views import LogoutView

from .views import CashierView, AttendeeView, VoucherView, BookingHistoryView, ReportsView, AccountingView

from Account.views import LoginCargoView, RegistrationView

from . import views



urlpatterns = [
    path('login/',LoginCargoView.as_view(),name='login-cargo'),

    path('logout', LogoutView.as_view(), name='logout-cargo'),

    path('register/',RegistrationView.as_view(), name='register'),

    path('', CashierView.as_view(), name='cashier'),

    path('accounting/', AccountingView.as_view(), name='accounting'),

    path('accounting/<int:id>/details/', AccountingView.as_view(), name='accounting-detail'),

    path('fetch_vouchers/', CashierView.as_view(), name='cashier-list'),
    
    # New url added. fetch_vouchers with campus_id params
    # Added by: John Cedric Ureta
    path('fetch_vouchers/<int:campus_id>', CashierView.as_view(), name='cashier-campus-list'),

    path('cashier/<int:id>/details/', CashierView.as_view(), name='cashier-detail'),

    path('update_remarks/<int:pk>/', views.update_remarks, name='update-remarks'),

    path('', include('cashier.remarks_urls')),

    path('update_amount/<int:pk>/', views.update_amount, name='update-amount'),

    path('attendees/', AttendeeView.as_view(), name='manage-attendees'),

    path('attendees/<int:id>/delete/', AttendeeView.as_view(), name='delete-attendees'),

    path('vouchers/', VoucherView.as_view(), name='vouchers-list'),
    path('history/', BookingHistoryView.as_view(), name='booking-history'),

    path('trip/', views.CargoView.as_view(), name='cashier_entry'),

    path('add-passenger/', views.add_passenger, name='add_passenger'),

    path('remove-passenger/<int:index>/', views.remove_passenger, name='remove_passenger'),

    path('approvals_list/', views.cashier_list.as_view(), name='approvals'),

    path('api/list/', views.PastorApprovals.as_view(), name='cashier_api_list'),
    path('api/list/<int:id>', views.PastorApprovals.as_view(), name='cashier_api_list_specific_campus'),
    path('api/getcampuses/', views.getcampuses, name='get-campuses'),

    # Add event fetching
    path('api/get-events/', views.load_events, name='get-events'),

    path('reports/', ReportsView.as_view(), name='reports-trip'),
    path('reports/<str:week>', ReportsView.as_view(), name='reports-trip'),

    path('<int:cashier_id>/approve/', views.approve_cashier, name='approve_cashier'),

    path('<int:cashier_id>/attendees/', views.cashier_attendees, name='cashier_attendees'),

    path('<int:id>/reject/', views.reject_cashier, name='reject-cashier'),

    path('api/get-schedules/', views.get_schedules, name='get_schedules'),
    path('verify_voucher/<int:cashier_id>/', views.verify_voucher, name='verify-voucher'),


    path('leaders/approvals_list/', views.AccountApproval.as_view(), name='account-approvals'),

    path('leaders/api/list/', views.leaders_api_list, name='accounts_api_list'),

    path('leader/<int:leader_id>/approve/', views.approve_leader, name='approve_leader'),

     path('leader/<int:id>/reject/', views.reject_leader, name='reject-leader'),


]
