from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from schoolmanagement.models import Student, Staff, Guardian
from schoolmanagement.utils import (
    generate_student_admission_number,
    generate_staff_number,
    generate_guardian_number
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate and assign unique identifiers to existing students, staff, and guardians'

    def handle(self, *args, **options):
        # Generate admission numbers for students without one
        students = Student.objects.filter(admission_number__isnull=True)
        for student in students:
            student.admission_number = generate_student_admission_number()
            student.save()
            self.stdout.write(self.style.SUCCESS(f'Assigned admission number {student.admission_number} to student {student.user.username}'))
        
        # Generate staff numbers for staff without one
        staff_members = Staff.objects.filter(staff_id__isnull=True)
        for staff in staff_members:
            staff.staff_id = generate_staff_number()
            staff.save()
            self.stdout.write(self.style.SUCCESS(f'Assigned staff number {staff.staff_id} to {staff.user.username}'))
        
        # Generate guardian numbers for guardians without one
        guardians = Guardian.objects.filter(guardian_number__isnull=True)
        for guardian in guardians:
            guardian.guardian_number = generate_guardian_number()
            guardian.save()
            self.stdout.write(self.style.SUCCESS(f'Assigned guardian number {guardian.guardian_number} to {guardian.user.username if guardian.user else guardian.email}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully generated all identifiers'))
