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
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta, date
from .forms import CashierEntryForm, PassengerForm
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
import secrets
from datetime import date 


from django.http import JsonResponse

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




class AttendeeView(LoginRequiredMixin, TemplateView):
    template_name='attendees.html'
    login_url = 'login-cargo'

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user

        if user.is_authenticated:
            if user.type != 'LE':
                return redirect(Usertype[user.type])

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
    
    # def get(self, request, *args, **kwargs):
    #     # Fetch matrix data for dynamic price display
    #     matrix_data = list(Matrix.objects.select_related('city', 'campus', 'vehicle').values(
    #         'id', 'city_id', 'campus_id', 'vehicle_id', 'peso_price'
    #     ))
        
       
    #     leader_attendees = Attendees.objects.filter(
    #         cashier_entries__leader=request.user
    #     ).distinct().values('id', 'first_name', 'middle_name', 'last_name','cop_id').order_by('first_name', 'last_name')
        
    #     context = {
    #         'form': CashierEntryForm(),
    #         'passenger_form': PassengerForm(),
    #         'matrix_prices_json': json.dumps(matrix_data, cls=DjangoJSONEncoder),
    #         'leader_attendees_json': json.dumps(list(leader_attendees), cls=DjangoJSONEncoder),
    #     }
    #     return render(request, self.template_name, context)
    
    

    def post(self, request, *args, **kwargs):
        form = CashierEntryForm(request.POST, request.FILES)
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
                error_msg = 'Please add at least one passenger to the manifest.'
                if is_ajax: return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                
            elif not files:
                error_msg = 'Please upload at least one photo or receipt.'
                if is_ajax: return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                
            else:
                try:
                    with transaction.atomic():
                        # Save the main cashier record
                        cashier = form.save(commmit=False)
			

                        cashier.leader = request.user
                        cashier.date = date.today()
                        cashier.plate_num =cashier.plate_num.strip() if " " not in cashier.plate_num.strip() else ''.join(cashier.plate_num.strip().split())
                        # Late Detection & Financials
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

                        cashier.save()

                        # Save images
                        CashierImage.objects.bulk_create([
                            CashierImage(cashier=cashier, image=f) for f in files
                        ])

                        # Process passengers - Create/Get Attendees and LeadersAttendees
                        cargo_details_to_create = []
                        
                        for p in passengers_data:
                            cop_id_value = None if not p.get('cop_id') or p['cop_id'].strip() == '' else p['cop_id'].strip()
                            
                            # Step 1: Get or create the Attendee
                            attendee, created = Attendees.objects.get_or_create(
                                cop_id=cop_id_value,
                                first_name=p['first_name'].strip(),
                                middle_name=p['middle_name'].strip(),
                                last_name=p['last_name'].strip(),
                            )
                            
                            # Step 2: Get or create LeadersAttendees (linking leader with attendee)
                            leader_attendee, created = LeadersAttendees.objects.get_or_create(
                                attendee=attendee,
                                leader=request.user
                            )
                            
                           
                            cargo_details_to_create.append(
                                CargoDetails(
                                    cashier=cashier,
                                    cargo=leader_attendee
                                )
                            )
                        
                        # Bulk create all CargoDetails records
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
        return super().dispatch(request, *args, **kwargs)
    
    
    
    def get(self, request,*args, **kwargs):
        if request.headers.get('X-Requested-With') == "XMLHttpRequest":
            data_list = Voucher.objects.filter(cashier__leader=self.request.user)
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
        cashier.save()
        return JsonResponse({'success': True, 'message': 'Request rejected successfully'})
    except Cashier.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Record not found'}, status=404)
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



