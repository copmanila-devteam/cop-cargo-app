from django.contrib import admin

from .models import Vehicle, Campus, Attendees, Cashier, CashierUsers, City, SubsidyType, Matrix, ServiceSchedule, CashierImage, LeadersAttendees, CargoDetails, Voucher
from .models import Event, RemarksList

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'description']
    search_fields = ['name', 'start_date', 'end_date', 'description']

@admin.register(RemarksList)
class RemarksListAdmin(admin.ModelAdmin):
    list_display = ['description', 'user', 'cashier', 'timestamp']
    search_fields = ['description', 'user__first_name', 'user__last_name', 'cashier__leader__first_name', 'cashier__leader__last_name']

# @admin.register(CampusEvent)
# class CampusEventAdmin(admin.ModelAdmin):
#    list_display = ['campus__name', 'event__name']
#    search_fields = ['campus__name', 'event__name']

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['name', 'peso_price']
    search_fields = ['name']



@admin.register(ServiceSchedule)

class ServiceSchedAdmin(admin.ModelAdmin):

    list_display = ['campus', 'time', 'days']

    search_fields = ['campus']





@admin.register(SubsidyType)

class SubsidyTypeAdmin(admin.ModelAdmin):

    list_display = ['name']

    search_fields = ['name']







@admin.register(Campus)

class CampusAdmin(admin.ModelAdmin):

    list_display = ['id','name']

    search_fields = ['name']





@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']







@admin.register(Matrix)
class MatrixAdmin(admin.ModelAdmin):
    list_display = ['campus','city','vehicle', 'peso_price']
    search_fields = ['campus__name', 'city__name', 'vehicle__name']


@admin.register(Attendees)
class AttendeesAdmin(admin.ModelAdmin):

    # This makes the Attendees searchable (required for autocomplete)

    search_fields = ['first_name', 'last_name', 'cop_id']

    list_display = ['first_name', 'last_name', 'cop_id']

    # This makes the COP ID editable directly from the main list view
    list_editable = ['cop_id']



@admin.register(LeadersAttendees)
class LeaderAttendeesAdmin(admin.ModelAdmin):
    list_display = ['attendee', 'leader']
    search_fields = ['attendee', 'leader']

@admin.register(CargoDetails)
class CargoDetailsAdmin(admin.ModelAdmin):
    list_display = ['cashier', 'cargo']
    search_fields = ['cashier', 'cargo']





class CashierUsersInline(admin.TabularInline):

    model = CashierUsers

    extra = 1

    # FIX: Use 'user' because that is the field name in your model

    autocomplete_fields = ['user'] 

    

    # Adding cop_id as a read-only field so you can see it while editing the trip

    fields = ['user', 'get_cop_id', 'role']

    readonly_fields = ['get_cop_id']



    def get_cop_id(self, obj):

        return obj.user.cop_id if obj and obj.user else "-"

    get_cop_id.short_description = 'COP ID'







@admin.register(CashierImage)

class CashierImageAdmin(admin.ModelAdmin):

    list_display = ['get_cashier_name','image', 'cashier']



    def get_cashier_name(self, obj):

        return f'{obj.cashier.leader.first_name} {obj.cashier.leader.last_name}'









@admin.register(Cashier)

class CashierAdmin(admin.ModelAdmin):

  

    list_display = [

        'get_leader_first', 

        'get_leader_last',

        'date', 

        'start_location', 

        'campus', 

        'subsidy_amount',

        'amount_released',

        'vehicle', 

        

        'time_arrived', 

        'service_schedule'

    ]

    

    # 2. These must be actual model fields. 

    # Note: 'service_schedule' and 'time_arrived' are fine.

    list_editable = ['time_arrived', 'service_schedule'] 

    

    list_filter = ['date', 'campus', 'vehicle']

    

    # 3. Use double underscores (__) to search through relationships

    search_fields = [

        'leader__first_name', 

        'leader__last_name', 

        'start_location__name'

    ]

    



    # 4. Use 'leader' in the edit fields instead of the separate name strings

    fields = [

        'leader', 

        'date', 

        'start_location', 

        'campus',
        'capacity', 

        'vehicle', 

        'plate_num',

        'subsidy_amount',

        'amount_released',

        'subsidy_type', 

        'service_schedule', 

        'time_arrived', 

        'approved_by',

        'rejected',

        'remarks'

    ]



    # --- Custom Methods to access UserType data ---



    def get_leader_first(self, obj):

        return obj.leader.first_name

    get_leader_first.short_description = 'Leader First Name'

    get_leader_first.admin_order_field = 'leader__first_name' # Allows sorting



    def get_leader_last(self, obj):

        return obj.leader.last_name

    get_leader_last.short_description = 'Leader Last Name'

    get_leader_last.admin_order_field = 'leader__last_name'



@admin.register(Voucher)

class VoucherAdmin(admin.ModelAdmin):

    list_display = ['cashier', 'voucher_code']

    search_fields = ['voucher_code']

    





@admin.register(CashierUsers)

class CashierUsersAdmin(admin.ModelAdmin):

    # FIX: Use a method 'get_cop_id' instead of the field 'cop_id'

    list_display = ['get_cop_id', 'user_name', 'role', 'cashier_info']

    list_filter = ['role', 'cashier__date', 'cashier__campus']

    search_fields = ['user__first_name', 'user__last_name', 'user__cop_id']



    def get_cop_id(self, obj):

        return obj.user.cop_id if obj.user else "-"

    get_cop_id.short_description = 'COP ID'



    def user_name(self, obj):

        return f"{obj.user.first_name} {obj.user.last_name}"

    user_name.short_description = 'Personnel'



    def cashier_info(self, obj):

        return f"Trip to {obj.cashier.campus} ({obj.cashier.date})"

    cashier_info.short_description = 'Trip Details'

