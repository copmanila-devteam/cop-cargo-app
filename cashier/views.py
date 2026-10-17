import json
from bson import ObjectId
from datetime import datetime
from django.http import JsonResponse
from pymongo import MongoClient
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from pymongo.errors import ConnectionFailure, OperationFailure
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta, date
from .forms import CashierEntryForm, PassengerForm, ReportFilterForm, ReportDateRangeFilterForm
from .models import Cashier, Attendees, Matrix, ServiceSchedule, CashierImage, Voucher, CargoDetails, LeadersAttendees
from Account.auth import Usertype
from Account.models import UserType
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction # Required to fix your error
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from decimal import Decimal
from django.db.models import Count, Q
from django.utils.decorators import method_decorator
from django.utils import timezone as django_timezone
from django.http import HttpResponse
from django.core.exceptions import MultipleObjectsReturned
from datetime import date
import calendar 
from .helpers import get_image_hash
from openpyxl.worksheet.table import Table, TableStyleInfo
import openpyxl
import secrets



def page_404_view(request, exception):

    return render(request, 'error_pages/404_page.html', status=404)



def page_500_view(request):

    return render(request, 'error_pages/500_page.html', status=500)




def get_schedules(request):
    campus_id = request.GET.get('campus_id')
    # Use select_related to make the database query faster
    schedules = ServiceSchedule.objects.filter(campus_id=campus_id).select_related('campus')
    
    data = []
    for s in schedules:
        # %I:%M %p converts 15:00:00 to 03:00 PM
        formatted_time = s.time.strftime("%I:%M %p")
        
        # Construct the string: Campus | Day | Time
        # Using getattr handles cases where campus might be None
        campus_name = s.campus.name if s.campus else "Unknown Campus"
        display_text = f"{campus_name} | {s.get_days_display()} | {formatted_time}"
        
        data.append({
            'id': s.id, 
            'name': display_text
        })
        
    return JsonResponse(data, safe=False)


class BookingHistoryView(LoginRequiredMixin, TemplateView):

    template_name = 'booking_history.html'

    login_url ='login-cargo'





    def dispatch(self, request, *args, **kwargs):

        user = self.request.user



        if user.is_authenticated:

            if user.type != 'LE':

                return redirect(Usertype[user.type])

        else:

            return render(request, 'error_pages/404_page.html')



        return super().dispatch(request, *args, **kwargs)

    

    def get(self, request, *args, **kwargs):

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

            try:

                user = self.request.user

                bookings = Cashier.objects.filter(leader=user, approved_by__isnull=False).order_by('-time_arrived')

               

                booking_data = [

                    {   

                    'origin':booking.start_location.name,

                    'destination': booking.campus.name,

                    'service_schedule':str(booking.service_schedule),

                    'vehicle': booking.vehicle.name,

                    'plate_number': booking.plate_num,

                    'date_time_arrived':booking.time_arrived.astimezone().strftime('%B %d, %Y %I:%M:%S %p'),

                    'subsidy_amount':float(booking.subsidy_amount),

                    'amount_released':float(booking.amount_released), 

                        

                    } for booking in bookings

                ]

           

                return JsonResponse({'status':'success','data_entries':booking_data})

            except Exception as e:

                return JsonResponse({'status':'error', 'message':str(e)})

        else:

            return render(request, self.template_name)


