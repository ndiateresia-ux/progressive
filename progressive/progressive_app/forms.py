# forms.py
from django import forms
from .models import TeacherSubject, Subject, SchoolClass

class TeacherSubjectForm(forms.ModelForm):
    class Meta:
        model = TeacherSubject
        fields = ["subject", "school_class"]
        widgets = {
            "subject": forms.Select(attrs={"class": "form-select"}),
            "school_class": forms.Select(attrs={"class": "form-select"}),
        }
