from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),

    path("dashboard/", views.role_redirect, name="role_redirect"),
    path("dashboard/agent/", views.agent_dashboard, name="agent_dashboard"),
    path("dashboard/manager/", views.manager_dashboard, name="manager_dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
]