class AttendeeView(LoginRequiredMixin, TemplateView):
    template_name='attendees.html'
    login_url = 'login-cargo'

    def dispatch(self, request, *args, **kwargs):

        user = self.request.user



        if user.is_authenticated:

            if user.type != 'LE':

                return redirect(Usertype[user.type])

        else:

            return render(request, 'error_pages/404_page.html')



        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                user = self.request.user
                data_items = LeadersAttendees.objects.filter(leader=user)
                attendees = [
                    {   'id': item.attendee.id,
                        'cop_id':item.attendee.cop_id if item.attendee.cop_id is not None else 'N/A',
                        'first_name': item.attendee.first_name,
                        'middle_name': item.attendee.middle_name,
                        'last_name': item.attendee.last_name,
                    }
                for item in data_items
                ]
                return JsonResponse({'Status':'Success','data_entries':attendees})
            except Exception as e:
                return JsonResponse({'Status':'Error','message':str(e)})
        else:
            form = PassengerForm()
            return render(request, self.template_name, {'form': form})
    
    def delete(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                id = int(self.kwargs.get('id'))
                attendee = Attendees.objects.get(pk=id)
                attendee.delete()
                return JsonResponse({'Status': 'Success', 'message':"Deleted successful"})

            except Exception as e:
                print(e)
                return JsonResponse({'Status':'Error', 'message':str(e)})
        else:
            form = PassengerForm()
            return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = json.loads(request.body)

            post_data = {
                'cop_id':int(data.get('cop_id').strip()) if data.get('cop_id').strip() != '' else None,
                'first_name': data.get('first_name').strip(),
                'middle_name':data.get('middle_name').strip(),
                'last_name':data.get('last_name').strip(),
            }


            form = PassengerForm(post_data)
            if form.is_valid():
                try:
                    cop_id = form.cleaned_data.get('cop_id')
                    first_name = form.cleaned_data.get('first_name')
                    middle_name = form.cleaned_data.get('middle_name')
                    last_name = form.cleaned_data.get('last_name')
                    
                    new_entry = Attendees(cop_id=cop_id, first_name=first_name, middle_name=middle_name, last_name=last_name)
                    new_entry.save()

                    if LeadersAttendees.objects.filter(leader=self.request.user,attendee__first_name=new_entry.first_name, attendee__middle_name=new_entry.middle_name,attendee__last_name=new_entry.last_name).exists():
                        return JsonResponse({'Status':'Error', 'message':f'You already added {new_entry.first_name} {new_entry.last_name}'})

                    data_entry = LeadersAttendees(leader=self.request.user,attendee=new_entry)
                    data_entry.save()
                    return JsonResponse({'Status':'Success', 'message':f"{first_name} {last_name} is successfully added"})
                except Exception as e:
                    print(e)
                    return JsonResponse({'Status':'Error', 'message':str(e)})
            else:
                return JsonResponse({'Status':'Error Fields', 'message':form.errors.get_json_data()})
        else:
            form = PassengerForm()
            return render(request, self.template_name, {'form': form})

            



class CargoView(LoginRequiredMixin, TemplateView):
    template_name = 'cargo_form.html'
    login_url = 'login-cargo'

    def dispatch(self, request, *args, **kwargs):

        user = self.request.user

        if user.is_authenticated:

            if user.type not in ['LE']:

                return redirect(Usertype[user.type])

        else:

            return render(request, 'error_pages/404_page.html')

        

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Fetch matrix data for dynamic price display
        matrix_data = list(Matrix.objects.select_related('city', 'campus', 'vehicle').values(
            'id', 'city_id', 'campus_id', 'vehicle_id', 'peso_price'
        ))
        
        # Get all attendees associated with this leader from LeadersAttendees
        leader_attendees = Attendees.objects.filter(
            leaders_attendees__leader=request.user
        ).distinct().values('id', 'first_name', 'middle_name', 'last_name', 'cop_id').order_by('first_name', 'last_name')
        
        context = {
            'form': CashierEntryForm(),
            'passenger_form': PassengerForm(),
            'matrix_prices_json': json.dumps(matrix_data, cls=DjangoJSONEncoder),
            'leader_attendees_json': json.dumps(list(leader_attendees), cls=DjangoJSONEncoder),
        }
        return render(request, self.template_name, context)
    
   
    def post(self, request, *args, **kwargs):
        data_post = request.POST.copy()
        data_post['plate_num'] = ''.join(data_post['plate_num'].strip().split())
        
        form = CashierEntryForm(data_post, request.FILES)
        files = request.FILES.getlist('photos') 
        passengers_raw = request.POST.get('passengers_data', '[]')
        
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        
        try:
            passengers_data = json.loads(passengers_raw)
           
        except json.JSONDecodeError:
            passengers_data = []

        # Validation Logic
        if form.is_valid():
            if not passengers_data:
                error_msg = 'Please add at least one passenger.'
                if is_ajax: return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                
            elif not files:
                error_msg = 'Please upload at least one photo or receipt.'
                if is_ajax: return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                
            else:
                try:
                    with transaction.atomic():
                      
                        cashier = form.save(commit=False)
                       
                        cashier.leader = request.user
                        cashier.date = date.today()
                        now = timezone.now()
                        cashier.time_arrived = now
                        
                        sched_time = cashier.service_schedule.time
                        scheduled_datetime = timezone.make_aware(
                            datetime.combine(cashier.date, sched_time)
                        )
                        
                        grace_threshold = scheduled_datetime - timedelta(minutes=15)
                        
                        try:
                            matrix_entry = Matrix.objects.get(
                                city=cashier.start_location,
                                campus=cashier.campus,
                                vehicle=cashier.vehicle
                            )
                            vehicle_price = Decimal(str(matrix_entry.peso_price))
                        except Matrix.DoesNotExist:
                            vehicle_price = Decimal('0.00')
                        

                        try:
                            total_members = LeadersAttendees.objects.filter(leader=self.request.user).count()

                        except LeadersAttendees.DoesNotExist:
                            total_members = 0
		

                        now = now.replace(second=0, microsecond=0)

                        grace_threshold = grace_threshold.replace(second=0, microsecond=0)
                    
                        if now > grace_threshold:
                            diff = now - grace_threshold
                            minutes_late = int(diff.total_seconds() // 60)
                            cashier.subsidy_amount = Decimal('0.00')
                            cashier.amount_released = Decimal('0.00')
                            status_note = f"(LATE - {minutes_late} mins)"
                        elif total_members != len(passengers_data):
                            cashier.subsidy_amount = vehicle_price
                            cashier.amount_released = vehicle_price * Decimal('0.30')
                            status_note = ""
                        else:
                            cashier.subsidy_amount = vehicle_price
                            cashier.amount_released = vehicle_price * Decimal('0.5')
                            status_note = ""

                        if status_note:
                            cashier.remarks = f"{status_note} {cashier.remarks}".strip()
                        

                        data_cashier_images = []

                        for image in files:

                            img_hash = get_image_hash(image)



                            image.seek(0)

                            is_exists = CashierImage.objects.filter(hash=img_hash, cashier__leader=self.request.user).exists()

                            if is_exists:

                                return JsonResponse({'status': 'error','message':'Duplicate Entry. You already submitted this entry'})

                            else:

                                data_cashier_images.append(CashierImage(cashier=cashier, image=image, hash=get_image_hash(image)))
                        

 

                        # Process passengers - Create/Get Attendees and LeadersAttendees
                        cargo_details_to_create = []
                        
                        for p in passengers_data:
                            cop_id_value = None if not p.get('cop_id') or p['cop_id'].strip() == '' else p['cop_id'].strip()
                            
                            
                            try:
                                
                                leader_attendee = LeadersAttendees.objects.get(attendee__first_name=p['first_name'].strip(), attendee__middle_name=p['middle_name'].strip(), attendee__last_name=p['last_name'].strip(), leader=request.user
                                )
                            except MultipleObjectsReturned:
                                error_msg = f"{p['first_name'].strip()} {p['last_name'].strip()} has a duplicate"
                                return JsonResponse({'status':'error', 'message':error_msg})
                            
                            
                              
                            cargo_details_to_create.append(
                                CargoDetails(
                                    cashier=cashier,
                                    cargo=leader_attendee
                                )
                            )                       
                        cashier.save()

                        CashierImage.objects.bulk_create(data_cashier_images)
                        CargoDetails.objects.bulk_create(cargo_details_to_create)

                        
                    
                    success_msg = 'Record stored! ' + ('Late arrival detected - no subsidy applied.' if now > grace_threshold else 'Subsidy applied.')
                    if is_ajax :
                        return JsonResponse({'status': 'success', 'message': success_msg})
                   
                    
                    messages.success(request, success_msg)
                    return redirect('cashier_entry') 

                except Exception as e:
                    error_msg = f'Database Error: {str(e)}'
                    if is_ajax: return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
                    messages.error(request, error_msg)
        else:
            # Form Field Validation Errors
            if is_ajax:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Please correct the errors in the form.',
                    'errors': form.errors
                }, status=400)
            messages.error(request, 'Please correct the errors in the form.')

        # Fallback context
        leader_attendees = Attendees.objects.filter(
            leaders_attendees__leader=request.user
        ).distinct().values('id', 'first_name', 'middle_name', 'last_name', 'cop_id').order_by('first_name', 'last_name')
        
        matrix_data = list(Matrix.objects.select_related('city', 'campus', 'vehicle').values(
            'id', 'city_id', 'campus_id', 'vehicle_id', 'peso_price'
        ))
        
        context = {
            'form': form,
            'passenger_form': PassengerForm(), 
            'passengers_json': passengers_raw,
            'leader_attendees_json': json.dumps(list(leader_attendees), cls=DjangoJSONEncoder),
            'matrix_prices_json': json.dumps(matrix_data, cls=DjangoJSONEncoder),
        }
        return render(request, self.template_name, context)



