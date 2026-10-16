from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from django.contrib.auth import authenticate

from .models import UserType

from django import forms



class RegistrationForm(UserCreationForm):

    email = forms.EmailField(label='Email Address', widget=forms.EmailInput(attrs={'placeholder':'Ex. juandelacruz@gmail.com'}))

    go_group_id = forms.CharField(label='Go Group ID', max_length=8, required=True)





    class Meta:

        model = UserType

        fields = ['go_group_id','first_name','last_name', 'email','password1', 'password2']

    def clean_first_name(self):

        first_name = self.cleaned_data.get('first_name')



        if first_name:

            first_name = first_name.capitalize()



        return first_name 

    

    def clean_last_name(self):

        last_name = self.cleaned_data.get('last_name')



        if last_name:

            last_name = last_name.capitalize()



        return last_name     

    def clean(self):

        cleaned_data = super().clean()

        go_group_id = cleaned_data.get('go_group_id')

        first_name = cleaned_data.get('first_name')

        last_name = cleaned_data.get('last_name')

    

          

        if UserType.objects.filter(go_group_id=go_group_id).exists():

            self.add_error('go_group_id', 'Go Group ID already taken')

     

            self.add_error('password2','Incorrect Password confirmation')

        

        if not first_name:

            self.add_error('first_name', 'First Name is required')

        elif not last_name:

            self.add_error('last_name', 'Last Name is required')





        return cleaned_data

   

















class LoginForm(AuthenticationForm):



    username = forms.CharField(widget=forms.EmailInput(attrs={'class': 'form-control'}))

    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))



    

    def clean(self):

        cleaned_data = super().clean()

        username = cleaned_data.get('username')

        password = cleaned_data.get('password')  



        # Check if username exists in your custom UserType model

        if not UserType.objects.filter(email=username).exists():

            self.add_error('username', 'No user found with this username')

        

            



        user = authenticate(username=username, password=password)

        if user is None or user.is_active == False:

            raise forms.ValidationError("Invalid username or password") 

        elif user.is_active_leader == False and user.type == 'LE':

            raise forms.ValidationError("Please contact your pastor for Account approval") 



        self.user = user

        return cleaned_data
