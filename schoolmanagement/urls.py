from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include, reverse_lazy

from . import views
# from .views import (
#     CustomLoginView,
#     CustomPasswordResetForm, 
#     CustomSetPasswordForm,
#     CustomPasswordResetConfirmView
# )

app_name = 'schoolmanagement'

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    
    # Password Reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='auth/password_reset_form.html',
        email_template_name='auth/password_reset_email.html',
        subject_template_name='auth/password_reset_subject.txt',
        success_url=reverse_lazy('schoolmanagement:password_reset_done')
    ), name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html',
        success_url=reverse_lazy('schoolmanagement:password_reset_complete')
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Profiles
    path('profile/', views.profile_view, name='profile'),
    path('profile/student/', views.student_profile, name='student_profile'),
    path('profile/student/<int:student_id>/', views.student_detail, name='student_detail'),
    path('profile/student/<int:student_id>/add_guardian/', views.add_guardian, name='add_guardian'),
    path('profile/staff/', views.staff_profile, name='staff_profile'),
    
    # Guardian URLs
    path('guardian/', views.guardian_dashboard, name='guardian_dashboard'),
    path('guardian/student/<int:student_id>/', views.student_detail, name='guardian_student_detail'),
    path('guardian/attendance/<int:student_id>/', views.attendance_history, name='attendance_history'),
    path('guardian/exams/<int:student_id>/', views.exam_results, name='exam_results'),
    path('guardian/fees/<int:student_id>/', views.fee_payments, name='fee_payments'),
    
    # Registration
    path('register/student/', views.register_student, name='register_student'),
    path('register/staff/', views.register_staff, name='register_staff'),
    
    # Academics
    path('exam/create/', views.create_exam, name='create_exam'),
    
    # Fees
    path('fee/create/', views.create_fee_structure, name='create_fee_structure'),
    
    # Attendance
    path('attendance/mark/<int:class_id>/', views.mark_attendance, name='mark_attendance'),
    
    # Classes
    path('class/<int:class_id>/', views.class_detail, name='class_detail'),
    
    # Staff Management
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/<int:staff_id>/', views.view_staff, name='view_staff'),
    path('staff/<int:staff_id>/edit/', views.edit_staff, name='edit_staff'),
    path('staff/<int:staff_id>/delete/', views.delete_staff, name='delete_staff'),
    path('staff/<int:staff_id>/assign-subjects/', views.assign_subjects, name='assign_subjects'),
    path('staff/<int:staff_id>/assign-classes/', views.assign_classes, name='assign_classes'),
]
