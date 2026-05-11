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


class User(AbstractBaseUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        STAFF = "STAFF", "Staff"
        MANAGER = "MANAGER", "Manager"

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    staff_role = models.CharField(max_length=20, blank=True, default="")
    is_admin = models.BooleanField(default=False)
    is_staff_flag = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        managed = False
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
