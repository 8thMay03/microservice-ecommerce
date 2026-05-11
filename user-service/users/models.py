from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", "CUSTOMER")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "MANAGER")
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_staff_flag", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        STAFF = "STAFF", "Staff"
        MANAGER = "MANAGER", "Manager"

    class StaffRole(models.TextChoices):
        WAREHOUSE = "WAREHOUSE", "Warehouse Staff"
        SALES = "SALES", "Sales Staff"
        SUPPORT = "SUPPORT", "Customer Support"
        MANAGER = "MANAGER", "Manager"

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Customer-specific fields
    phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")

    # Staff/Manager-specific fields
    staff_role = models.CharField(
        max_length=20, choices=StaffRole.choices, blank=True, default=""
    )
    is_admin = models.BooleanField(default=False)
    is_staff_flag = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"

    @property
    def is_staff(self):
        return self.is_staff_flag or self.role in ("STAFF", "MANAGER")

    @property
    def is_superuser(self):
        return self.role == "MANAGER" and self.is_admin

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}> [{self.role}]"
