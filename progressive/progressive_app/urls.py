from django.urls import path
from . import views

app_name = "progressive_app"

urlpatterns = [
    # -----------------------------------------------------------------
    # Auth
    # -----------------------------------------------------------------
    path("login/", views.custom_login, name="login"),
    path("logout/", views.custom_logout, name="logout"),

    # -----------------------------------------------------------------
    # Dashboard
    # -----------------------------------------------------------------
    path("dashboard/", views.dashboard, name="dashboard"),

    # -----------------------------------------------------------------
    # Students CRUD
    # -----------------------------------------------------------------
    path("students/", views.students_list, name="students_list"),
    path("students/create/", views.student_create, name="student_create"),
    path("students/<int:pk>/edit/", views.student_update, name="student_update"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),
    path("students/<int:student_id>/report/", views.student_report, name="student_report"),
    # progressive_app/urls.py
    path("results/student/<int:student_id>/pdf/", views.student_results_download, name="student_results_download"),

    # -----------------------------------------------------------------
    # Teachers CRUD
    # -----------------------------------------------------------------
    path("teachers/", views.teachers_list, name="teachers_list"),
    path("teachers/create/", views.teacher_create, name="teacher_create"),
    path("teachers/<int:pk>/edit/", views.teacher_update, name="teacher_update"),
    path("teachers/<int:pk>/delete/", views.teacher_delete, name="teacher_delete"),

    # -----------------------------------------------------------------
    # Admins CRUD
    # -----------------------------------------------------------------
    path("admins/", views.admins_list, name="admins_list"),
    path("admins/<int:pk>/edit/", views.admin_update, name="admin_update"),
    path("admins/<int:pk>/delete/", views.admin_delete, name="admin_delete"),

    # -----------------------------------------------------------------
    # Departments CRUD
    # -----------------------------------------------------------------
    path("departments/", views.departments_list, name="departments_list"),
    path("departments/create/", views.department_create, name="department_create"),
    path("departments/<int:pk>/edit/", views.department_edit, name="department_edit"),
    path("departments/<int:pk>/delete/", views.department_delete, name="department_delete"),

    # -----------------------------------------------------------------
    # Courses CRUD
    # -----------------------------------------------------------------
    path("courses/", views.courses_list, name="courses_list"),
    path("courses/create/", views.course_create, name="course_create"),
    path("courses/<int:course_id>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:course_id>/delete/", views.course_delete, name="course_delete"),

    # -----------------------------------------------------------------
    # Classes CRUD
    # -----------------------------------------------------------------
    path("classes/", views.classes_list, name="classes_list"),
    path("classes/create/", views.class_create, name="class_create"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),

    # -----------------------------------------------------------------
    # Subjects CRUD
    # -----------------------------------------------------------------
    path("subjects/", views.subjects_list, name="subjects_list"),
    path("subjects/create/", views.subject_create, name="subject_create"),
    path("subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),

    # -----------------------------------------------------------------
    # Semesters CRUD
    # -----------------------------------------------------------------
    path("semesters/", views.semesters_list, name="semesters_list"),
    path("semesters/create/", views.semester_create, name="semester_create"),
    path("semesters/<int:pk>/edit/", views.semester_edit, name="semester_edit"),
    path("semesters/<int:pk>/delete/", views.semester_delete, name="semester_delete"),

    # -----------------------------------------------------------------
    # Announcements CRUD
    # -----------------------------------------------------------------
    path("announcements/", views.announcements_list, name="announcements_list"),
    path("announcements/create/", views.announcement_create, name="announcement_create"),
    path("announcements/<int:pk>/edit/", views.announcement_edit, name="announcement_edit"),
    path("announcements/<int:pk>/delete/", views.announcement_delete, name="announcement_delete"),

    # -----------------------------------------------------------------
    # Events CRUD
    # -----------------------------------------------------------------
    path("events/", views.events_list, name="events_list"),
    path("events/create/", views.event_create, name="event_create"),
    path("events/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("events/<int:pk>/delete/", views.event_delete, name="event_delete"),

    # -----------------------------------------------------------------
    # Results & Reports
    # -----------------------------------------------------------------
    path("results/student/", views.student_results, name="student_results"),
    path("results/admin/pdf/", views.admin_results_pdf, name="admin_results_pdf"),
    path("results/teacher/<int:subject_id>/<int:class_id>/<int:semester_id>/pdf/",
         views.teacher_results_pdf, name="teacher_results_pdf"),
    path("results/class/<int:class_id>/<int:subject_id>/pdf/",
         views.class_marks_pdf, name="class_marks_pdf"),
    path("results/student/<int:student_id>/pdf/", views.student_report_pdf, name="student_report_pdf"),

    # -----------------------------------------------------------------
    # Marks
    # -----------------------------------------------------------------
    path("mark/upload/", views.upload_marks, name="upload_marks"),

    path("reports/", views.reports, name="reports"),
    path("reports/all/pdf/", views.all_reports_pdf, name="all_reports_pdf"),
# urls.py
    # urls.py
    path("teachers/register_subjects/", views.register_subjects, name="register_subjects"),
    path("teachers/delete_subject/<int:pk>/", views.delete_teacher_subject, name="delete_teacher_subject"),

    path("teachers/manage_subjects/", views.teacher_subjects_manage, name="teacher_subjects_manage"),
    path("teachers/results/", views.teachers_results, name="teachers_results"),
path("teachers/results/pdf/", views.teachers_results_pdf, name="teachers_results_pdf"),





]