class VoucherView(LoginRequiredMixin, TemplateView):
    template_name = "vouchers.html"
    login_url = "login-cargo"


    

    def dispatch(self, request, *args, **kwargs):

        user = self.request.user

        if user.is_authenticated:

            if user.type not in ['LE']:

                return redirect(Usertype[user.type])

        else:

            return render(request, 'error_pages/404_page.html')

        return super().dispatch(request, *args, **kwargs)
    
    
    
    def get(self, request,*args, **kwargs):
        if request.headers.get('X-Requested-With') == "XMLHttpRequest":
            data_list = Voucher.objects.filter(cashier__leader=self.request.user).order_by('-cashier__time_arrived')
            json_data_list = []
            for data in data_list:
                service_schedule_data = None
                if data.cashier.service_schedule:
                    service_schedule_data = {
                        'id': data.cashier.service_schedule.id,
                        'day': data.cashier.service_schedule.get_days_display(),
                        'time': data.cashier.service_schedule.time.strftime('%H:%M:%S'),
                        'campus': {'name': data.cashier.service_schedule.campus.name} if data.cashier.service_schedule.campus else None
                    }
                json_data_list.append( {
                    'service_schedule': service_schedule_data,
                    'arrival_time':data.cashier.time_arrived.isoformat() if data.cashier.time_arrived else None,
                    'voucher':data.voucher_code,
                })

        
            return JsonResponse({'status':'success','data_entries':json_data_list})
        else:
            return render(request, self.template_name)


@require_POST

def reject_cashier(request, id):

    try:

        cashier = Cashier.objects.get(id=id)

        cashier.rejected = True

        if cashier.approved_by is None:

            cashier.save()

            return JsonResponse({'success': True, 'message': 'Request rejected successfully'})

        else:

            return JsonResponse({'success': True, 'message': 'This booking is already approved'})

    except Cashier.DoesNotExist:

        return JsonResponse({'success': False, 'message': 'Record not found'})

    except Exception as e:

        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_http_methods(["POST"])
def add_passenger(request):
    passenger_form = PassengerForm(request.POST)
    
    if passenger_form.is_valid():
        passenger_data = {
            'first_name': passenger_form.cleaned_data['first_name'],
            'middle_name': passenger_form.cleaned_data['middle_name'],
            'last_name': passenger_form.cleaned_data['last_name'],
        }
        
        # Using .get() is safer to avoid KeyErrors
        passengers = request.session.get('passengers', [])
        passengers.append(passenger_data)
        
        request.session['passengers'] = passengers
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'passengers': passengers
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': passenger_form.errors
        })



@require_http_methods(["POST"])
def remove_passenger(request, index):
    """AJAX view to remove passenger from session"""
    if 'passengers' in request.session:
        try:
            request.session['passengers'].pop(index)
            request.session.modified = True
            return JsonResponse({
                'success': True,
                'passengers': request.session['passengers']
            })
        except IndexError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid index'
            })
    
    return JsonResponse({'success': False, 'error': 'No passengers in session'})



@login_required

@require_POST

def verify_voucher(request, cashier_id):

    try:

        data = json.loads(request.body)

        voucher_input = data.get('voucher_code', '').strip()



        cashier = Cashier.objects.get(id=cashier_id)

        voucher = Voucher.objects.filter(cashier=cashier, voucher_code=voucher_input).first()



        if voucher:

            cashier.completed = True  # ✅ This sets completed to True

            cashier.save()

            return JsonResponse({'status': 'success', 'message': 'Voucher verified and marked as completed.'})

        else:

            return JsonResponse({'status': 'error', 'message': 'Invalid voucher code. Please try again.'}, status=400)



    except Cashier.DoesNotExist:

        return JsonResponse({'status': 'error', 'message': 'Entry not found.'}, status=404)

    except Exception as e:

        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



