from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import AbstractUser
from tenant.models import Tenant 

class CustomUser(AbstractUser):
    # Define choices for user roles
    ADMIN = 'admin'
    EMPLOYEE = 'employee'
    MANAGER = 'manager'
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (EMPLOYEE, 'Employee'),
        (MANAGER, 'Manager'),
    ]

    # Existing fields
    organization = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    # Additional fields
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    job_profile = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.username
    

