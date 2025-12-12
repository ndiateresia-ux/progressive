from django.contrib import admin
from django.urls import path, include
from progressive_app import views

urlpatterns = [
    # Root URL → login page
    path("", views.custom_login, name="root_login"),

    # Django admin site
    path("admin/", admin.site.urls),

    # App routes
    path("", include("progressive_app.urls")),
]