class CashierView(LoginRequiredMixin, View):
    login_url = 'login-cargo'    

    def dispatch(self, request, *args, **kwargs):

        user = self.request.user
        if user.is_authenticated:
            # Note: Assuming Usertype is a mapping defined elsewhere in your code
            if user.type not in ['FI']:
                return redirect(Usertype[user.type])

        else:
            # If the user is not authenticated, you might want to redirect them to the login page or show a 404 page. Adjust this as needed.
            redirect_url = reverse('login-cargo')  # Assuming 'login-cargo' is the name of your login URL

            # return render(request, 'error_pages/404_page.html', status=404)

        return super().dispatch(request, *args, **kwargs)



    def get(self, request, id=None, *args, **kwargs):

        if id:

            return self.get_cashier_detail(request, id)

        

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

            return self.get_cashier_list(request)

        

        form = ReportDateRangeFilterForm()

        return render(request, 'cashier_list.html', {'form': form})





    def post(self, request, id=None, *args, **kwargs):

        form = ReportDateRangeFilterForm(request.POST)



        if form.is_valid():

           

            start_date = form.cleaned_data.get('start_date')

            end_date = form.cleaned_data.get('end_date')

            user = self.request.user



            start_date_format = start_date.strftime('%B %d, %Y')

            end_date_format = end_date.strftime('%B %d, %Y')

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

          

            response['Content-Disposition'] = f'attachment; filename="Cashier Report {start_date_format} - {end_date_format}.xlsx"'

           



            cashier_data = Cashier.objects.filter(Q(date__gte=start_date) & Q(date__lte=end_date),approved_by__isnull=False).order_by('-time_arrived') if user.campus.name == 'Campus Main' else Cashier.objects.filter(Q(date__gte=start_date) & Q(date__lte=end_date), approved_by__isnull=False ,campus=user.campus).order_by('-time_arrived')



            wb = openpyxl.Workbook()

            ws = wb.active

            ws.title = 'Cashier'



            headers = ['Leader Name', 'Origin','Campus', 'Service Schedule', 'Date & Time Arrived', 'Vehicle Type','Number of Members','Subsidy Amount','Amount Released','Remarks']

            ws.append(headers)



            for row_num, cashier in enumerate(cashier_data, start=2):

                num_members = CargoDetails.objects.filter(cashier=cashier).count()

                time_arrived = cashier.time_arrived.astimezone()

                ws.append(

                    [

                        f'{cashier.leader.first_name} {cashier.leader.last_name}',

                        cashier.start_location.name,

                        cashier.campus.name,

                        str(cashier.service_schedule),

                        time_arrived.strftime('%B %d, %Y %I:%M %p'),

                        cashier.vehicle.name,

                        num_members,

                        cashier.subsidy_amount,

                        cashier.amount_released,

                        cashier.remarks,

                    ])

                ws.cell(row=row_num, column=8).number_format = '0.00'

                ws.cell(row=row_num, column=9).number_format = '0.00'

                

            tab = Table(displayName="ProjectTable", ref=f"A1:{openpyxl.utils.get_column_letter(ws.max_column)}{ws.max_row}")

            style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,

                           showLastColumn=False, showRowStripes=True, showColumnStripes=False)

            

            tab.tableStyleInfo = style

            ws.add_table(tab)

            wb.save(response)

            return response





    def get_cashier_list(self, request):
        try:
            user = self.request.user
            from django.db.models import Count

            base_qs = (
                Cashier.objects
                .select_related(
                    'leader', 'campus', 'subsidy_type', 'vehicle',
                    'start_location', 'approved_by', 'service_schedule'
                )
                .prefetch_related('images')  # leader removed from here
                .annotate(image_count=Count('images'))
                .filter(approved_by__isnull=False)
                .order_by('-time_arrived')
            )

            if user.campus.name != "Main Campus":
                base_qs = base_qs.filter(campus=user.campus)

            # Evaluate queryset once
            cashiers = list(base_qs)

            # Bulk fetch vouchers — no more N+1
            cashier_ids = [c.id for c in cashiers]
            voucher_map = {
                v.cashier_id: v.voucher_code
                for v in Voucher.objects.filter(cashier_id__in=cashier_ids)
            }

            data = []
            for i, cashier in enumerate(cashiers, start=1):
                is_late = False
                if cashier.time_arrived and cashier.service_schedule:
                    sched_dt = datetime.combine(cashier.date, cashier.service_schedule.time)
                    threshold_time = sched_dt + timedelta(minutes=15)
                    arrival = cashier.time_arrived
                    if timezone.is_aware(arrival):
                        arrival = timezone.make_naive(arrival)
                    is_late = arrival > threshold_time

                data_date_time_arrived = cashier.time_arrived.astimezone()
                data.append({
                    'id': cashier.id,
                    'row_num': i,
                    'leader': {
                        'id': cashier.leader.id,
                        'first_name': cashier.leader.first_name,
                        'last_name': cashier.leader.last_name,
                    } if cashier.leader else None,
                    'date': cashier.date.isoformat() if cashier.date else None,
                    'campus': {
                        'id': cashier.campus.id,
                        'name': cashier.campus.name
                    } if cashier.campus else None,
                    'vehicle': {
                        'id': cashier.vehicle.id,
                        'name': cashier.vehicle.name,
                        'price': float(cashier.vehicle.peso_price)
                    } if cashier.vehicle else None,
                    'subsidy_amount': float(cashier.subsidy_amount),
                    'date_time_arrived': data_date_time_arrived.strftime('%B %d, %Y %I:%M:%S %p'),
                    'amount_released': float(cashier.amount_released),
                    'voucher': voucher_map.get(cashier.id, 'N/A'),
                    'is_late': is_late,
                    'remarks': cashier.remarks,
                    'image_count': cashier.image_count,  # from annotation
                    'completed': cashier.completed,
                })
            return JsonResponse({'status': 'success', 'count': len(data), 'data': data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

 
   
                    

                  

    

    def get_cashier_detail(self, request, id):

        """Unchanged detailed view logic..."""

        # (This remains largely as you provided but ensures consistency with calculations)

        try:

            cashier = Cashier.objects.select_related(

                'leader', 'start_location','campus', 'subsidy_type', 'vehicle', 

                'start_location', 'approved_by', 'service_schedule'

            ).prefetch_related('leader', 'images').get(id=id)





            cargo_items = CargoDetails.objects.filter(cashier=cashier, cargo__leader=cashier.leader)

            try:

                voucher = Voucher.objects.get(cashier=cashier)

                voucher = voucher.voucher_code

            except Exception as e:

                voucher = 'N/A'



            is_late = False

            if cashier.time_arrived and cashier.service_schedule:

                sched_dt = datetime.combine(cashier.date, cashier.service_schedule.time)

                threshold = sched_dt - timedelta(minutes=15)

                arrival = timezone.make_naive(cashier.time_arrived) if timezone.is_aware(cashier.time_arrived) else cashier.time_arrived

                if arrival > threshold:

                    is_late = True



            service_schedule_data = None

            if cashier.service_schedule:

                service_schedule_data = {

                    'id': cashier.service_schedule.id,

                    'day': cashier.service_schedule.get_days_display(),

                    'time': cashier.service_schedule.time.strftime('%H:%M:%S'),

                    'campus': {'name': cashier.service_schedule.campus.name} if cashier.service_schedule.campus else None

                }



            detail_data = {

                'id': cashier.id,

                'leader': {'first_name': cashier.leader.first_name, 'last_name': cashier.leader.last_name} if cashier.leader else None,

                'date': cashier.date.isoformat() if cashier.date else None,

                'start_location': {'name': cashier.start_location.name} if cashier.start_location else None,

                'campus': {'name': cashier.campus.name} if cashier.campus else None,

                'vehicle': {'name': cashier.vehicle.name} if cashier.vehicle else None,

                'subsidy_type': {'name': cashier.subsidy_type.name} if cashier.subsidy_type else None,

                'service_schedule': service_schedule_data,

                'plate_num': cashier.plate_num,

                'subsidy_amount': float(cashier.subsidy_amount),

                'amount_released': float(cashier.amount_released),

                'is_late': is_late,

                'rejected': cashier.rejected,

                'voucher': voucher,

                'remarks': cashier.remarks,

                'time_arrived': cashier.time_arrived.isoformat() if cashier.time_arrived else None,

                'images': [{'url': request.build_absolute_uri(img.image.url), 'uploaded_at': img.uploaded_at.isoformat()} for img in cashier.images.all()],

                'users': [

                    {

                        'first_name': u.cargo.attendee.first_name, 

                        'middle_name': u.cargo.attendee.middle_name,

                        'last_name': u.cargo.attendee.last_name,

                        'cop_id':'N/A' if u.cargo.attendee.cop_id is None else u.cargo.attendee.cop_id,

                    } for u in cargo_items

                ],

            }

            return JsonResponse({'status': 'success', 'data': detail_data})

        except Cashier.DoesNotExist:

            return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)     





class AccountingView(LoginRequiredMixin, View):
    login_url = 'login-cargo'    

    def dispatch(self, request, *args, **kwargs):

        user = self.request.user
        if user.is_authenticated:
            # Note: Assuming Usertype is a mapping defined elsewhere in your code
            if user.type not in ['ACNT']:
                return redirect(Usertype[user.type])

        else:
            # If the user is not authenticated, you might want to redirect them to the login page or show a 404 page. Adjust this as needed.
            redirect_url = reverse('login-cargo')  # Assuming 'login-cargo' is the name of your login URL

            # return render(request, 'error_pages/404_page.html', status=404)

        return super().dispatch(request, *args, **kwargs)



    def get(self, request, id=None, *args, **kwargs):

        if id:

            return self.get_cashier_detail(request, id)

        

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

            return self.get_cashier_list(request)

        

        form = ReportDateRangeFilterForm()

        return render(request, 'Accountant/index.html', {'form': form})





    def post(self, request, id=None, *args, **kwargs):

        form = ReportDateRangeFilterForm(request.POST)



        if form.is_valid():

           

            start_date = form.cleaned_data.get('start_date')

            end_date = form.cleaned_data.get('end_date')

            user = self.request.user



            start_date_format = start_date.strftime('%B %d, %Y')

            end_date_format = end_date.strftime('%B %d, %Y')

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

          

            response['Content-Disposition'] = f'attachment; filename="Cashier Report {start_date_format} - {end_date_format}.xlsx"'

           



            cashier_data = Cashier.objects.filter(Q(date__gte=start_date) & Q(date__lte=end_date),approved_by__isnull=False).order_by('-time_arrived') if user.campus.name == 'Campus Main' else Cashier.objects.filter(Q(date__gte=start_date) & Q(date__lte=end_date), approved_by__isnull=False ,campus=user.campus).order_by('-time_arrived')



            wb = openpyxl.Workbook()

            ws = wb.active

            ws.title = 'Cashier'



            headers = ['Leader Name', 'Origin','Campus', 'Service Schedule', 'Date & Time Arrived', 'Vehicle Type','Number of Members','Subsidy Amount','Amount Released','Remarks']

            ws.append(headers)



            for row_num, cashier in enumerate(cashier_data, start=2):

                num_members = CargoDetails.objects.filter(cashier=cashier).count()

                time_arrived = cashier.time_arrived.astimezone()

                ws.append(

                    [

                        f'{cashier.leader.first_name} {cashier.leader.last_name}',

                        cashier.start_location.name,

                        cashier.campus.name,

                        str(cashier.service_schedule),

                        time_arrived.strftime('%B %d, %Y %I:%M %p'),

                        cashier.vehicle.name,

                        num_members,

                        cashier.subsidy_amount,

                        cashier.amount_released,

                        cashier.remarks,

                    ])

                ws.cell(row=row_num, column=8).number_format = '0.00'

                ws.cell(row=row_num, column=9).number_format = '0.00'

                

            tab = Table(displayName="ProjectTable", ref=f"A1:{openpyxl.utils.get_column_letter(ws.max_column)}{ws.max_row}")

            style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,

                           showLastColumn=False, showRowStripes=True, showColumnStripes=False)

            

            tab.tableStyleInfo = style

            ws.add_table(tab)

            wb.save(response)

            return response





    def get_cashier_list(self, request):
        try:
            user = self.request.user
            from django.db.models import Count

            base_qs = (
                Cashier.objects
                .select_related(
                    'leader', 'campus', 'subsidy_type', 'vehicle',
                    'start_location', 'approved_by', 'service_schedule'
                )
                .prefetch_related('images')  # leader removed from here
                .annotate(image_count=Count('images'))
                .filter(approved_by__isnull=False)
                .order_by('-time_arrived')
            )

            if user.campus.name != "Main Campus":
                base_qs = base_qs.filter(campus=user.campus)

            # Evaluate queryset once
            cashiers = list(base_qs)

            # Bulk fetch vouchers — no more N+1
            cashier_ids = [c.id for c in cashiers]
            voucher_map = {
                v.cashier_id: v.voucher_code
                for v in Voucher.objects.filter(cashier_id__in=cashier_ids)
            }

            data = []
            for i, cashier in enumerate(cashiers, start=1):
                is_late = False
                if cashier.time_arrived and cashier.service_schedule:
                    sched_dt = datetime.combine(cashier.date, cashier.service_schedule.time)
                    threshold_time = sched_dt + timedelta(minutes=15)
                    arrival = cashier.time_arrived
                    if timezone.is_aware(arrival):
                        arrival = timezone.make_naive(arrival)
                    is_late = arrival > threshold_time

                data_date_time_arrived = cashier.time_arrived.astimezone()
                data.append({
                    'id': cashier.id,
                    'row_num': i,
                    'leader': {
                        'id': cashier.leader.id,
                        'first_name': cashier.leader.first_name,
                        'last_name': cashier.leader.last_name,
                    } if cashier.leader else None,
                    'date': cashier.date.isoformat() if cashier.date else None,
                    'campus': {
                        'id': cashier.campus.id,
                        'name': cashier.campus.name
                    } if cashier.campus else None,
                    'vehicle': {
                        'id': cashier.vehicle.id,
                        'name': cashier.vehicle.name,
                        'price': float(cashier.vehicle.peso_price)
                    } if cashier.vehicle else None,
                    'subsidy_amount': float(cashier.subsidy_amount),
                    'date_time_arrived': data_date_time_arrived.strftime('%B %d, %Y %I:%M:%S %p'),
                    'amount_released': float(cashier.amount_released),
                    'voucher': voucher_map.get(cashier.id, 'N/A'),
                    'is_late': is_late,
                    'remarks': cashier.remarks,
                    'image_count': cashier.image_count,  # from annotation
                    'completed': cashier.completed,
                })
            return JsonResponse({'status': 'success', 'count': len(data), 'data': data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

 
   
                    

                  

    

    def get_cashier_detail(self, request, id):

        """Unchanged detailed view logic..."""

        # (This remains largely as you provided but ensures consistency with calculations)

        try:

            cashier = Cashier.objects.select_related(

                'leader', 'start_location','campus', 'subsidy_type', 'vehicle', 

                'start_location', 'approved_by', 'service_schedule'

            ).prefetch_related('leader', 'images').get(id=id)





            cargo_items = CargoDetails.objects.filter(cashier=cashier, cargo__leader=cashier.leader)

            try:

                voucher = Voucher.objects.get(cashier=cashier)

                voucher = voucher.voucher_code

            except Exception as e:

                voucher = 'N/A'



            is_late = False

            if cashier.time_arrived and cashier.service_schedule:

                sched_dt = datetime.combine(cashier.date, cashier.service_schedule.time)

                threshold = sched_dt - timedelta(minutes=15)

                arrival = timezone.make_naive(cashier.time_arrived) if timezone.is_aware(cashier.time_arrived) else cashier.time_arrived

                if arrival > threshold:

                    is_late = True



            service_schedule_data = None

            if cashier.service_schedule:

                service_schedule_data = {

                    'id': cashier.service_schedule.id,

                    'day': cashier.service_schedule.get_days_display(),

                    'time': cashier.service_schedule.time.strftime('%H:%M:%S'),

                    'campus': {'name': cashier.service_schedule.campus.name} if cashier.service_schedule.campus else None

                }



            detail_data = {

                'id': cashier.id,

                'leader': {'first_name': cashier.leader.first_name, 'last_name': cashier.leader.last_name} if cashier.leader else None,

                'date': cashier.date.isoformat() if cashier.date else None,

                'start_location': {'name': cashier.start_location.name} if cashier.start_location else None,

                'campus': {'name': cashier.campus.name} if cashier.campus else None,

                'vehicle': {'name': cashier.vehicle.name} if cashier.vehicle else None,

                'subsidy_type': {'name': cashier.subsidy_type.name} if cashier.subsidy_type else None,

                'service_schedule': service_schedule_data,

                'plate_num': cashier.plate_num,

                'subsidy_amount': float(cashier.subsidy_amount),

                'amount_released': float(cashier.amount_released),

                'is_late': is_late,

                'rejected': cashier.rejected,

                'voucher': voucher,

                'remarks': cashier.remarks,

                'time_arrived': cashier.time_arrived.isoformat() if cashier.time_arrived else None,

                'images': [{'url': request.build_absolute_uri(img.image.url), 'uploaded_at': img.uploaded_at.isoformat()} for img in cashier.images.all()],

                'users': [

                    {

                        'first_name': u.cargo.attendee.first_name, 

                        'middle_name': u.cargo.attendee.middle_name,

                        'last_name': u.cargo.attendee.last_name,

                        'cop_id':'N/A' if u.cargo.attendee.cop_id is None else u.cargo.attendee.cop_id,

                    } for u in cargo_items

                ],

            }

            return JsonResponse({'status': 'success', 'data': detail_data})

        except Cashier.DoesNotExist:

            return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)     


@login_required
@require_POST
def update_remarks(request, pk):
    try:
        # 1. Get the entry
        entry = get_object_or_404(Cashier, pk=pk)
        
        # 2. Parse JSON data
        data = json.loads(request.body)
        remarks_text = data.get('remarks', '')
        
        # 3. Update and Save
        entry.remarks = remarks_text
        entry.save()
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Remarks updated successfully'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def update_amount(request, pk):
    try:
        # 1. Get the entry
        entry = get_object_or_404(Cashier, pk=pk)
        
        # 2. Parse JSON data
        data = json.loads(request.body)
        new_amount = data.get('amount_released')
        
        if new_amount is not None:
            # 3. Update fields
            entry.amount_released = float(new_amount)
            
            # Automatically set the cashier who approved this release
            # Assuming request.user is linked to your UserType model
            if hasattr(request.user, 'usertype'):
                entry.approved_by = request.user.usertype
            
            # (Optional) Update subsidy_amount based on vehicle price if not set
            if entry.subsidy_amount == 0 and entry.vehicle:
                entry.subsidy_amount = entry.vehicle.peso_price
                
            entry.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Amount ₱{new_amount} released and approved.'
            })
            
        return JsonResponse({'status': 'error', 'message': 'No amount provided'}, status=400)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid number format'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)




