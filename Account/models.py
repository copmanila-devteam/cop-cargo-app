from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser, BaseUserManager
import datetime

class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        # Notice 'username' is removed from the arguments here
        return self.create_user(email, password, **extra_fields)

class UserType(AbstractUser):
    usertype_choices = [
          ('PTR','Pastor'),
          ('FI','Finance'),
          ('LE','Leader'),
          ('ACNT','Accountant')]

    type = models.CharField(choices=usertype_choices, max_length=100,default='FI')
    is_active_leader = models.BooleanField(default=False)
    email = models.EmailField(unique=True, null=False, blank=False)
    first_name = models.CharField(max_length=250, blank=True, null=True)
    campus = models.ForeignKey('cashier.Campus', on_delete=models.SET_DEFAULT, default=1)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    username = None
    date_approved = models.DateField(null=True)
    objects = MyUserManager()
    go_group_id = models.IntegerField(

        validators=[
            MinValueValidator(1000),
            MaxValueValidator(99999999)
        ],
        null=True,                   
        blank=True,
        unique=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["password",]

    def __str__(self):
        return self.email

# For the designated landing page based on the user type. Decommissioning the Auth.py
class AuthRoute(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=6)
    url = models.CharField(max_length=200) # Can be switched to URLField for standardized
    updated_on = models.DateTimeField(auto_now=datetime.datetime.now)
    
    def __str__(self):
        return self.name