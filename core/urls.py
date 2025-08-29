from django.urls import path
from . import views
from . import views_agent
from core import views_products, views_markets

urlpatterns = [
    # Public pages
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Role-based dashboards
    path("dashboard/", views.dashboard, name="dashboard"),   # redirects by role
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/manager/", views.manager_dashboard, name="manager_dashboard"),
    path("dashboard/agent/", views.agent_dashboard, name="agent_dashboard"),

    # Admin user management
    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.add_user, name="add_user"),

    # Product Management
    path("products/", views_products.product_list, name="product_list"),
    path("products/add/", views_products.product_add, name="product_add"),
    path("products/<uuid:pk>/edit/", views_products.product_edit, name="product_edit"),
    path("products/<uuid:pk>/delete/", views_products.product_delete, name="product_delete"),

    # Pack Sizes
    path("products/<uuid:product_id>/packsize/add/", views_products.packsize_add, name="packsize_add"),

    # Price Lists
    path("packs/<uuid:pack_id>/pricelist/add/", views_products.pricelist_add, name="pricelist_add"),


    # Markets
    path("markets/", views_markets.market_list, name="market_list"),
    path("markets/add/", views_markets.market_add, name="market_add"),
    path("markets/<uuid:pk>/edit/", views_markets.market_edit, name="market_edit"),
    path("markets/<uuid:pk>/delete/", views_markets.market_delete, name="market_delete"),

    # Outlets
    path("outlets/", views_markets.outlet_list, name="outlet_list"),
    path("outlets/add/", views_markets.outlet_add, name="outlet_add"),
    path("outlets/<uuid:pk>/edit/", views_markets.outlet_edit, name="outlet_edit"),
    path("outlets/<uuid:pk>/delete/", views_markets.outlet_delete, name="outlet_delete"),
]
