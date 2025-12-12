from datetime import datetime
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Sum, Count, Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa

from .forms import TeacherSubjectForm
from .models import (
    User,
    Department,
    Course,
    SchoolClass,
    Subject,
    Semester,
    Announcement,
    Event,
    TeacherSubject,
    Mark,
)
from .utilis import render_to_pdf


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def require_role(user, allowed_roles):
    return user.is_authenticated and user.role in allowed_roles

def forbid_or_redirect_login(request):
    messages.error(request, "You are not authorized to view this page.")
    return redirect("progressive_app:login")

def _next_admission_number():
    prefix = "prog"
    used = User.objects.filter(
        role="student", admission_number__startswith=prefix
    ).values_list("admission_number", flat=True)
    max_num = 0
    for adm in used:
        try:
            num = int(adm.replace(prefix, ""))
            max_num = max(max_num, num)
        except ValueError:
            continue
    return f"{prefix}{str(max_num + 1).zfill(4)}"

def _student_email(admission_number):
    return f"{admission_number}@progstudent.sch"

def get_grade_and_gpa(score):
    s = float(score)
    if s >= 90: return "A", 4.0
    if s >= 80: return "B", 3.0
    if s >= 70: return "C", 2.0
    if s >= 60: return "D", 1.0
    return "F", 0.0

# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------

def custom_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            return redirect("progressive_app:dashboard")
        messages.error(request, "Invalid email or password.")
        return redirect("progressive_app:login")
    return render(request, "login.html")

@login_required
def custom_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("progressive_app:login")

# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------

@login_required
def dashboard(request):
    user = request.user
    if user.role == "admin":
        context = {
            "title": "Admin Dashboard",
            "counts": {
                "departments": Department.objects.count(),
                "courses": Course.objects.count(),
                "classes": SchoolClass.objects.count(),
                "students": User.objects.filter(role="student").count(),
                "teachers": User.objects.filter(role="teacher").count(),
                "subjects": Subject.objects.count(),
                "semesters": Semester.objects.count(),
                "announcements": Announcement.objects.count(),
                "events": Event.objects.count(),
                "marks": Mark.objects.count(),
            },
            "announcements": Announcement.objects.order_by("-created_at")[:5],
            "events": Event.objects.order_by("-date")[:5],
        }
        return render(request, "dashboards/admin.html", context)

    if user.role == "teacher":
        assignments = (
            TeacherSubject.objects.filter(teacher=user)
            .select_related("subject", "school_class")
            .order_by("school_class__name", "subject__name")
        )
        context = {
            "title": "Teacher Dashboard",
            "teacher_subjects": assignments,
            "announcements": Announcement.objects.filter(
                Q(visibility="all") | Q(visibility="teacher")
            ).order_by("-created_at")[:5],
            "events": Event.objects.filter(
                Q(visibility="all") | Q(visibility="teacher")
            ).order_by("-date")[:5],
        }
        return render(request, "dashboards/teacher.html", context)

    # student
    marks = (
        Mark.objects.filter(student=user)
        .select_related("subject", "school_class", "semester")
        .order_by("-date_recorded")[:10]
    )
    context = {
        "title": "Student Dashboard",
        "marks": marks,
        "announcements": Announcement.objects.filter(
            Q(visibility="all") | Q(visibility="student")
        ).order_by("-created_at")[:5],
        "events": Event.objects.filter(
            Q(visibility="all") | Q(visibility="student")
        ).order_by("-date")[:5],
    }
    return render(request, "dashboards/student.html", context)

# ---------------------------------------------------------------------
# Students CRUD
# ---------------------------------------------------------------------

@login_required
def students_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    q = request.GET.get("q", "")
    qs = User.objects.filter(role="student").order_by("admission_number", "email")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(admission_number__icontains=q))
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "admin/students_list.html", {"page_obj": page_obj, "q": q})

