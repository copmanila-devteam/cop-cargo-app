

from django import forms

from django.contrib.auth.models import User

from django.contrib.auth import authenticate

from django.contrib.auth.hashers import make_password

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from django.core.validators import MinValueValidator, MaxValueValidator

from django import forms

from .models import Cashier, Attendees, SubsidyType,Campus, Vehicle, ServiceSchedule, City













class MultipleFileInput(forms.ClearableFileInput):

    allow_multiple_selected = True



class CashierEntryForm(forms.ModelForm):

    # Field 1: Dynamic QuerySet for validation

    service_schedule = forms.ModelChoiceField(

        queryset=ServiceSchedule.objects.all(),

        required=True,

        empty_label='Select Service Schedule',

        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_service_schedule'})

    )



    # Field 2: Campus selector

    campus = forms.ModelChoiceField(

        required=True,

        empty_label='Select COP campus',

        queryset=Campus.objects.all(),

        widget=forms.Select(attrs={

            'class': 'form-control', 

            'id': 'id_campus',

            'data-action': 'change->trip-form#filterSchedules',

        })

    )





    start_location = forms.ModelChoiceField(

        required=True,

        empty_label='Select Origin',

        label='Origin',

        queryset=City.objects.all(),

        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_start_location'}),

       

    )



    subsidy_type = forms.ModelChoiceField(

        required=True,

        empty_label='Select Subsidy type',

        label="Subsidy Type*",

        queryset=SubsidyType.objects.all(),

        widget=forms.Select(attrs={'class': 'form-control'}))





    vehicle = forms.ModelChoiceField(

        required=True,

        empty_label='Select Vehicle',

        label="Vehicle Type*",

        queryset=Vehicle.objects.all(),

        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_vehicle'})

       

    )





    # Field 3: "Dummy" field to handle the UI for photos

    # Using CharField with required=False prevents "No file submitted" errors

    photos = forms.CharField(

        required=False, 

        label="Upload Receipts/Photos*",

        widget=MultipleFileInput(attrs={

            'class': 'form-control',

            'multiple': True,

            'accept': 'image/*',

            'id': 'id_photos',

            'required':'required',

            'data-action': 'change->trip-form#previewImages'

        })

    )



    class Meta:

        model = Cashier

        # DO NOT put 'photos' in this list

        fields = ['start_location', 'campus', 'service_schedule', 'vehicle', 'subsidy_type', 'plate_num']

        widgets = {

         

            'plate_num': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex. ABC 123'}),

        }



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Filters schedules based on campus during form validation

        if 'campus' in self.data:

            try:

                campus_id = int(self.data.get('campus'))

                self.fields['service_schedule'].queryset = ServiceSchedule.objects.filter(campus_id=campus_id)

            except (ValueError, TypeError):

                self.fields['service_schedule'].queryset = ServiceSchedule.objects.none()





class PassengerForm(forms.Form):  



    cop_id = forms.IntegerField(

    required=False,

    label="COP ID",

    min_value=000000,

    max_value=999999,

    widget=forms.NumberInput(attrs={

        'class': 'form-control',

        'placeholder': '6-digit COP ID. If None leave it blank',

        'id': 'id_cop_id',

        'oninput': 'javascript: if (this.value.length > 6) this.value = this.value.slice(0, 6);'

    }),

    error_messages={

        'min_value': 'COP ID must be at least 6 digits.',

        'max_value': 'COP ID cannot exceed 6 digits.',

    })



    first_name = forms.CharField(

        max_length=200,

        widget=forms.TextInput(attrs={

            'class': 'form-control',

            'placeholder': 'First Name',

            'id': 'id_first_name'

        })

    )

    middle_name = forms.CharField(

        max_length=200,
        required=False,

        widget=forms.TextInput(attrs={

            'class': 'form-control',

            'placeholder': 'Middle Name',

            'id': 'id_middle_name'

        })

    )

    last_name = forms.CharField(

        max_length=100,

        widget=forms.TextInput(attrs={

            'class': 'form-control',

            'placeholder': 'Last Name',

            'id': 'id_last_name'

        })

    )

    def clean_cop_id(self):

        cop_id = self.cleaned_data.get('cop_id')

        

        # Only check if a value was actually entered

        if cop_id:

            # Check if this COP ID already exists in the database

            if Attendees.objects.filter(cop_id=int(cop_id)).exists():

                raise forms.ValidationError(

                    "This COP ID is already registered. Please use a different one."

                )

        return cop_id
