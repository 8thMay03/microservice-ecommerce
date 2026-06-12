from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class StaffManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "MANAGER")
        extra_fields.setdefault("is_admin", True)
        return self.create_user(email, password, **extra_fields)


class StaffMember(AbstractBaseUser):
    class Role(models.TextChoices):
        WAREHOUSE = "WAREHOUSE", "Warehouse Staff"
        SALES = "SALES", "Sales Staff"
        SUPPORT = "SUPPORT", "Customer Support"
        MANAGER = "MANAGER", "Manager"

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WAREHOUSE)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = StaffManager()

    class Meta:
        db_table = "staff_members"

    @property
    def is_superuser(self):
        return False

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    def __str__(self):
        return f"{self.first_name} {self.last_name} [{self.role}]"