class CashierView(LoginRequiredMixin, View):
    login_url = 'login-cargo'
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated:
            # Note: Assuming Usertype is a mapping defined elsewhere in your code
            if user.type not in ['FI']:
                return redirect(Usertype[user.type])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, id=None, *args, **kwargs):
        if id:
            return self.get_cashier_detail(request, id)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.get_cashier_list(request)
        
        return render(request, 'cashier_list.html')

    def post(self, request, id=None, *args, **kwargs):
        """
        Handles updates for Remarks and Amount Released.
        Expects 'action' and corresponding data in POST request.
        """
        if not id:
            return JsonResponse({'status': 'error', 'message': 'ID required'}, status=400)
            
        try:
            cashier = Cashier.objects.get(id=id)
            action = request.POST.get('action')

            if action == 'update_remarks':
                cashier.remarks = request.POST.get('remarks', '')
                cashier.save()
                return JsonResponse({'status': 'success', 'message': 'Remarks updated successfully'})

            elif action == 'update_amount':
                amount = request.POST.get('amount_released')
                # Optional: Add validation logic here
                cashier.amount_released = amount
                cashier.save()
                return JsonResponse({'status': 'success', 'message': 'Amount released updated'})

            return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

        except Cashier.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Entry not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


    def get_cashier_list(self, request):
        try:
            cashiers = Cashier.objects.select_related(
                'leader', 'campus', 'subsidy_type', 'vehicle', 
                'start_location', 'approved_by', 'service_schedule'
            ).prefetch_related('leader', 'images').filter(
                approved_by__isnull=False
            ).all()
            
            data = []
            for cashier in cashiers:
              
                is_late = False
                if cashier.time_arrived and cashier.service_schedule:
                    # Combine date and schedule time
                    sched_dt = datetime.combine(cashier.date, cashier.service_schedule.time)
                    # Threshold is Schedule Time + 15 minutes grace period
                    threshold_time = sched_dt + timedelta(minutes=15)
                    
                    arrival = cashier.time_arrived
                    if timezone.is_aware(arrival):
                        arrival = timezone.make_naive(arrival)
                    
                  
                    if arrival > threshold_time:
                        is_late = True
                    
                try:
                    voucher = Voucher.objects.get(cashier=cashier)
                    voucher = voucher.voucher_code
                except Exception as e:
                    voucher = 'N/A'

              
                data.append({
                    'id': cashier.id,
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
                        'price': float(cashier.vehicle.peso_price) if cashier.vehicle else 0.0
                    } if cashier.vehicle else None,
                    
                    # We show the values stored in the DB, not recalculated ones
                    'subsidy_amount': float(cashier.subsidy_amount),
                    'amount_released': float(cashier.amount_released),
                    'voucher':voucher,
                    'is_late': is_late,
                    'remarks': cashier.remarks,
                    'image_count': cashier.images.count(), 
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




@login_required
@require_GET
def cashier_api_list(request):
    """API endpoint to get list of cashiers as JSON"""
    try:
        # Get all cashiers for stats
        all_cashiers = Cashier.objects.select_related(
            'start_location', 
            'campus', 
            'vehicle', 
            'approved_by',
            'leader'
        ).prefetch_related('images', 'leader').all()
        
        # Get only non-approved and non-rejected cashiers for table display
        pending_cashiers = all_cashiers.filter(approved_by__isnull=True, rejected=False)
        

        cashiers_data = []
        for cashier in pending_cashiers:
            # Get all images for this cashier
            images = cashier.images.all()
            image_urls = [img.image.url for img in images] if images.exists() else []
            
            # users = []
            # attendees=LeadersAttendees.objects.filter(leader=user)
            # for attendee in attendees:
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
                'leader_first_name': cashier.leader.first_name,
                'leader_last_name': cashier.leader.last_name,
                'date': cashier.date.strftime('%Y-%m-%d'),
                'start_location': str(cashier.start_location) if cashier.start_location else None,
                'campus': str(cashier.campus) if cashier.campus else None,
                'vehicle': str(cashier.vehicle) if cashier.vehicle else None,
                'plate_num': cashier.plate_num,
                'subsidy_type': str(cashier.subsidy_type) if cashier.subsidy_type else None,
                'service_schedule': str(cashier.service_schedule) if cashier.service_schedule else None,
                'time_arrived': time_arrived_str,
                'remarks': cashier.remarks,
                'approved_by': f"{cashier.approved_by.first_name} {cashier.approved_by.last_name}" if cashier.approved_by else None,
                'images': image_urls,
                'photo_url': image_urls[0] if image_urls else None,
                'users': users_list,
                'users_count': len(users_list)
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
        while True:
            try:
                alpha_caps = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
                alpha_low_caps = alpha_caps.lower()
                chars = f"{alpha_low_caps}123456789" 
                code = ''.join(secrets.choice(chars) for _ in range(length))
                is_exists = Voucher.objects.filter(voucher_code=code).exists()
                if not is_exists:
                    break
                else:
                    continue
            except Exception as e:
                continue
        return code

@login_required
@require_POST
def approve_cashier(request, cashier_id):
    """Approve a cashier entry"""
    try:
        cashier = get_object_or_404(Cashier, id=cashier_id)
        
        # Check if already approved
        if cashier.approved_by:
            return JsonResponse({
                'error': 'This cashier entry is already approved.'
            }, status=400)
        
        code = generate_voucher(7)
    
        voucher_data = Voucher(voucher_code=code,cashier=cashier)
        voucher_data.save()

        # Assign the current logged-in user to approved_by
        cashier.approved_by = request.user
        cashier.save()
        
        return JsonResponse({
            'success': True,
            'approved_by': str(request.user),
            'message': 'Cashier entry approved successfully.'
        })
        
    except Exception as e:
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
    




class AccountApproval(LoginRequiredMixin,TemplateView):
    login_url = 'login-cargo'
    template_name = 'Pastor/account_approvals.html'

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
      
        if user.is_authenticated:
          
            if user.type not in ['PTR']:
                return redirect(Usertype[user.type])
        return super().dispatch(request, *args, **kwargs)
    




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
        
        # total_count = UserType.objects.filter(type='LE')
        # approved_count = total_count.filter(is_active_leader=True).count()
        # pending_count = total_count.filter(is_active_leader=False).count()
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
