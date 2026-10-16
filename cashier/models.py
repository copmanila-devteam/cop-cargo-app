from django.db import models

from Account.models import UserType

from django.core.validators import MinValueValidator, MaxValueValidator

from django.core.validators import RegexValidator
from django.utils import timezone





class Vehicle(models.Model):

    """Vehicle model for different types of vehicles"""

    name = models.CharField(max_length=100)

    peso_price = models.DecimalField(max_digits=10, decimal_places=2)

    

    class Meta:

        db_table = 'vehicle'

    

    def __str__(self):

        return self.name











class Campus(models.Model):

    """Campus model for locations"""

    name = models.CharField(max_length=255, unique=True)

    

    class Meta:

        db_table = 'campus'

        verbose_name_plural = 'Campuses'

    

    def __str__(self):

        return self.name







class Attendees(models.Model):

    """User model for passengers and leaders"""



    first_name = models.CharField(max_length=250)

    middle_name = models.CharField(max_length=200, blank=True, null=True)

    last_name = models.CharField(max_length=250)

    cop_id = models.IntegerField(

        validators=[

            MinValueValidator(000000),

            MaxValueValidator(999999)

        ],

        null=True,

        blank=True,

        unique=True,

        error_messages={

            'unique': "This COP ID is already registered. Please check the ID and try again."

        }

    )



     

    class Meta:

        db_table = 'user'

    

    def __str__(self):

        return f"{self.first_name}  {self.middle_name} {self.last_name}"

    

    @property

    def full_name(self):

        return f"{self.first_name}  {self.middle_name} {self.last_name}"

    



   



class City(models.Model):

    name = models.CharField(max_length=300)



    def __str__(self):

        return f"{self.name}"







class SubsidyType(models.Model):

    name = models.CharField(max_length=200)



    def __str__(self):

        return self.name





class ServiceSchedule(models.Model):

    DAY_CHOICES = [

        ('MON', 'Monday'),

        ('TUE', 'Tuesday'),

        ('WED', 'Wednesday'),

        ('THU', 'Thursday'),

        ('FRI', 'Friday'),

        ('SAT', 'Saturday'),

        ('SUN', 'Sunday'),

    ]



    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, null=True, blank=True, related_name='service_entries')

    time = models.TimeField()

    days = models.CharField(max_length=50, choices=DAY_CHOICES)



    def __str__(self):

        # This mirrors the view logic for consistency

        formatted_time = self.time.strftime("%I:%M %p")

        return f"{self.campus.name} | {self.get_days_display()} | {formatted_time}"







class LeadersAttendees(models.Model):

    attendee = models.ForeignKey(Attendees, on_delete=models.CASCADE, related_name='leaders_attendees')

    leader = models.ForeignKey(UserType, on_delete=models.CASCADE, related_name='leader')





class Cashier(models.Model):

    leader = models.ForeignKey(UserType, on_delete=models.CASCADE, related_name='led_cashier_entries')

    date = models.DateField()

    start_location = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='city_entries')

    campus = models.ForeignKey(Campus, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashier_entries')

    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashier_entries')

    subsidy_type = models.ForeignKey(SubsidyType, on_delete=models.CASCADE, null=True, blank=True, related_name='subsidy_types')
    capacity = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(20)],default=0)

    plate_regex = RegexValidator(

        regex=r'^[A-Z]{3}\d{3,4}$',

        message="Plate number must be in the format: 'ABC 123' or 'ABC 1234'"

    )

    plate_num = models.CharField(max_length=200, validators=[plate_regex],

        help_text="Format: ABC 123")

    # users = models.ManyToManyField(Attendees, through='CashierUsers', related_name='cashier_entries')

    approved_by = models.ForeignKey(UserType, on_delete=models.CASCADE, null=True, related_name='approved_cashier_entries')

    subsidy_amount = models.DecimalField(max_digits=12, decimal_places=2,default=0.00)

    amount_released = models.DecimalField(max_digits=12, decimal_places=2,default=0.00)


    completed = models.BooleanField(default=False)
    

    rejected = models.BooleanField(default=False)

    service_schedule = models.ForeignKey(ServiceSchedule, on_delete=models.CASCADE, null=True, blank=True, related_name='service_schedule')

    time_arrived = models.DateTimeField(default=timezone.now, null=True)

    remarks = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = 'cashier'
        ordering = ['-date']
        indexes = [
       
            models.Index(fields=['campus', '-time_arrived'], name='idx_cash_campus_time'),
            models.Index(fields=['approved_by'], name='idx_cash_approved'),
            models.Index(fields=['-time_arrived'], name='idx_cash_time'),
            models.Index(fields=['campus', 'approved_by', '-time_arrived'], name='idx_cash_camp_appr_time'),
        ]



    def __str__(self):

        # Updated to use the leader relationship since first_name/last_name fields are gone

        return f"{self.leader.first_name} {self.leader.last_name} - {self.date}"


class Voucher(models.Model):

    cashier = models.ForeignKey(Cashier, on_delete=models.CASCADE)

    voucher_regex = RegexValidator(

        regex=r'^[a-zA-Z0-9]{7}$',

        message="Voucher code should be combination of 7 alpha and numeric characters"

    )

    voucher_code = models.CharField(max_length=150, validators=[voucher_regex], null=False)




class CargoDetails(models.Model):

    cashier = models.ForeignKey(Cashier, on_delete=models.CASCADE, related_name='cargo_cashier')

    cargo = models.ForeignKey(LeadersAttendees, on_delete=models.CASCADE, related_name='cargo_leaders_attendees')

      

    class Meta:

        db_table = 'cargo_details'







class CashierImage(models.Model):

    cashier = models.ForeignKey(

        Cashier, 

        on_delete=models.CASCADE, 

        related_name='images'

    )

    image = models.ImageField(upload_to='cashier_photos/')
    hash = models.CharField(max_length=64, unique=True, db_index=True, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)



    def __str__(self):

        return f"Image for {self.cashier.id}"





class Matrix(models.Model):

    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, related_name='matrix_campus')

    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, null=True, blank=True, related_name='matrix_campus')

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True)

    peso_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)



    def __str__(self):

        return f'{self.campus} {self.vehicle} | {self.peso_price}'

    

    class Meta:

        db_table = 'Matrix'

        verbose_name ='Matrix'

        verbose_name_plural = 'Matrix Fare'





    

class CashierUsers(models.Model):

    """Junction table linking Cashier and User with role"""

    ROLE_CHOICES = [

        ('member', 'Member'),

    ]

    

    cashier = models.ForeignKey(

        Cashier,

        on_delete=models.CASCADE,

        related_name='cashier_user_links'

    )

    user = models.ForeignKey(

        Attendees,

        on_delete=models.CASCADE,

        related_name='user_cashier_links'

    )

    role = models.CharField(

        max_length=50,

        choices=ROLE_CHOICES,

        default='passenger'

    )

    

    class Meta:

        db_table = 'cashier_users'

        unique_together = ['cashier', 'user']

        verbose_name = 'Cashier User'

        verbose_name_plural = 'Cashier Users'

    

    def __str__(self):

        return f"{self.user} - {self.cashier} ({self.role})"
