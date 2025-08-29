# core/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db.models import Count

from core.models import User, Role, Visit, Sale, Return, Transfer, Payment


# -------------------
# General
# -------------------
def home(request):
    """Landing page (before login)."""
    return render(request, "home.html")


def login_view(request):
    """Custom login with role-based redirection."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back {user.username}!")

            if user.role == Role.ADMIN:
                return redirect("admin_dashboard")
            elif user.role == Role.MANAGER:
                return redirect("manager_dashboard")
            elif user.role == Role.AGENT:
                return redirect("agent_dashboard")
            else:
                messages.error(request, "Your role is not recognized.")
                return redirect("login")
        else:
            messages.error(request, "Invalid username or password")
            return redirect("login")

    return render(request, "auth/login.html")


@login_required
def logout_view(request):
    """Logout user."""
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("login")


@login_required
def dashboard(request):
    """Redirect users to their dashboard by role."""
    if request.user.role == Role.ADMIN:
        return redirect("admin_dashboard")
    elif request.user.role == Role.MANAGER:
        return redirect("manager_dashboard")
    elif request.user.role == Role.AGENT:
        return redirect("agent_dashboard")
    else:
        messages.error(request, "No dashboard available for your role.")
        return redirect("home")


# -------------------
# Dashboards
# -------------------
@login_required
def admin_dashboard(request):
    if request.user.role != Role.ADMIN:
        messages.error(request, "Unauthorized access.")
        return redirect("home")

    stats = {
        "total_users": User.objects.count(),
        "total_agents": User.objects.filter(role=Role.AGENT).count(),
        "total_managers": User.objects.filter(role=Role.MANAGER).count(),
        "total_visits": Visit.objects.count(),
        "total_sales": Sale.objects.count(),
        "total_returns": Return.objects.count(),
    }
    return render(request, "dashboards/admin_dashboard.html", {"stats": stats})


@login_required
def manager_dashboard(request):
    return render(request, "dashboards/manager_dashboard.html")


@login_required
def agent_dashboard(request):
    return render(request, "dashboards/agent_dashboard.html")


# -------------------
# User Management (Admin Only)
# -------------------
@login_required
def add_user(request):
    """Admin can add Managers or Agents."""
    if request.user.role != Role.ADMIN:
        messages.error(request, "You don’t have permission to add users.")
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("add_user")

        user = User.objects.create(
            username=username,
            email=email,
            phone=phone,
            role=role,
            password=make_password(password),
        )
        messages.success(request, f"{role.title()} account for {username} created successfully!")
        return redirect("user_list")

    return render(request, "users/add_user.html")


@login_required
def user_list(request):
    """Admin view of all users."""
    if request.user.role != Role.ADMIN:
        messages.error(request, "Unauthorized access.")
        return redirect("dashboard")

    users = User.objects.all().order_by("-date_joined")
    return render(request, "users/user_list.html", {"users": users})
