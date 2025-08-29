from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count

from .models import Sale, Visit, Return, Payment

@login_required
def agent_dashboard(request):
    agent = request.user
    today = timezone.now().date()

    # Aggregate stats
    sales = Sale.objects.filter(agent=agent, timestamp__date=today)
    visits = Visit.objects.filter(agent=agent, datetime__date=today)
    returns = Return.objects.filter(agent=agent, created_at__date=today)
    payments = Payment.objects.filter(sale__agent=agent, created_at__date=today)

    summary = {
        "total_sales": sales.aggregate(total=Count("id"))["total"] or 0,
        "total_revenue": sales.aggregate(rev=Sum("revenue"))["rev"] or 0,
        "visits": visits.count(),
        "returns": returns.count(),
        "payments": payments.aggregate(total=Sum("amount"))["total"] or 0,
    }

    # Recent activity
    recent_sales = sales.order_by("-timestamp")[:5]
    recent_visits = visits.order_by("-datetime")[:5]
    recent_returns = returns.order_by("-created_at")[:5]

    context = {
        "summary": summary,
        "recent_sales": recent_sales,
        "recent_visits": recent_visits,
        "recent_returns": recent_returns,
    }
    return render(request, "agent/agent_dashboard.html", context)



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from core.models import Visit, Sale, Return, Transfer, Payment


# -------------------
# LIST VIEWS WITH SEARCH
# -------------------
@login_required
def sale_list(request):
    query = request.GET.get("q", "")
    sales = Sale.objects.filter(agent=request.user).order_by("-timestamp")
    if query:
        sales = sales.filter(
            Q(pack__product__name__icontains=query) |
            Q(market__name__icontains=query) |
            Q(promo_code__code__icontains=query)
        )
    return render(request, "agent/sales_list.html", {"sales": sales, "query": query})


@login_required
def return_list(request):
    query = request.GET.get("q", "")
    returns = Return.objects.filter(agent=request.user).order_by("-created_at")
    if query:
        returns = returns.filter(
            Q(pack__product__name__icontains=query) |
            Q(reason_code__icontains=query)
        )
    return render(request, "agent/returns_list.html", {"returns": returns, "query": query})


@login_required
def transfer_list(request):
    query = request.GET.get("q", "")
    transfers = Transfer.objects.filter(from_agent=request.user).order_by("-created_at")
    if query:
        transfers = transfers.filter(
            Q(pack__product__name__icontains=query) |
            Q(to_agent__username__icontains=query) |
            Q(status__icontains=query)
        )
    return render(request, "agent/transfers_list.html", {"transfers": transfers, "query": query})


@login_required
def payment_list(request):
    query = request.GET.get("q", "")
    payments = Payment.objects.filter(sale__agent=request.user).order_by("-created_at")
    if query:
        payments = payments.filter(
            Q(method__icontains=query) |
            Q(status__icontains=query) |
            Q(transaction_ref__icontains=query)
        )
    return render(request, "agent/payments_list.html", {"payments": payments, "query": query})


# -------------------
# DELETE ACTIONS
# -------------------
@login_required
def sale_delete(request, pk):
    sale = get_object_or_404(Sale, pk=pk, agent=request.user)
    if request.method == "POST":
        sale.delete()
        messages.success(request, "Sale deleted successfully.")
        return redirect("agent:sale_list")
    return render(request, "agent/confirm_delete.html", {"object": sale, "type": "Sale"})


@login_required
def return_delete(request, pk):
    obj = get_object_or_404(Return, pk=pk, agent=request.user)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Return deleted successfully.")
        return redirect("agent:return_list")
    return render(request, "agent/confirm_delete.html", {"object": obj, "type": "Return"})