class cashier_list(LoginRequiredMixin,TemplateView):

    login_url = 'login-cargo'

    template_name = 'Pastor/approvals.html'



    def dispatch(self, request, *args, **kwargs):

        user = self.request.user

      

        if user.is_authenticated:

          

            if user.type not in ['PTR']:

                return redirect(Usertype[user.type])

           

        return super().dispatch(request, *args, **kwargs)





    def get(self, request, id=None, *args, **kwargs):

        

        return render(request, self.template_name)

                 
   
        



class PastorApprovals(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated:
          
            if user.type not in ['PTR']:
                return redirect(Usertype[user.type])
           
        return super().dispatch(request, *args, **kwargs)
    

    def get(self, request, *args, **kwargs):
        """API endpoint to get list of cashiers as JSON"""
        try:
            # Get all cashiers for stats
            id = kwargs.get('id')
            if id:
                 all_cashiers = Cashier.objects.select_related(
                    'start_location', 
                    'campus', 
                    'vehicle', 
                    'approved_by',
                    'leader'
                ).prefetch_related('images', 'leader').filter(campus__id=id)
            else:
                all_cashiers = Cashier.objects.select_related(
                    'start_location', 
                    'campus', 
                    'vehicle', 
                    'approved_by',
                    'leader'
                ).prefetch_related('images', 'leader').all()
            
            
            pending_cashiers = all_cashiers.filter(approved_by__isnull=True, rejected=False).order_by('-time_arrived')
            

            cashiers_data = []
            for row_num, cashier in enumerate(pending_cashiers, start=1):
                # Get all images for this cashier
                images = cashier.images.all()
                image_urls = [img.image.url for img in images] if images.exists() else []
        
                cargo_items = CargoDetails.objects.filter(cashier=cashier,cargo__leader=cashier.leader)
                
                users_list = [
                    {
                        'id': item.cargo.attendee.id,
                        'cop_id': 'N/A' if item.cargo.attendee.cop_id is None else item.cargo.attendee.cop_id,
                        'first_name': item.cargo.attendee.first_name,
                        'middle_name':item.cargo.attendee.middle_name,
                        'last_name': item.cargo.attendee.last_name,
                        'full_name': f"{item.cargo.attendee.first_name} {item.cargo.attendee.middle_name} {item.cargo.attendee.last_name}"
                    } 
                    for item in cargo_items
                ]

                
                # Format time_arrived to match server timezone
                time_arrived_str = None
                if cashier.time_arrived:
                    # If USE_TZ is True, convert to local timezone
                    if django_timezone.is_aware(cashier.time_arrived):
                        local_time = django_timezone.localtime(cashier.time_arrived)
                        time_arrived_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        time_arrived_str = cashier.time_arrived.strftime('%Y-%m-%d %H:%M:%S')
                
                cashiers_data.append({
                    'id': cashier.id,
                    'row_num':row_num,
                    'date_time_arrived': local_time.strftime('%B %d, %Y %I:%M:%S %p'),
                    'time_arrived': cashier.time_arrived.strftime('%B %d, %Y %I:%M:%S %p'),
                    'leader_first_name': cashier.leader.first_name,
                    'leader_last_name': cashier.leader.last_name,
                    'date': cashier.date.strftime('%Y-%m-%d'),
                    'start_location': str(cashier.start_location) if cashier.start_location else None,
                    'campus':str(cashier.campus) if cashier.campus else None,
		    'capacity':str(cashier.capacity) if cashier.capacity else None,
                    'vehicle':str(cashier.vehicle) if cashier.vehicle else None,
                    'plate_num': cashier.plate_num,
                    'subsidy_type': str(cashier.subsidy_type) if cashier.subsidy_type else None,
                    'service_schedule': str(cashier.service_schedule) if cashier.service_schedule else None,
                    'time_arrived': time_arrived_str,
                    'remarks': cashier.remarks,
                    'approved_by': f"{cashier.approved_by.first_name} {cashier.approved_by.last_name}" if cashier.approved_by else None,
                    'images': image_urls,
                    'photo_url': image_urls[0] if image_urls else None,
		    'users':users_list,
                    'users_count':len(users_list)
		})
                        # Calculate stats
            total_count = all_cashiers.count()
            approved_count = all_cashiers.filter(approved_by__isnull=False).count()
            pending_count = pending_cashiers.count()
            
            response_data = {
                'cashiers': cashiers_data,
                'stats': {
                    'total': total_count,
                    'approved': approved_count,
                    'pending': pending_count
                }
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'error': str(e),
                'detail': traceback.format_exc()
            }, status=500)


