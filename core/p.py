Below is a ready‑to‑drop scaffold for the **Agent** side of TTDMS. It includes:

* A role gate (`role_required`) and a small security mixin
* Agent dashboard view + KPIs
* Agent quick‑action views (Log Visit, Record Sale, Request Transfer, File Return)
* Forms for Visit, Sale, Transfer, Return (with basic helpers)
* URL routes (namespaced under `agent/`)
* Templates with a responsive **sidenav** layout
* Notes for settings, project urls, and small conveniences

Copy each file into the indicated path. All template paths assume your Django `TEMPLATES[0]['DIRS']` already points at `templates/`.

---

## 0) **Settings checklist (important)**

```python
# settings.py

# Use your custom user
AUTH_USER_MODEL = "core.User"

# Where to send unauthenticated users
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "role_redirect"
LOGOUT_REDIRECT_URL = "home"

# Messages (optional but used throughout)
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: "debug",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

# Timezone
USE_TZ = True
TIME_ZONE = "Africa/Nairobi"
```

> **Migrations gotcha:** If you previously migrated with the default `auth.User`, delete the DB and migrations (if safe) or create a fresh DB so that `AUTH_USER_MODEL = "core.User"` is in place **before** running the first migration to avoid the `auth.User.groups` clash.

---

## 1) **Role gate**

**`core/decorators.py`**

```python
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login


def role_required(*allowed_roles):
    """Require that request.user.role is in allowed_roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in allowed_roles:
                raise PermissionDenied("You do not have access to this area.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
```

(If you prefer CBVs, you can add a mixin later; for now we’ll keep FBVs simple.)

---

## 2) **Forms**

**`core/forms.py`** (append these below your existing `UserRegistrationForm`)

```python
from django import forms
from django.utils import timezone
from django.db.models import Q

from .models import (
    Visit, Sale, Transfer, Return, Attachment,
    PackSize, PriceList, Campaign, PromoCode, Market, Outlet,
    PaymentStatus, PriceListStatus
)


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ["market", "outlet", "datetime", "purpose", "notes"]
        widgets = {
            "datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Limit choices to user's region if you wish; for now show all
        self.fields["market"].queryset = Market.objects.all().order_by("region", "name")
        self.fields["outlet"].queryset = Outlet.objects.all().order_by("market__name", "name")


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            "market", "visit", "pack", "quantity",
            "unit_price", "discount_amount", "promo_code", "campaign",
        ]
        widgets = {
            "discount_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["market"].queryset = Market.objects.all().order_by("region", "name")
        self.fields["visit"].queryset = Visit.objects.none() if user is None else Visit.objects.filter(agent=user)
        self.fields["pack"].queryset = PackSize.objects.filter(is_active=True).select_related("product").order_by("product__name", "label")
        self.fields["campaign"].required = False
        self.fields["promo_code"].required = False

    @staticmethod
    def active_price_for_pack(pack: PackSize, on_date=None):
        on_date = on_date or timezone.localdate()
        return (
            PriceList.objects
            .filter(
                pack=pack,
                status=PriceListStatus.ACTIVE,
                effective_from__lte=on_date,
            )
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=on_date))
            .order_by("-effective_from")
            .first()
        )


class TransferRequestForm(forms.ModelForm):
    class Meta:
        model = Transfer
        fields = ["to_agent", "to_market", "pack", "quantity", "reason"]
        widgets = {"reason": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Only allow transferring to other agents
        if user is not None:
            self.fields["to_agent"].queryset = user.__class__.objects.filter(role="agent").exclude(id=user.id)
        self.fields["pack"].queryset = PackSize.objects.filter(is_active=True).order_by("product__name", "label")
        self.fields["to_market"].required = False
        self.fields["to_agent"].required = False


class ReturnForm(forms.ModelForm):
    # Let user upload multiple files; we'll create Attachment objects in the view
    files = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={"multiple": True}))

    class Meta:
        model = Return
        fields = ["pack", "quantity", "reason_code"]
        widgets = {"reason_code": forms.TextInput(attrs={"placeholder": "e.g., damaged, expired"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pack"].queryset = PackSize.objects.filter(is_active=True).order_by("product__name", "label")
```

---

## 3) **Agent views**

> We keep these in a separate module to stay tidy.

**`core/views_agent.py`**