@login_required
def student_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)

    admission_number = _next_admission_number()
    email = _student_email(admission_number)

    if request.method == "POST":
        student = User.objects.create_user(
            email=email,
            username=email,
            password=admission_number,
            role="student",
            admission_number=admission_number,
            first_name=request.POST.get("first_name", "").strip(),
            last_name=request.POST.get("last_name", "").strip(),
            department=get_object_or_404(Department, id=request.POST.get("department")),
            course=get_object_or_404(Course, id=request.POST.get("course")),
            school_class=get_object_or_404(SchoolClass, id=request.POST.get("school_class")),
            semester=get_object_or_404(Semester, id=request.POST.get("semester")),
        )
        messages.success(request, f"Student created: {student.first_name} {student.last_name}")
        return redirect("progressive_app:students_list")

    return render(request, "admin/student_form.html", {
        "form_title": "Register Student",
        "student": User(admission_number=admission_number, email=email),
        "departments": Department.objects.order_by("name"),
        "courses": Course.objects.order_by("name"),
        "classes": SchoolClass.objects.order_by("name"),
        "semesters": Semester.objects.order_by("start_date"),
    })

@login_required
def student_update(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    student = get_object_or_404(User, pk=pk, role="student")
    if request.method == "POST":
        student.first_name = request.POST.get("first_name", "").strip()
        student.last_name = request.POST.get("last_name", "").strip()
        student.department = get_object_or_404(Department, id=request.POST.get("department"))
        student.course = get_object_or_404(Course, id=request.POST.get("course"))
        student.school_class = get_object_or_404(SchoolClass, id=request.POST.get("school_class"))
        student.semester = get_object_or_404(Semester, id=request.POST.get("semester"))
        student.save()
        messages.success(request, f"Student {student.first_name} updated successfully.")
        return redirect("progressive_app:students_list")
    return render(request, "admin/student_form.html", {
        "form_title": "Edit Student",
        "student": student,
        "departments": Department.objects.order_by("name"),
        "courses": Course.objects.order_by("name"),
        "classes": SchoolClass.objects.order_by("name"),
        "semesters": Semester.objects.order_by("start_date"),
    })

@login_required
def student_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    student = get_object_or_404(User, pk=pk, role="student")
    if request.method == "POST":
        student.delete()
        messages.success(request, "Student deleted successfully.")
        return redirect("admin/students_list")
    return render(request, "admin/student_confirm_delete.html", {"student": student})

# ---------------------------------------------------------------------
# Teachers CRUD
# ---------------------------------------------------------------------

@login_required
def teachers_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    q = request.GET.get("q", "")
    qs = User.objects.filter(role="teacher").order_by("username", "email")
    if q:
        qs = qs.filter(
            Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "admin/teachers_list.html", {"page_obj": page_obj, "q": q})

@login_required
def teacher_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        department = get_object_or_404(Department, id=request.POST.get("department"))
        email = f"{first_name.lower()}{last_name.lower()}@progressive.sch"
        password = "1234"
        teacher = User.objects.create_user(
            email=email,
            username=email,
            password=password,
            role="teacher",
            first_name=first_name,
            last_name=last_name,
            department=department,
        )
        messages.success(
            request,
            f"Teacher {teacher.first_name} created. Email: {email}, Default Password: {password}"
        )
        return redirect("progressive_app:teachers_list")

    return render(request, "admin/teacher_form.html", {
        "form_title": "Add Teacher",
        "teacher": User(),
        "departments": Department.objects.order_by("name"),
    })

@login_required
def teacher_update(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    teacher = get_object_or_404(User, pk=pk, role="teacher")
    if request.method == "POST":
        teacher.first_name = request.POST.get("first_name", "").strip()
        teacher.last_name = request.POST.get("last_name", "").strip()
        teacher.department = get_object_or_404(Department, id=request.POST.get("department"))
        teacher.save()
        messages.success(request, "Teacher updated successfully.")
        return redirect("progressive_app:teachers_list")
    return render(request, "admin/teacher_form.html", {
        "form_title": "Edit Teacher",
        "teacher": teacher,
        "departments": Department.objects.order_by("name"),
    })

@login_required
def teacher_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    teacher = get_object_or_404(User, pk=pk, role="teacher")
    if request.method == "POST":
        teacher.delete()
        messages.success(request, "Teacher deleted successfully.")
        return redirect("progressive_app:teachers_list")
    return render(request, "admin/teacher_confirm_delete.html", {"teacher": teacher})

# ---------------------------------------------------------------------
# Admins list and CRUD
# ---------------------------------------------------------------------

@login_required
def admins_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    qs = User.objects.filter(role="admin").order_by("username", "email")
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "admin/admins_list.html", {"page_obj": page_obj})

@login_required
def admin_update(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    admin_user = get_object_or_404(User, pk=pk, role="admin")
    if request.method == "POST":
        admin_user.first_name = request.POST.get("first_name", "").strip()
        admin_user.last_name = request.POST.get("last_name", "").strip()
        admin_user.save()
        messages.success(request, "Admin updated successfully.")
        return redirect("progressive_app:admins_list")
    return render(request, "admin/admin_form.html", {"admin": admin_user, "form_title": "Edit Admin"})

@login_required
def admin_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    admin_user = get_object_or_404(User, pk=pk, role="admin")
    if request.method == "POST":
        admin_user.delete()
        messages.success(request, "Admin deleted successfully.")
        return redirect("progressive_app:admins_list")
    return render(request, "admin/admin_confirm_delete.html", {"admin": admin_user})

# ---------------------------------------------------------------------
# Departments CRUD
# ---------------------------------------------------------------------

@login_required
def departments_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    qs = Department.objects.order_by("name")
    return render(request, "admin/departments_list.html", {"departments": qs})

@login_required
def department_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Department name is required.")
            return redirect("progressive_app:department_create")
        Department.objects.create(name=name)
        messages.success(request, f"Department '{name}' created.")
        return redirect("progressive_app:departments_list")
    return render(request, "admin/department_form.html", {"form_title": "Add Department"})

@login_required
def department_edit(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Department name is required.")
            return redirect("progressive_app:department_edit", pk=pk)
        department.name = name
        department.save()
        messages.success(request, f"Department '{department.name}' updated.")
        return redirect("progressive_app:departments_list")
    return render(request, "admin/department_form.html", {"form_title": "Edit Department", "department": department})

@login_required
def department_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        department.delete()
        messages.success(request, "Department deleted successfully.")
        return redirect("progressive_app:departments_list")
    return render(request, "admin/department_confirm_delete.html", {"department": department})

# ---------------------------------------------------------------------
# Courses CRUD
# ---------------------------------------------------------------------

@login_required
def courses_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    qs = Course.objects.select_related("department").order_by("name")
    return render(request, "admin/courses_list.html", {"courses": qs})

@login_required
def course_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        department_id = request.POST.get("department")
        if not name or not department_id:
            messages.error(request, "Course name and department are required.")
            return redirect("progressive_app:course_create")
        department = get_object_or_404(Department, pk=department_id)
        Course.objects.create(name=name, department=department)
        messages.success(request, f"Course '{name}' created.")
        return redirect("progressive_app:courses_list")
    return render(request, "admin/course_form.html", {
        "form_title": "Add Course",
        "course": Course(),
        "departments": Department.objects.order_by("name"),
    })

@login_required
def course_edit(request, course_id):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    course = get_object_or_404(Course, pk=course_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        department_id = request.POST.get("department")
        if not name or not department_id:
            messages.error(request, "Course name and department are required.")
            return redirect("progressive_app:course_edit", course_id=course.id)
        course.name = name
        course.department = get_object_or_404(Department, pk=department_id)
        course.save()
        messages.success(request, f"Course '{course.name}' updated.")
        return redirect("progressive_app:courses_list")
    return render(request, "admin/course_form.html", {
        "form_title": "Edit Course",
        "course": course,
        "departments": Department.objects.order_by("name"),
    })

@login_required
def course_delete(request, course_id):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    course = get_object_or_404(Course, pk=course_id)
    if request.method == "POST":
        course.delete()
        messages.success(request, f"Course deleted successfully.")
        return redirect("progressive_app:courses_list")
    return render(request, "admin/course_confirm_delete.html", {"course": course})

# ---------------------------------------------------------------------
# Classes CRUD
# ---------------------------------------------------------------------

@login_required
def classes_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    qs = SchoolClass.objects.select_related("course").order_by("name")
    return render(request, "admin/classes_list.html", {"classes": qs})

@login_required
def class_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        course_id = request.POST.get("course")
        if not name or not course_id:
            messages.error(request, "Class name and course are required.")
            return redirect("progressive_app:class_create")
        course = get_object_or_404(Course, pk=course_id)
        SchoolClass.objects.create(name=name, course=course)
        messages.success(request, f"Class '{name}' created.")
        return redirect("progressive_app:classes_list")
    return render(request, "admin/class_form.html", {
        "form_title": "Add Class",
        "school_class": SchoolClass(),
        "courses": Course.objects.order_by("name"),
    })

@login_required
def class_edit(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    school_class = get_object_or_404(SchoolClass, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        course_id = request.POST.get("course")
        if not name or not course_id:
            messages.error(request, "Class name and course are required.")
            return redirect("progressive_app:class_edit", pk=pk)
        school_class.name = name
        school_class.course = get_object_or_404(Course, pk=course_id)
        school_class.save()
        messages.success(request, f"Class '{school_class.name}' updated.")
        return redirect("progressive_app:classes_list")
    return render(request, "admin/class_form.html", {
        "form_title": "Edit Class",
        "school_class": school_class,
        "courses": Course.objects.order_by("name"),
    })

@login_required
def class_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    school_class = get_object_or_404(SchoolClass, pk=pk)
    if request.method == "POST":
        school_class.delete()
        messages.success(request, "Class deleted successfully.")
        return redirect("progressive_app:classes_list")
    return render(request, "admin/class_confirm_delete.html", {"school_class": school_class})

# ---------------------------------------------------------------------
# Subjects CRUD
# ---------------------------------------------------------------------

@login_required
def subjects_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    qs = Subject.objects.select_related("course").order_by("name")
    return render(request, "admin/subjects_list.html", {"subjects": qs})

@login_required
def subject_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        course_id = request.POST.get("course")
        if not name or not course_id:
            messages.error(request, "Subject name and course are required.")
            return redirect("progressive_app:subject_create")
        course = get_object_or_404(Course, id=course_id)
        Subject.objects.create(name=name, course=course)
        messages.success(request, f"Subject '{name}' created.")
        return redirect("progressive_app:subjects_list")
    return render(request, "admin/subject_form.html", {
        "form_title": "Add Subject",
        "subject": Subject(),
        "courses": Course.objects.order_by("name"),
    })

@login_required
def subject_edit(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        course_id = request.POST.get("course")
        if not name or not course_id:
            messages.error(request, "Subject name and course are required.")
            return redirect("progressive_app:subject_edit", pk=pk)
        subject.name = name
        subject.course = get_object_or_404(Course, pk=course_id)
        subject.save()
        messages.success(request, "Subject updated successfully.")
        return redirect("progressive_app:subjects_list")
    return render(request, "admin/subject_form.html", {
        "form_title": "Edit Subject",
        "subject": subject,
        "courses": Course.objects.order_by("name"),
    })

@login_required
def subject_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        subject.delete()
        messages.success(request, "Subject deleted successfully.")
        return redirect("progressive_app:subjects_list")
    return render(request, "admin/subject_confirm_delete.html", {"subject": subject})

# ---------------------------------------------------------------------
# Semesters CRUD
# ---------------------------------------------------------------------

@login_required
def semesters_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    qs = Semester.objects.order_by("-start_date")
    return render(request, "admin/semesters_list.html", {"semesters": qs})

@login_required
def semester_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        start_date = request.POST.get("start_date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        if not name or not start_date or not end_date:
            messages.error(request, "Name, start date, and end date are required.")
            return redirect("progressive_app:semester_create")
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d").date()
            ed = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Dates must be in YYYY-MM-DD format.")
            return redirect("progressive_app:semester_create")
        if sd > ed:
            messages.error(request, "Start date cannot be after end date.")
            return redirect("progressive_app:semester_create")
        Semester.objects.create(name=name, start_date=sd, end_date=ed)
        messages.success(request, f"Semester '{name}' created.")
        return redirect("progressive_app:semesters_list")
    return render(request, "admin/semester_form.html", {"form_title": "Add Semester"})

@login_required
def semester_edit(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        start_date = request.POST.get("start_date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        if not name or not start_date or not end_date:
            messages.error(request, "Name, start date, and end date are required.")
            return redirect("progressive_app:semester_edit", pk=pk)
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d").date()
            ed = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Dates must be in YYYY-MM-DD format.")
            return redirect("progressive_app:semester_edit", pk=pk)
        if sd > ed:
            messages.error(request, "Start date cannot be after end date.")
            return redirect("progressive_app:semester_edit", pk=pk)
        semester.name = name
        semester.start_date = sd
        semester.end_date = ed
        semester.save()
        messages.success(request, "Semester updated successfully.")
        return redirect("progressive_app:semesters_list")
    return render(request, "admin/semester_form.html", {"form_title": "Edit Semester", "semester": semester})

@login_required
def semester_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == "POST":
        semester.delete()
        messages.success(request, "Semester deleted successfully.")
        return redirect("progressive_app:semesters_list")
    return render(request, "admin/semester_confirm_delete.html", {"semester": semester})

# ---------------------------------------------------------------------
# Announcements CRUD
# ---------------------------------------------------------------------

@login_required
def announcements_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    qs = Announcement.objects.order_by("-created_at")
    return render(request, "admin/announcements_list.html", {"announcements": qs})

@login_required
def announcement_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        visibility = request.POST.get("visibility", "all")
        Announcement.objects.create(title=title, content=content, visibility=visibility)
        messages.success(request, "Announcement created.")
        return redirect("progressive_app:announcements_list")
    return render(request, "admin/announcement_form.html", {"form_title": "Create Announcement"})

@login_required
def announcement_edit(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        announcement.title = request.POST.get("title", "").strip()
        announcement.content = request.POST.get("content", "").strip()
        announcement.visibility = request.POST.get("visibility", "all")
        announcement.save()
        messages.success(request, "Announcement updated.")
        return redirect("progressive_app:announcements_list")
    return render(request, "admin/announcement_form.html", {"form_title": "Edit Announcement", "announcement": announcement})

@login_required
def announcement_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        announcement.delete()
        messages.success(request, "Announcement deleted.")
        return redirect("progressive_app:announcements_list")
    return render(request, "admin/announcement_confirm_delete.html", {"announcement": announcement})

# ---------------------------------------------------------------------
# Events CRUD
# ---------------------------------------------------------------------

@login_required
def events_list(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    qs = Event.objects.order_by("-date")
    return render(request, "admin/events_list.html", {"events": qs})

@login_required
def event_create(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        date = request.POST.get("date", "").strip()
        visibility = request.POST.get("visibility", "all")
        Event.objects.create(title=title, description=description, date=date, visibility=visibility)
        messages.success(request, "Event created.")
        return redirect("progressive_app:events_list")
    return render(request, "admin/event_form.html", {"form_title": "Create Event"})

@login_required
def event_edit(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        event.title = request.POST.get("title", "").strip()
        event.description = request.POST.get("description", "").strip()
        event.date = request.POST.get("date", "").strip()
        event.visibility = request.POST.get("visibility", "all")
        event.save()
        messages.success(request, "Event updated.")
        return redirect("progressive_app:events_list")
    return render(request, "admin/event_form.html", {"form_title": "Edit Event", "event": event})

@login_required
def event_delete(request, pk):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        event.delete()
        messages.success(request, "Event deleted.")
        return redirect("progressive_app:events_list")
    return render(request, "admin/event_confirm_delete.html", {"event": event})

# ---------------------------------------------------------------------
# Teacher: register subjects to classes (TeacherSubject)
# ---------------------------------------------------------------------

@login_required
def teacher_subjects_manage(request):
    if not require_role(request.user, ["teacher", "admin"]):
        return forbid_or_redirect_login(request)

    context = {
        "subjects": Subject.objects.select_related("course").order_by("name"),
        "classes": SchoolClass.objects.select_related("course").order_by("name"),
        "teachers": User.objects.filter(role="teacher").order_by("username"),
        "is_admin": request.user.role == "admin",
    }

    if request.method == "POST":
        subject_id = request.POST.get("subject_id")
        class_id = request.POST.get("class_id")
        subject = get_object_or_404(Subject, id=subject_id)
        school_class = get_object_or_404(SchoolClass, id=class_id)
        teacher = request.user
        if request.user.role == "admin":
            teacher_id = request.POST.get("teacher_id")
            teacher = get_object_or_404(User, id=teacher_id, role="teacher")
        TeacherSubject.objects.get_or_create(
            teacher=teacher, subject=subject, school_class=school_class
        )
        messages.success(request, "Teaching assignment saved.")
        return redirect("progressive_app:teacher_subjects_manage")

    existing = TeacherSubject.objects.select_related("teacher", "subject", "school_class")
    if request.user.role == "teacher":
        existing = existing.filter(teacher=request.user)

    context["existing"] = existing
    return render(request, "teachers/teacher_subjects_manage.html", context)

# ---------------------------------------------------------------------
# Marks: upload by teacher/admin
# ---------------------------------------------------------------------

@login_required
def upload_marks(request):
    if not require_role(request.user, ["teacher", "admin"]):
        return forbid_or_redirect_login(request)

    registrations = (
        TeacherSubject.objects.filter(teacher=request.user)
        if request.user.role == "teacher"
        else TeacherSubject.objects.all()
    )

    students = None
    selected_class = None
    selected_subject = None
    selected_semester = None
    teacher = request.user

    if request.method == "POST":
        subject_id = request.POST.get("subject")
        class_id = request.POST.get("school_class")
        semester_id = request.POST.get("semester")

        if subject_id and class_id and semester_id:
            selected_subject = get_object_or_404(Subject, id=subject_id)
            selected_class = get_object_or_404(SchoolClass, id=class_id)
            selected_semester = get_object_or_404(Semester, id=semester_id)

            if request.user.role == "admin":
                teacher_id = request.POST.get("teacher_id")
                if teacher_id:
                    teacher = get_object_or_404(User, id=teacher_id, role="teacher")

            if not TeacherSubject.objects.filter(
                teacher=teacher, subject=selected_subject, school_class=selected_class
            ).exists():
                messages.error(request, "This teacher is not registered to teach this subject in this class.")
                return redirect("progressive_app:upload_marks")

            students = User.objects.filter(role="student", school_class=selected_class)

            if "save_marks" in request.POST:
                for student in students:
                    score_value = request.POST.get(f"marks_{student.id}")
                    if score_value not in (None, ""):
                        Mark.objects.update_or_create(
                            student=student,
                            subject=selected_subject,
                            teacher=teacher,
                            school_class=selected_class,
                            semester=selected_semester,
                            defaults={"score": score_value},
                        )
                messages.success(
                    request,
                    f"Marks uploaded for {selected_class.name} ({selected_subject.name}) in {selected_semester.name}."
                )
                return redirect("progressive_app:teachers_results")

    return render(request, "upload_marks.html", {
        "form_title": "Upload Marks",
        "registrations": registrations,
        "students": students,
        "selected_class": selected_class,
        "selected_subject": selected_subject,
        "selected_semester": selected_semester,
        "semesters": Semester.objects.all(),
        "teachers": User.objects.filter(role="teacher") if request.user.role == "admin" else None,
    })

# ---------------------------------------------------------------------
# Results & Reports
# ---------------------------------------------------------------------

@login_required
def student_results(request):
    if request.user.role != "student":
        messages.error(request, "Access denied.")
        return redirect("progressive_app:dashboard")
    marks = Mark.objects.filter(student=request.user).select_related(
        "subject", "school_class", "semester", "teacher"
    )
    return render(request, "students/results.html", {"marks": marks})

@login_required
def student_report(request, student_id):
    if not require_role(request.user, ["admin", "teacher", "student"]):
        return forbid_or_redirect_login(request)
    student = get_object_or_404(User, pk=student_id, role="student")
    marks = Mark.objects.filter(student=student).select_related("subject", "teacher", "semester")
    for m in marks:
        grade, gpa = get_grade_and_gpa(m.score)
        m.grade = grade
        m.gpa = gpa
    total_score = marks.aggregate(total=Sum("score"))["total"] or 0
    average_score = marks.aggregate(avg=Avg("score"))["avg"] or 0
    subjects_count = marks.aggregate(count=Count("subject", distinct=True))["count"] or 0
    return render(request, "reports/student_reports.html", {
        "student": student,
        "marks": marks,
        "total_marks": total_score,
        "average_marks": round(average_score, 2),
        "subjects_count": subjects_count,
    })

@login_required
def student_results_download(request, student_id):
    student = get_object_or_404(User, pk=student_id, role="student")
    marks = Mark.objects.filter(student=student).select_related("subject", "semester", "teacher")

    total_score = marks.aggregate(total=Sum("score"))["total"] or 0
    average_score = marks.aggregate(avg=Avg("score"))["avg"] or 0
    subjects_count = marks.aggregate(count=Count("subject", distinct=True))["count"] or 0

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{student.username}_results.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Student Report Card")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"Name: {student.first_name} {student.last_name}")
    p.drawString(50, height - 100, f"Admission No: {student.admission_number or ''}")
    p.drawString(50, height - 120, f"Email: {student.email}")
    if student.school_class:
        p.drawString(50, height - 140, f"Class: {student.school_class.name}")

    y = height - 180
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Total Marks: {total_score}")
    p.drawString(250, y, f"Average Marks: {round(average_score, 2)}")
    p.drawString(450, y, f"Subjects Count: {subjects_count}")

    y -= 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Subject")
    p.drawString(200, y, "Semester")
    p.drawString(350, y, "Teacher")
    p.drawString(500, y, "Score")

    p.setFont("Helvetica", 11)
    y -= 20
    for mark in marks:
        p.drawString(50, y, mark.subject.name)
        p.drawString(200, y, mark.semester.name)
        p.drawString(350, y, f"{mark.teacher.first_name} {mark.teacher.last_name}")
        p.drawString(500, y, str(mark.score))
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.showPage()
    p.save()
    return response

@login_required
def class_marks_pdf(request, class_id, subject_id):
    if request.user.role != "teacher":
        messages.error(request, "Access denied.")
        return redirect("progressive_app:dashboard")

    school_class = get_object_or_404(SchoolClass, pk=class_id)
    subject = get_object_or_404(Subject, pk=subject_id)

    # ensure teacher is assigned to this subject/class
    if not TeacherSubject.objects.filter(
        teacher=request.user, subject=subject, school_class=school_class
    ).exists():
        messages.error(request, "Not authorized for this class/subject.")
        return redirect("progressive_app:dashboard")

    marks = Mark.objects.filter(
        school_class=school_class, subject=subject, teacher=request.user
    ).select_related("student")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="class_{school_class.id}_{subject.name}_marks.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Marks Report - {school_class.name} ({subject.name})")

    y = height - 100
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Student")
    p.drawString(300, y, "Score")
    y -= 20

    p.setFont("Helvetica", 12)
    for mark in marks:
        p.drawString(50, y, f"{mark.student.first_name} {mark.student.last_name}")
        p.drawString(300, y, str(mark.score))
        y -= 20
        if y < 100:
            p.showPage()
            y = height - 100

    p.showPage()
    p.save()
    return response

@login_required
def teacher_results_pdf(request, subject_id, class_id, semester_id):
    if request.user.role != "teacher":
        return forbid_or_redirect_login(request)

    assignment_exists = TeacherSubject.objects.filter(
        teacher=request.user, subject_id=subject_id, school_class_id=class_id
    ).exists()
    if not assignment_exists:
        return HttpResponse("Not authorized for this class/subject", status=403)

    marks = Mark.objects.filter(
        subject_id=subject_id,
        school_class_id=class_id,
        semester_id=semester_id,
        teacher=request.user,
    ).select_related("student", "subject", "school_class", "semester")

    subject = get_object_or_404(Subject, id=subject_id)
    school_class = get_object_or_404(SchoolClass, id=class_id)
    semester = get_object_or_404(Semester, id=semester_id)

    template = get_template("teachers/teachers_results_pdf.html")
    html = template.render({
        "marks": marks,
        "subject": subject,
        "school_class": school_class,
        "semester": semester,
        "teacher": request.user,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="results_{subject.name}_{school_class.name}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)
    return response

@login_required
def admin_results_pdf(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)

    semester_id = request.GET.get("semester_id")
    subject_id = request.GET.get("subject_id")
    class_id = request.GET.get("class_id")
    student_id = request.GET.get("student_id")

    marks = Mark.objects.all().select_related("student", "subject", "school_class", "semester")

    if semester_id:
        marks = marks.filter(semester_id=semester_id)
    if subject_id:
        marks = marks.filter(subject_id=subject_id)
    if class_id:
        marks = marks.filter(school_class_id=class_id)
    if student_id:
        marks = marks.filter(student_id=student_id)

    template = get_template("admin_results_pdf.html")
    html = template.render({"marks": marks})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=consolidated_results.pdf"

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)
    return response

# ---------------------------------------------------------------------
# Teacher view: results listing (filterable)
# ---------------------------------------------------------------------

@login_required
def teachers_results(request):
    if request.user.role != "teacher":
        messages.error(request, "Access denied.")
        return redirect("progressive_app:dashboard")

    subject_id = request.GET.get("subject")
    class_id = request.GET.get("class")
    semester_id = request.GET.get("semester")

    assignments = TeacherSubject.objects.filter(teacher=request.user)
    class_ids = assignments.values_list("school_class_id", flat=True)
    subject_ids = assignments.values_list("subject_id", flat=True)

    marks = Mark.objects.filter(teacher=request.user).select_related(
        "student", "subject", "school_class", "semester"
    ).filter(
        school_class_id__in=class_ids,
        subject_id__in=subject_ids
    )

    if subject_id:
        marks = marks.filter(subject_id=subject_id)
    if class_id:
        marks = marks.filter(school_class_id=class_id)
    if semester_id:
        marks = marks.filter(semester_id=semester_id)

    context = {
        "marks": marks,
        "teacher": request.user,
        "subjects": Subject.objects.filter(id__in=subject_ids),
        "classes": SchoolClass.objects.filter(id__in=class_ids),
        "semesters": Semester.objects.all(),
    }
    return render(request, "teachers/teachers_results.html", context)

# ---------------------------------------------------------------------
# Profile & Settings
# ---------------------------------------------------------------------

@login_required
def profile_settings(request):
    user = request.user
    if request.method == "POST":
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.save()
        messages.success(request, "Profile updated.")
        return redirect("progressive_app:profile_settings")
    return render(request, "settings/profile_settings.html")

@login_required
def system_settings(request):
    if not require_role(request.user, ["admin"]):
        return forbid_or_redirect_login(request)
    return render(request, "settings/system_settings.html")

@login_required
def reports(request):
    return render(request, "reports/all_reports_pdf.html")
@login_required
def student_report_pdf(request, student_id):
    # simply reuse the existing PDF generator
    return student_results_download(request, student_id)


@login_required
def all_reports_pdf(request):
    # Pull ALL marks in the system
    mark = Mark.objects.select_related("student", "subject", "school_class", "semester").all()

    context = {"mark": mark}
    pdf = render_to_pdf("reports/all_reports_pdf.html", context)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=all_reports.pdf"
    return
@login_required
def all_reports_pdf(request):
    mark = Mark.objects.select_related(
        "student", "subject", "school_class", "semester", "department", "course"
    ).all()

    context = {"mark": mark}
    pdf = render_to_pdf("reports/all_reports_pdf.html", context)

    if pdf:
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=all_reports.pdf"
        return response
    return HttpResponse("Error generating PDF", status=500)

@login_required
def register_subjects(request):
    if request.user.role != "teacher":
        return redirect("progressive_app:dashboard")

    # Fetch subjects and classes from DB
    subjects = Subject.objects.select_related("course").all()
    classes = SchoolClass.objects.all()

    # Fetch already registered subjects for this teacher
    registered = TeacherSubject.objects.filter(teacher=request.user)

    if request.method == "POST":
        subject_id = request.POST.get("subject")
        class_id = request.POST.get("school_class")

        if subject_id and class_id:
            TeacherSubject.objects.get_or_create(
                teacher=request.user,
                subject_id=subject_id,
                school_class_id=class_id
            )
            return redirect("progressive_app:register_subjects")

    context = {
        "subjects": subjects,
        "classes": classes,
        "registered": registered,
    }
    return render(request, "teachers/register_subjects.html", context)


@login_required
def delete_teacher_subject(request, pk):
    if request.user.role != "teacher":
        return redirect("progressive_app:dashboard")

    ts = get_object_or_404(TeacherSubject, pk=pk, teacher=request.user)

    if request.method == "POST":
        ts.delete()
        return redirect("progressive_app:register_subjects")

@login_required
def teachers_results(request):
    if request.user.role != "teacher":
        return redirect("progressive_app:dashboard")

    # Base queryset: all marks uploaded by this teacher
    marks = Mark.objects.filter(teacher=request.user)

    # Apply filters from GET parameters
    subject_id = request.GET.get("subject")
    class_id = request.GET.get("class")
    semester_id = request.GET.get("semester")

    if subject_id:
        marks = marks.filter(subject_id=subject_id)
    if class_id:
        marks = marks.filter(school_class_id=class_id)
    if semester_id:
        marks = marks.filter(semester_id=semester_id)

    context = {
        "marks": marks,
        "subjects": Subject.objects.all(),
        "classes": SchoolClass.objects.all(),
        "semesters": Semester.objects.all(),
    }
    return render(request, "teachers/teachers_results.html", context)
@login_required
def teachers_results_pdf(request):
    if request.user.role != "teacher":
        return redirect("progressive_app:dashboard")

    mark = Mark.objects.filter(teacher=request.user)

    context = {"marks": mark}
    pdf = render_to_pdf("teachers/teachers_results_pdf.html", context)

    if pdf:
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=teacher_results.pdf"
        return response
    return HttpResponse("Error generating PDF", status=500)