def generate_voucher(length=7):

    alpha_caps = 'ABCDEFGHJKLMNPQRSTUVWXYZ'

    chars = f"{alpha_caps.lower()}123456789"

    

    # Try up to 10 times, then fail gracefully

    for _ in range(10):

        code = ''.join(secrets.choice(chars) for _ in range(length))

        if not Voucher.objects.filter(voucher_code=code).exists():

            return code

            

    raise Exception("Could not generate a unique voucher code after 10 attempts.")



@login_required

@require_POST

def approve_cashier(request, cashier_id):

    try:



        try:

            cashier = Cashier.objects.get(pk=cashier_id, rejected=False)

        except Cashier.DoesNotExist:

            return JsonResponse({'status':'error', 'message':'Data not found'})



        if cashier.approved_by:

            return JsonResponse({

                'error': 'This cashier entry is already approved.'

            }, status=400)

        

        code = generate_voucher(7)

    

        voucher_data = Voucher(voucher_code=code,cashier=cashier)

        voucher_data.save()



        cashier.approved_by = request.user

        if cashier.rejected != True:

            cashier.save()

        else:

            return JsonResponse({

            'success': True,

            'approved_by': str(request.user),

            'message': 'Cashier entry is already rejected.'

        })



        return JsonResponse({

            'success': True,

            'approved_by': str(request.user),

            'message': 'Cashier entry approved successfully.'

        })

        

    except Exception as e:

        print(f'Errpr:{e}')

        return JsonResponse({

            'error': str(e)

        }, status=500)