```python
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import role_required
from .forms import VisitForm, SaleForm, TransferRequestForm, ReturnForm
from .models import (
    Visit, Sale, Transfer, Return, Payment, StockLedger,
    PaymentStatus
)


@login_required
@role_required("agent")
def dashboard(request):
    user = request.user
    today = timezone.localdate()

    visits_today = Visit.objects.filter(agent=user, datetime__date=today).count()
    sales_today_qs = Sale.objects.filter(agent=user, timestamp__date=today)
    units_today = sales_today_qs.aggregate(total=Sum("quantity"))['total'] or 0
    revenue_today = sales_today_qs.aggregate(total=Sum("revenue"))['total'] or 0

    pending_amount = (
        Payment.objects
        .filter(sale__agent=user, status=PaymentStatus.PENDING)
        .aggregate(total=Sum("amount"))['total'] or 0
    )

    recent_visits = Visit.objects.filter(agent=user).select_related("market", "outlet").order_by("-datetime")[:5]
    recent_sales = (Sale.objects
                    .filter(agent=user)
                    .select_related("market", "pack__product")
                    .order_by("-timestamp")[:5])

    # Try to show a small stock snapshot if ledger has balances
    stock_rows = []
    try:
        from django.db.models import Max
        snap = (
            StockLedger.objects
            .filter(agent=user)
            .values("product__name", "pack__label")
            .annotate(balance=Max("balance_after"))
            .order_by("product__name", "pack__label")
        )
        stock_rows = list(snap[:8])  # keep it short on the dashboard
    except Exception:
        stock_rows = []

    ctx = dict(
        visits_today=visits_today,
        units_today=units_today,
        revenue_today=revenue_today,
        pending_amount=pending_amount,
        recent_visits=recent_visits,
        recent_sales=recent_sales,
        stock_rows=stock_rows,
        today=today,
    )
    return render(request, "agent/dashboard.html", ctx)


@login_required
@role_required("agent")
def visit_create(request):
    if request.method == "POST":
        form = VisitForm(request.POST, user=request.user)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.agent = request.user
            visit.save()
            messages.success(request, "Visit logged.")
            return redirect("agent_dashboard")
    else:
        form = VisitForm(user=request.user)
    return render(request, "agent/visit_form.html", {"form": form})


@login_required
@role_required("agent")
def sale_create(request):
    if request.method == "POST":
        form = SaleForm(request.POST, user=request.user)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.agent = request.user
            sale.timestamp = timezone.now()
            sale.save()
            messages.success(request, "Sale recorded.")
            return redirect("agent_dashboard")
    else:
        form = SaleForm(user=request.user)
    return render(request, "agent/sale_form.html", {"form": form})


@login_required
@role_required("agent")
def transfer_request(request):
    if request.method == "POST":
        form = TransferRequestForm(request.POST, user=request.user)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.from_agent = request.user
            transfer.status = "pending"
            transfer.save()
            messages.success(request, "Transfer request submitted.")
            return redirect("agent_dashboard")
    else:
        form = TransferRequestForm(user=request.user)
    return render(request, "agent/transfer_form.html", {"form": form})


@login_required
@role_required("agent")
def return_create(request):
    if request.method == "POST":
        form = ReturnForm(request.POST, request.FILES)
        if form.is_valid():
            ret = form.save(commit=False)
            ret.agent = request.user
            ret.status = "pending"
            ret.save()

            # Handle multiple file uploads -> Attachment objects and link to Return
            files = request.FILES.getlist("files")
            if files:
                from .models import Attachment
                for f in files:
                    att = Attachment.objects.create(file=f, owner=request.user, associated_type="return", associated_id=ret.id)
                    ret.attachments.add(att)

            messages.success(request, "Return filed.")
            return redirect("agent_dashboard")
    else:
        form = ReturnForm()
    return render(request, "agent/return_form.html", {"form": form})
```

---

## 4) **URLs**

**`core/urls.py`** (add an `agent/` section; keep your existing auth routes)

```python
from django.urls import path
from . import views
from . import views_agent

urlpatterns = [
    # existing routes
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("redirect/", views.role_redirect, name="role_redirect"),

    # Agent area
    path("agent/", views_agent.dashboard, name="agent_dashboard"),
    path("agent/visit/new/", views_agent.visit_create, name="agent_visit_new"),
    path("agent/sale/new/", views_agent.sale_create, name="agent_sale_new"),
    path("agent/transfer/new/", views_agent.transfer_request, name="agent_transfer_new"),
    path("agent/return/new/", views_agent.return_create, name="agent_return_new"),
]
```

