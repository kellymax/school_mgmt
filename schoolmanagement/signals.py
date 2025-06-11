from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Student, Staff, Guardian

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to create a Student or Staff profile when a new User is created.
    The user type is determined by the 'is_staff' flag.
    """
    if created:
        if instance.is_staff:
            Staff.objects.get_or_create(user=instance)
        else:
            Student.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal to save the profile when the User model is saved.
    """
    if hasattr(instance, 'student'):
        instance.student.save()
    elif hasattr(instance, 'staff'):
        instance.staff.save()
    elif hasattr(instance, 'guardian'):
        instance.guardian.save()
