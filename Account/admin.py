from django.contrib import admin
from .models import UserType, AuthRoute


admin.site.site_header = "COP Cargo Admin"
admin.site.site_title = "COP Cargo"
admin.site.index_title = "Welcome to Cargo Admin"


# Register your models here.
@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name','go_group_id','email']
    search_fields = ['first_name','last_name', 'email']
    list_display_links = ['first_name', 'email']

    def save_model(self, request, obj, form, change):

        if 'password' in form.changed_data:
            obj.set_password(obj.password)
            
        return super().save_model(request, obj, form, change)

@admin.register(AuthRoute)
class AuthRouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'url', 'updated_on']
    search_fields = ['code', 'name']