**`project/urls.py`** (ensure it includes the app urls)

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
```

---

## 5) **Templates**

### 5.1 Base layout with sidenav

**`templates/agent/base_agent.html`**

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{% block title %}Agent — TTDMS{% endblock %}</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root { --bg: #0d6efd; --fg: #111; --muted:#6b7280; --card:#fff; --chip:#f3f4f6; }
    *{box-sizing:border-box} body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#f8f9fa;color:#111}
    .layout{display:flex;min-height:100vh}
    .sidenav{width:260px;background:#fff;border-right:1px solid #e5e7eb;position:sticky;top:0;height:100vh;padding:20px}
    .brand{display:flex;gap:10px;align-items:center;margin-bottom:24px}
    .brand .dot{width:12px;height:12px;border-radius:50%;background:var(--bg)}
    .nav a{display:flex;gap:10px;align-items:center;padding:10px 12px;margin-bottom:6px;border-radius:12px;color:#111;text-decoration:none}
    .nav a:hover, .nav a.active{background:#eef2ff}
    .content{flex:1;min-width:0}
    .topbar{position:sticky;top:0;background:#fff;border-bottom:1px solid #e5e7eb;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;z-index:10}
    .kpis{display:grid;grid-template-columns:repeat(4, minmax(0,1fr));gap:16px}
    .card{background:var(--card);border:1px solid #e5e7eb;border-radius:16px;padding:16px}
    .card h3{margin:0 0 4px 0;font-size:14px;color:#374151}
    .card .big{font-size:28px;font-weight:700}
    .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
    table{width:100%;border-collapse:collapse}
    th,td{padding:10px;border-bottom:1px solid #e5e7eb;text-align:left;font-size:14px}
    .muted{color:var(--muted)}
    .btn{display:inline-block;padding:10px 14px;border-radius:12px;border:1px solid #e5e7eb;background:#fff;text-decoration:none}
    .btn.primary{background:var(--bg);color:#fff;border-color:var(--bg)}
    .chips{display:flex;gap:8px;flex-wrap:wrap}
    .chip{background:var(--chip);padding:6px 10px;border-radius:999px;font-size:12px}
    @media (max-width: 1024px){ .kpis{grid-template-columns:repeat(2,1fr)} .grid{grid-template-columns:1fr} .sidenav{position:fixed;left:-280px;transition:left .2s} .sidenav.open{left:0} .menu-btn{display:inline-block} }
    @media (min-width: 1025px){ .menu-btn{display:none} }
  </style>
  {% block extra_css %}{% endblock %}
</head>
<body>
  <div class="layout">
    <aside id="sidenav" class="sidenav">
      <div class="brand"><span class="dot"></span><strong>TTDMS Agent</strong></div>
      <nav class="nav">
        <a href="{% url 'agent_dashboard' %}" class="{% if request.resolver_match.url_name == 'agent_dashboard' %}active{% endif %}">🏠 Dashboard</a>
        <a href="{% url 'agent_visit_new' %}">🗺️ Log Visit</a>
        <a href="{% url 'agent_sale_new' %}">🧾 Record Sale</a>
        <a href="{% url 'agent_transfer_new' %}">🔁 Request Transfer</a>
        <a href="{% url 'agent_return_new' %}">↩️ File Return</a>
        <hr>
        <a href="{% url 'logout' %}">🚪 Logout</a>
      </nav>
    </aside>

    <main class="content">
      <div class="topbar">
        <div>
          <button class="btn" id="menuBtn">☰</button>
          <strong>Welcome, {{ request.user.username }}</strong>
          <span class="muted">· {{ request.user.get_role_display|default:request.user.role|capfirst }}</span>
        </div>
        <div class="chips">
          <span class="chip">Today: {{ today|default:now|date:"M j, Y" }}</span>
          <span class="chip">Region: {{ request.user.region|default:"—" }}</span>
        </div>
      </div>

      {% if messages %}
      <div style="padding: 16px 20px;">
        {% for message in messages %}
          <div class="card" style="border-left:4px solid {% if message.tags == 'success' %#16a34a{% elif message.tags == 'danger' %#dc2626{% else %}#0ea5e9{% endif %};">
            {{ message }}
          </div>
        {% endfor %}
      </div>
      {% endif %}

      <div style="padding: 20px;">
        {% block content %}{% endblock %}
      </div>
    </main>
  </div>

  <script>
    const btn = document.getElementById('menuBtn');
    const sidenav = document.getElementById('sidenav');
    if (btn) btn.addEventListener('click', () => sidenav.classList.toggle('open'));
  </script>
  {% block extra_js %}{% endblock %}
</body>
</html>
```