@login_required
@require_GET
def cashier_attendees(request, cashier_id):
    """API endpoint to get attendees for a specific cashier"""
    try:
        cashier = get_object_or_404(Cashier, id=cashier_id)
        
        # Get all attendees for this cashier
        attendees = cashier.users.all()
        
        attendees_data = []
        for attendee in attendees:
            attendees_data.append({
                'id': attendee.id,
                'name': f"{attendee.first_name} {attendee.last_name}",
                'email': attendee.email if hasattr(attendee, 'email') else None,
                'phone': attendee.phone if hasattr(attendee, 'phone') else None,
            })
        
        return JsonResponse({
            'attendees': attendees_data
        })
        
    except Exception as e:
        import traceback
      
        return JsonResponse({
            'error': str(e)
        }, status=500)
    






class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'Pastor/approval_history.html'
    login_url = 'login-cargo'

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user

        if user.is_authenticated:
            if user.type != 'PTR':
                return redirect(Usertype[user.type])
        else:
            return render(request, 'error_pages/404_page.html')

        return super().dispatch(request, *args, **kwargs)

    def _get_date_range_from_week(self, week_str):
        week_num = int(week_str.split(' ')[1])
        year = datetime.now().year

        jan1 = date(year, 1, 1)
        # weekday(): Monday=0, Wednesday=2
        # Roll BACK to the nearest Wednesday on or before Jan 1
        days_since_wednesday = (jan1.weekday() - 2) % 7
        first_week_start = jan1 - timedelta(days=days_since_wednesday)

        start_date = first_week_start + timedelta(weeks=week_num - 1)
        end_date = start_date + timedelta(days=6)  # Wednesday to Tuesday

        return start_date, end_date


    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                week = kwargs.get('week')
                if not week:
                    return JsonResponse({'status': 'error', 'message': 'Week parameter is required.'})

                start_date, end_date = self._get_date_range_from_week(str(week))
                user = self.request.user

                bookings = (
                    Cashier.objects.filter(
                        Q(date__gte=start_date) & Q(date__lte=end_date),
                        approved_by__isnull=False
                    ).order_by('-time_arrived')
                    if user.campus.name == 'Main Campus'
                    else Cashier.objects.filter(
                        Q(date__gte=start_date) & Q(date__lte=end_date),
                        approved_by__isnull=False,
                        campus=user.campus
                    ).order_by('-time_arrived')
                )

                booking_data = []

                for row_num, booking in enumerate(bookings, start=1):
                    images = booking.images.all()
                    image_urls = [img.image.url for img in images] if images.exists() else []

                    cargo_items = CargoDetails.objects.filter(
                        cashier=booking, cargo__leader=booking.leader
                    )

                    users_list = [
                        {
                            'id': item.cargo.attendee.id,
                            'cop_id': 'N/A' if item.cargo.attendee.cop_id is None else item.cargo.attendee.cop_id,
                            'first_name': item.cargo.attendee.first_name,
                            'middle_name': item.cargo.attendee.middle_name,
                            'last_name': item.cargo.attendee.last_name,
                            'full_name': f"{item.cargo.attendee.first_name} {item.cargo.attendee.middle_name} {item.cargo.attendee.last_name}"
                        }
                        for item in cargo_items
                    ]

                    time_arrived_str = None
                    local_time = None
                    if booking.time_arrived:
                        if django_timezone.is_aware(booking.time_arrived):
                            local_time = django_timezone.localtime(booking.time_arrived)
                            time_arrived_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            local_time = booking.time_arrived
                            time_arrived_str = booking.time_arrived.strftime('%Y-%m-%d %H:%M:%S')

                    data_details = {
                        'id': booking.id,
                        'row_num': row_num,
                        'date_time_arrived': local_time.strftime('%B %d, %Y %I:%M:%S %p') if local_time else None,
                        'time_arrived': time_arrived_str,
                        'leader_first_name': booking.leader.first_name,
                        'leader_last_name': booking.leader.last_name,
                        'date': booking.date.strftime('%Y-%m-%d'),
                        'start_location': str(booking.start_location) if booking.start_location else None,
                        'campus': str(booking.campus) if booking.campus else None,
                        'vehicle': str(booking.vehicle) if booking.vehicle else None,
                        'plate_num': booking.plate_num,
                        'subsidy_type': str(booking.subsidy_type) if booking.subsidy_type else None,
                        'service_schedule': str(booking.service_schedule) if booking.service_schedule else None,
                        'remarks': booking.remarks,
                        'approved_by': f"{booking.approved_by.first_name} {booking.approved_by.last_name}" if booking.approved_by else None,
                        'images': image_urls,
                        'photo_url': image_urls[0] if image_urls else None,
                        'users': users_list,
                        'users_count': len(users_list)
                    }
                    booking_data.append(data_details)

                pending_cashiers = Cashier.objects.filter(approved_by__isnull=True, rejected=False).count()
                total_count = len(booking_data)
                approved_count = Cashier.objects.filter(approved_by__isnull=False).count()

                return JsonResponse({
                    'status': 'success',
                    'cashiers': booking_data,
                    'stats': {
                        'total': total_count,
                        'approved': approved_count,
                        'pending': pending_cashiers,
                    }
                })

            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
        else:
            form = ReportFilterForm()
            return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = ReportFilterForm(request.POST)

        if form.is_valid():
            week = form.cleaned_data.get('week')
            start_date, end_date = self._get_date_range_from_week(str(week))

            user = self.request.user
            year = datetime.now().year

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = (
                f'attachment; filename="Cargo Report {year} - {week}.xlsx"'
            )

            cashier_data = (
                Cashier.objects.filter(
                    Q(date__gte=start_date) & Q(date__lte=end_date),
                    approved_by__isnull=False
                ).order_by('-time_arrived')
                if user.campus.name == 'Main Campus'
                else Cashier.objects.filter(
                    Q(date__gte=start_date) & Q(date__lte=end_date),
                    approved_by__isnull=False,
                    campus=user.campus
                ).order_by('-time_arrived')
            )

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Cashier'

            headers = [
                'Leader Name', 'Origin', 'Campus', 'Service Schedule',
                'Date & Time Arrived', 'Vehicle Type', 'Number of Members',
                'Subsidy Amount', 'Amount Released', 'Remarks'
            ]
            ws.append(headers)

            for row_num, cashier in enumerate(cashier_data, start=2):
                num_members = CargoDetails.objects.filter(cashier=cashier).count()
                time_arrived = cashier.time_arrived.astimezone()
                ws.append([
                    f'{cashier.leader.first_name} {cashier.leader.last_name}',
                    cashier.start_location.name,
                    cashier.campus.name,
                    str(cashier.service_schedule),
                    time_arrived.strftime('%B %d, %Y %I:%M %p'),
                    cashier.vehicle.name,
                    num_members,
                    cashier.subsidy_amount,
                    cashier.amount_released,
                    cashier.remarks,
                ])
                ws.cell(row=row_num, column=8).number_format = '0.00'
                ws.cell(row=row_num, column=9).number_format = '0.00'

            tab = Table(
                displayName="ProjectTable",
                ref=f"A1:{openpyxl.utils.get_column_letter(ws.max_column)}{ws.max_row}"
            )
            style = TableStyleInfo(
                name="TableStyleMedium9",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False
            )
            tab.tableStyleInfo = style
            ws.add_table(tab)
            wb.save(response)
            return response
        
    
     



