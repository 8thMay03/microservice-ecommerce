from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class ManagerUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class ManagerUser(AbstractBaseUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]
    objects = ManagerUserManager()

    class Meta:
        db_table = "managers"

    @property
    def is_staff(self):
        return True  # All managers can access admin

    @property
    def is_superuser(self):
        return True

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"
