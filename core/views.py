from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

from .models import User
from .forms import UserRegistrationForm


def home(request):
    """Landing page (before login)."""
    return render(request, "home.html")


def register(request):
    """User signup form."""
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # auto login after registration
            messages.success(request, "Account created successfully!")
            return redirect("role_redirect")
    else:
        form = UserRegistrationForm()
    return render(request, "registration/register.html", {"form": form})

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm

def user_login(request):
    """Custom login view with role redirect."""
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("role_redirect")
            else:
                messages.error(request, "Invalid username or password")
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()
    return render(request, "registration/login.html", {"form": form})


@login_required
def user_logout(request):
    """Logout view."""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")

@login_required
def role_redirect(request):
    """Redirect users after login to correct dashboard."""
    if request.user.role == "admin":
        return redirect("admin_dashboard")
    elif request.user.role == "manager":
        return redirect("manager_dashboard")
    else:
        return redirect("agent_dashboard")


@login_required
def agent_dashboard(request):
    """Dashboard for Agents."""
    return render(request, "dashboards/agent_dashboard.html")


@login_required
def manager_dashboard(request):
    """Dashboard for Managers (with team list)."""
    team = User.objects.filter(manager=request.user)
    return render(request, "dashboards/manager_dashboard.html", {"team": team})


@login_required
def admin_dashboard(request):
    """Dashboard for Admins (manage users)."""
    users = User.objects.all()
    return render(request, "dashboards/admin_dashboard.html", {"users": users})
