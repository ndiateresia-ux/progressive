from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

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

# ---------------------------------------------------------------------
# Inlines for Mark (different fk_name per parent)
# ---------------------------------------------------------------------

class StudentMarkInline(admin.TabularInline):
    model = Mark
    fk_name = "student"
    extra = 0
    fields = ("subject", "teacher", "semester", "score", "date_recorded")
    readonly_fields = ("date_recorded",)

class TeacherMarkInline(admin.TabularInline):
    model = Mark
    fk_name = "teacher"
    extra = 0
    fields = ("subject", "student", "semester", "score", "date_recorded")
    readonly_fields = ("date_recorded",)

class ClassMarkInline(admin.TabularInline):
    model = Mark
    fk_name = "school_class"
    extra = 0
    fields = ("student", "subject", "teacher", "semester", "score", "date_recorded")
    readonly_fields = ("date_recorded",)

class SubjectMarkInline(admin.TabularInline):
    model = Mark
    fk_name = "subject"
    extra = 0
    fields = ("student", "teacher", "semester", "score", "date_recorded")
    readonly_fields = ("date_recorded",)

class SemesterMarkInline(admin.TabularInline):
    model = Mark
    fk_name = "semester"
    extra = 0
    fields = ("student", "subject", "teacher", "score", "date_recorded")
    readonly_fields = ("date_recorded",)

# ---------------------------------------------------------------------
# TeacherSubject Inline
# ---------------------------------------------------------------------

class TeacherSubjectInline(admin.TabularInline):
    model = TeacherSubject
    extra = 0
    fields = ("subject", "school_class")
    show_change_link = True

# ---------------------------------------------------------------------
# Custom Actions
# ---------------------------------------------------------------------

def export_marks_pdf(modeladmin, request, queryset):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=marks_export.pdf"

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Marks Export Report")

    y = height - 100
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Student")
    p.drawString(250, y, "Subject")
    p.drawString(400, y, "Score")
    y -= 20

    p.setFont("Helvetica", 11)
    for mark in queryset.select_related("student", "subject"):
        p.drawString(50, y, f"{mark.student.first_name} {mark.student.last_name}")
        p.drawString(250, y, mark.subject.name)
        p.drawString(400, y, str(mark.score))
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.showPage()
    p.save()
    return response
export_marks_pdf.short_description = "Export selected marks to PDF"

# ---------------------------------------------------------------------
# User Admin
# ---------------------------------------------------------------------

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username", "email", "first_name", "last_name",
        "role", "admission_number", "is_staff", "is_superuser"
    )
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "admission_number")
    fieldsets = UserAdmin.fieldsets + (
        ("Role Information", {"fields": ("role", "admission_number")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role Information", {"fields": ("role", "admission_number")}),
    )

    def get_inlines(self, request, obj=None):
        if obj and obj.role == "student":
            return [StudentMarkInline]
        elif obj and obj.role == "teacher":
            return [TeacherMarkInline, TeacherSubjectInline]
        return []

# ---------------------------------------------------------------------
# Academic Models
# ---------------------------------------------------------------------

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "department")
    list_filter = ("department",)
    search_fields = ("name",)

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "course")
    list_filter = ("course",)
    search_fields = ("name",)
    inlines = [ClassMarkInline, TeacherSubjectInline]

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "course")
    list_filter = ("course",)
    search_fields = ("name",)
    inlines = [SubjectMarkInline, TeacherSubjectInline]

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    list_filter = ("start_date", "end_date")
    search_fields = ("name",)
    inlines = [SemesterMarkInline]

# ---------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "visibility", "created_at")
    list_filter = ("visibility",)
    search_fields = ("title", "content")
    ordering = ("-created_at",)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "visibility")
    search_fields = ("title", "description")
    list_filter = ("visibility", "date")
    ordering = ("-date",)

# ---------------------------------------------------------------------
# Teaching Assignments
# ---------------------------------------------------------------------

@admin.register(TeacherSubject)
class TeacherSubjectAdmin(admin.ModelAdmin):
    list_display = ("teacher", "subject", "school_class")
    list_filter = ("teacher", "subject", "school_class")
    search_fields = ("teacher__first_name", "teacher__last_name", "subject__name", "school_class__name")

# ---------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------

@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "teacher", "school_class", "semester", "score", "date_recorded")
    list_filter = ("subject", "teacher", "school_class", "semester")
    search_fields = ("student__first_name", "student__last_name", "subject__name")
    ordering = ("-date_recorded",)
    actions = [export_marks_pdf]
