from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Student, Staff, Guardian, Subject, Class, Exam, ExamResult, FeeStructure, FeePayment, Attendance, Timetable, StudentClass, ClassSubject

# Define an inline admin descriptor for Student model
class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'student'

# Define an inline admin descriptor for Staff model
class StaffInline(admin.StackedInline):
    model = Staff
    can_delete = False
    verbose_name_plural = 'staff'

class CustomUserAdmin(UserAdmin):
    inlines = (StudentInline, StaffInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_staff', 'is_active')}
        ),
    )

admin.site.register(User, CustomUserAdmin)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'admission_number', 'date_of_birth', 'gender')
    list_filter = ('gender',)
    search_fields = ('user__username', 'student_id', 'admission_number')

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_id', 'role', 'date_joined')
    list_filter = ('role',)
    search_fields = ('user__username', 'staff_id')

@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('get_student_name', 'first_name', 'last_name', 'relationship')
    list_filter = ('relationship',)
    search_fields = ('student__user__first_name', 'student__user__last_name', 'first_name', 'last_name')
    
    def get_student_name(self, obj):
        return obj.student.user.get_full_name() if obj.student and obj.student.user else 'No Student'
    get_student_name.short_description = 'Student'
    get_student_name.admin_order_field = 'student__user__first_name'

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'get_teacher_count')
    list_filter = ('teachers',)
    search_fields = ('name', 'code')
    
    def get_teacher_count(self, obj):
        return obj.teachers.count()
    get_teacher_count.short_description = 'Teachers'
    get_teacher_count.admin_order_field = 'teachers__count'

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'stream', 'get_students_count', 'get_teachers_count', 'get_subjects_count')
    list_filter = ('name', 'stream')
    search_fields = ('name', 'stream')
    
    def get_students_count(self, obj):
        return obj.students.count()
    get_students_count.short_description = 'Students'
    
    def get_teachers_count(self, obj):
        return obj.teachers.count()
    get_teachers_count.short_description = 'Teachers'
    
    def get_subjects_count(self, obj):
        return obj.subjects.count()
    get_subjects_count.short_description = 'Subjects'

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'subject', 'class_level', 'total_marks')
    list_filter = ('date', 'subject', 'class_level')
    search_fields = ('name', 'subject__name')

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'marks_obtained', 'grade')
    list_filter = ('exam__subject', 'exam__class_level')
    search_fields = ('student__user__username', 'exam__name')

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('class_level', 'amount', 'description', 'due_date')
    list_filter = ('due_date', 'class_level')
    search_fields = ('class_level__name', 'description')

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'fee_structure', 'amount_paid', 'payment_date', 'payment_method')
    list_filter = ('payment_date', 'payment_method')
    search_fields = ('student__user__username', 'receipt_number')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'remarks')
    list_filter = ('date', 'status')
    search_fields = ('student__user__username',)

@admin.register(StudentClass)
class StudentClassAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_level', 'admission_date', 'is_active')
    list_filter = ('class_level', 'admission_date', 'is_active')
    search_fields = ('student__user__username', 'class_level__name')
    ordering = ['-admission_date']

@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = ('class_level', 'subject', 'teacher')
    list_filter = ('class_level', 'subject')
    search_fields = ('class_level__name', 'subject__name', 'teacher__user__username')
    ordering = ['class_level__name', 'subject__name']

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('class_level', 'subject', 'teacher', 'day', 'period', 'start_time', 'end_time')
    list_filter = ('day', 'period', 'class_level')
    search_fields = ('class_level__name', 'subject__name', 'teacher__user__username')
    ordering = ('day', 'period')
