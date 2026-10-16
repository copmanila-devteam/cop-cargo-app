from django.shortcuts import render, redirect, reverse

from django.contrib.auth.views import LoginView

from django.views.generic import TemplateView

from .forms import LoginForm, RegistrationForm

from django.contrib.auth.decorators import login_required

from django.contrib.auth import logout

from django.urls import reverse_lazy

from django.contrib import messages
from django.http import JsonResponse
import json
from .auth import Usertype



class RegistrationView(TemplateView):

   

    template_name = 'Registration/register.html'

    

    def get(self,request, *args, **kwargs):

        form = RegistrationForm()



        return render(request, self.template_name, {'form': form})

    

    def post(self, request, *args, **kwargs):

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":

            data = json.loads(request.body)

            data_list = {

                'go_group_id': int(data.get('go_group_id')),

                'email': data.get('email'),

                'first_name':data.get('first_name'),

                'last_name':data.get('last_name'),

                'password1': data.get('password1'),

                'password2': data.get('password2'),

            }

            form = RegistrationForm(data_list)

           

            if form.is_valid():

                try:

                    user = form.save(commit=False)

                    user.type = 'LE'

                    user.save()

                    return JsonResponse({'status':'success','message':'Registration Successful. You are now Registered', 'success_url':'/login/'})

                except Exception as e:

                    return JsonResponse({'status':'error','message':str(e)})

            else:

                return JsonResponse({'status':'error forms', 'messages':form.errors.get_json_data()})

        else:

            form = RegistrationForm()

            return render(request, self.template_name,{'form':form})

        



class LoginCargoView(LoginView):

    form_class = LoginForm

    template_name = 'Authentication/login.html'



    

    def dispatch(self, request, *args, **kwargs):

        user = self.request.user

      

        if user.is_authenticated:

            if not user.is_active:

                return redirect('login-cargo')

            return redirect(Usertype[user.type])

       

        return super().dispatch(request, *args, **kwargs)

    

    

    def post(self, request, *args, **kwargs):

        

        form = self.get_form()

        if form.is_valid():

            

            return self.form_valid(form)



        else:

           return render(request, self.template_name, {'form': form})



    def get_success_url(self):

        user = self.request.user

        return Usertype[user.type]

    

       

    






