from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import AbstractUser

# ---------------------------------------------------------------------
# Custom User
# ---------------------------------------------------------------------

class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    admission_number = models.CharField(max_length=20, blank=True, null=True, unique=True)

    department = models.ForeignKey("Department", on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey("Course", on_delete=models.SET_NULL, null=True, blank=True)
    school_class = models.ForeignKey("SchoolClass", on_delete=models.SET_NULL, null=True, blank=True)
    semester = models.ForeignKey("Semester", on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


# ---------------------------------------------------------------------
# Academics
# ---------------------------------------------------------------------

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="courses")

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class SchoolClass(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="classes")

    def __str__(self):
        return f"{self.name} - {self.course.name}"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="subjects")

    def __str__(self):
        return self.name


class Semester(models.Model):
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------
# Announcements & Events
# ---------------------------------------------------------------------

class Announcement(models.Model):
    VISIBILITY_CHOICES = [
        ("all", "All"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="all")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Event(models.Model):
    VISIBILITY_CHOICES = [
        ("all", "All"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="all")

    def __str__(self):
        return f"{self.title} ({self.date})"


# ---------------------------------------------------------------------
# Marks & Teacher Assignments
# ---------------------------------------------------------------------

class TeacherSubject(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={"role": "teacher"})
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.subject.name} ({self.school_class.name})"


class Mark(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "student"}
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="given_marks",
        limit_choices_to={"role": "teacher"}
    )
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)

    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )

    grade = models.CharField(max_length=2, blank=True)

    date_recorded = models.DateTimeField(auto_now_add=True)

    def calculate_grade(self):
        try:
            score = float(self.score)
        except (ValueError, TypeError):
            return "F"

        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"

    def save(self, *args, **kwargs):
        if self.score not in [None, ""]:
            self.score = float(self.score)
            self.grade = self.calculate_grade()
        else:
            self.grade = None
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.student.get_full_name()} - "
            f"{self.subject.name}: {self.score} ({self.grade}) "
            f"by {self.teacher.get_full_name()}"
        )