---

### 5.2 Dashboard view

**`templates/agent/dashboard.html`**

```html
{% extends 'agent/base_agent.html' %}
{% block title %}Agent Dashboard — TTDMS{% endblock %}

{% block content %}
  <div class="kpis">
    <div class="card"><h3>Visits today</h3><div class="big">{{ visits_today }}</div></div>
    <div class="card"><h3>Units sold today</h3><div class="big">{{ units_today }}</div></div>
    <div class="card"><h3>Revenue today</h3><div class="big">KSh {{ revenue_today|floatformat:2 }}</div></div>
    <div class="card"><h3>Pending payments</h3><div class="big">KSh {{ pending_amount|floatformat:2 }}</div></div>
  </div>

  <div class="grid" style="margin-top:16px;">
    <div class="card">
      <h3>Recent visits</h3>
      <table>
        <thead><tr><th>Date/Time</th><th>Market</th><th>Outlet</th><th>Purpose</th></tr></thead>
        <tbody>
        {% for v in recent_visits %}
          <tr>
            <td>{{ v.datetime|date:"M j, Y H:i" }}</td>
            <td>{{ v.market.name }}</td>
            <td>{{ v.outlet.name|default:"—" }}</td>
            <td>{{ v.get_purpose_display|default:"—" }}</td>
          </tr>
        {% empty %}
          <tr><td colspan="4" class="muted">No visits yet</td></tr>
        {% endfor %}
        </tbody>
      </table>
      <div style="margin-top:10px"><a class="btn" href="{% url 'agent_visit_new' %}">+ Log a visit</a></div>
    </div>

    <div class="card">
      <h3>Recent sales</h3>
      <table>
        <thead><tr><th>When</th><th>Pack</th><th>Qty</th><th>Revenue</th></tr></thead>
        <tbody>
        {% for s in recent_sales %}
          <tr>
            <td>{{ s.timestamp|date:"M j, Y H:i" }}</td>
            <td>{{ s.pack.product.name }} — {{ s.pack.label }}</td>
            <td>{{ s.quantity }}</td>
            <td>KSh {{ s.revenue|floatformat:2 }}</td>
          </tr>
        {% empty %}
          <tr><td colspan="4" class="muted">No sales yet</td></tr>
        {% endfor %}
        </tbody>
      </table>
      <div style="margin-top:10px"><a class="btn" href="{% url 'agent_sale_new' %}">+ Record a sale</a></div>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h3>My stock snapshot</h3>
    <table>
      <thead><tr><th>Product</th><th>Pack</th><th>Qty (balance)</th></tr></thead>
      <tbody>
        {% for row in stock_rows %}
          <tr>
            <td>{{ row.product__name }}</td>
            <td>{{ row.pack__label }}</td>
            <td>{{ row.balance|default:"—" }}</td>
          </tr>
        {% empty %}
          <tr><td colspan="3" class="muted">No ledger entries yet</td></tr>
        {% endfor %}
      </tbody>
    </table>
    <div style="margin-top:10px" class="chips">
      <a class="btn" href="{% url 'agent_transfer_new' %}">Request stock transfer</a>
      <a class="btn" href="{% url 'agent_return_new' %}">File a return</a>
    </div>
  </div>
{% endblock %}
```

---

### 5.3 Quick‑action forms

**`templates/agent/visit_form.html`**

```html
{% extends 'agent/base_agent.html' %}
{% block title %}Log Visit — Agent{% endblock %}
{% block content %}
  <div class="card">
    <h3>Log a visit</h3>
    <form method="post">{% csrf_token %}
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px">
        {{ form.market.label_tag }}{{ form.market }}
        {{ form.outlet.label_tag }}{{ form.outlet }}
        {{ form.datetime.label_tag }}{{ form.datetime }}
        {{ form.purpose.label_tag }}{{ form.purpose }}
        <div style="grid-column:1/-1">{{ form.notes.label_tag }}{{ form.notes }}</div>
```
