from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.models import Market, Outlet, Role
from core.forms import MarketForm, OutletForm


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != Role.ADMIN:
            messages.error(request, "Unauthorized: Admins only")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return wrapper


# --- Market Views ---
@login_required
@admin_required
def market_list(request):
    markets = Market.objects.all().order_by("region", "name")
    return render(request, "markets/market_list.html", {"markets": markets})


@login_required
@admin_required
def market_add(request):
    if request.method == "POST":
        form = MarketForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Market added successfully.")
            return redirect("market_list")
    else:
        form = MarketForm()
    return render(request, "markets/market_form.html", {"form": form, "title": "Add Market"})


@login_required
@admin_required
def market_edit(request, pk):
    market = get_object_or_404(Market, pk=pk)
    if request.method == "POST":
        form = MarketForm(request.POST, instance=market)
        if form.is_valid():
            form.save()
            messages.success(request, "Market updated successfully.")
            return redirect("market_list")
    else:
        form = MarketForm(instance=market)
    return render(request, "markets/market_form.html", {"form": form, "title": "Edit Market"})


@login_required
@admin_required
def market_delete(request, pk):
    market = get_object_or_404(Market, pk=pk)
    market.delete()
    messages.success(request, "Market deleted.")
    return redirect("market_list")


# --- Outlet Views ---
@login_required
@admin_required
def outlet_list(request):
    outlets = Outlet.objects.select_related("market").all().order_by("market__name", "name")
    return render(request, "markets/outlet_list.html", {"outlets": outlets})


@login_required
@admin_required
def outlet_add(request):
    if request.method == "POST":
        form = OutletForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Outlet added successfully.")
            return redirect("outlet_list")
    else:
        form = OutletForm()
    return render(request, "markets/outlet_form.html", {"form": form, "title": "Add Outlet"})


@login_required
@admin_required
def outlet_edit(request, pk):
    outlet = get_object_or_404(Outlet, pk=pk)
    if request.method == "POST":
        form = OutletForm(request.POST, instance=outlet)
        if form.is_valid():
            form.save()
            messages.success(request, "Outlet updated successfully.")
            return redirect("outlet_list")
    else:
        form = OutletForm(instance=outlet)
    return render(request, "markets/outlet_form.html", {"form": form, "title": "Edit Outlet"})


@login_required
@admin_required
def outlet_delete(request, pk):
    outlet = get_object_or_404(Outlet, pk=pk)
    outlet.delete()
    messages.success(request, "Outlet deleted.")
    return redirect("outlet_list")