class AccountApproval(LoginRequiredMixin,TemplateView):

    login_url = 'login-cargo'

    template_name = 'Pastor/account_approvals.html'





    def dispatch(self, request, *args, **kwargs):

        user = self.request.user

      

        if user.is_authenticated:

          

            if user.type not in ['PTR']:

                return redirect(Usertype[user.type])

        return super().dispatch(request, *args, **kwargs)



    def get(self, request, id=None, *args, **kwargs):

        

        form = ReportFilterForm()

       

        return render(request, self.template_name, {'form':form})

    



    def post(self, request, *args, **kwargs):

        form = ReportFilterForm(request.POST)



        if form.is_valid():

            start_date = form.cleaned_data.get('start_date')

            end_date = form.cleaned_data.get('end_date')

            user = self.request.user



            start_date_format = start_date.strftime('%B %d, %Y')

            end_date_format = end_date.strftime('%B %d, %Y')

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

          

            response['Content-Disposition'] = f'attachment; filename="Leader Account Report {start_date_format} - {end_date_format}.xlsx"'



            account_data = UserType.objects.filter(Q(date_approved__gte=start_date) & Q(date_approved__lte=end_date),is_active_leader=True, date_approved__isnull=False).order_by('-date_approved')

            wb = openpyxl.Workbook()

            ws = wb.active

            ws.title = 'Accounts'



            headers = ['Go Group ID', 'First Name','Last Name', 'Email', 'Date Approved']

            ws.append(headers)



            for account in account_data:

                ws.append(

                    [   account.go_group_id,

                        account.first_name,

                        account.last_name,

                        account.email, 

                        account.date_approved.strftime('%B %d, %Y'),

                    ])

             

                

            tab = Table(displayName="ProjectTable", ref=f"A1:{openpyxl.utils.get_column_letter(ws.max_column)}{ws.max_row}")

            style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,

                           showLastColumn=False, showRowStripes=True, showColumnStripes=False)

            

            tab.tableStyleInfo = style

            ws.add_table(tab)

            wb.save(response)

            return response




   

@login_required

@require_GET

def leaders_api_list(request):

    """API endpoint to get list of cashiers as JSON"""

    try:

        pending_leaders = UserType.objects.filter(type='LE',is_active_leader=False,is_active=True)





    

        leaders_data = []

        for leader in pending_leaders:

          

  



            leaders_data.append({

                'id': leader.id,

                'go_group_id': leader.go_group_id,

                'first_name': leader.first_name,

                'last_name': leader.last_name,

                'email': leader.email,

            })

        

        counts = UserType.objects.filter(type='LE').aggregate(

        approved=Count('id', filter=Q(is_active_leader=True)),

        pending=Count('id', filter=Q(is_active_leader=False)),

        total=Count('id', filter=Q(is_active_leader=False) or Q(is_active_leader=True)))



        approved_count = counts['approved']

        pending_count = counts['pending']

        total_count = counts['total']

        

        response_data = {

            'leaders': leaders_data,

            'stats': {

                'total': total_count,

                'approved': approved_count,

                'pending': pending_count

            }

        }

        

        return JsonResponse(response_data)

        

    except Exception as e:

        import traceback

        return JsonResponse({

            'error': str(e),

            'detail': traceback.format_exc()

        }, status=500)

    

    



@login_required
@require_POST
def approve_leader(request, leader_id):
    """Approve a cashier entry"""
    try:
        leader_account = UserType.objects.get(id=leader_id)
        
        leader_account.is_active_leader = True
        leader_account.date_approved = timezone.now()
        leader_account.save()
        
        return JsonResponse({
            'success': True,
            'approved_by': str(request.user),
            'message': 'Cashier entry approved successfully.'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)



@require_POST
def reject_leader(request, id):
    try:
        account = UserType.objects.get(id=id)
        account.is_active = False
        account.is_active_leader = False
        account.save()
        return JsonResponse({'success': True, 'message': 'Request rejected successfully'})
    except Cashier.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    


@login_required
def getcampuses(request):
    try:
        user = request.user
        return JsonResponse({'status':'success', 'campus':user.campus.name,'id': user.campus.id})
    except Exception as e:
        return JsonResponse({'status':'error', 'message':str(e)})
