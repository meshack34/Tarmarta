from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.models import Product, PackSize, PriceList, Role
from core.forms import ProductForm, PackSizeForm, PriceListForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.models import Market, Outlet, Role
from core.forms import MarketForm, OutletForm

# --- Helper decorator ---
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != Role.ADMIN:
            messages.error(request, "Unauthorized: Admins only")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return wrapper  



# --- Product Views ---
@login_required
@admin_required
def product_list(request):
    products = Product.objects.all().order_by("name")
    return render(request, "products/product_list.html", {"products": products})


@login_required
@admin_required
def product_add(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully.")
            return redirect("product_list")
    else:
        form = ProductForm()
    return render(request, "products/product_form.html", {"form": form, "title": "Add Product"})


@login_required
@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect("product_list")
    else:
        form = ProductForm(instance=product)
    return render(request, "products/product_form.html", {"form": form, "title": "Edit Product"})


@login_required
@admin_required
def packsize_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        form = PackSizeForm(request.POST)
        if form.is_valid():
            pack = form.save(commit=False)
            pack.product = product
            pack.save()
            messages.success(request, "Pack size added successfully.")
            return redirect("product_list")
    else:
        form = PackSizeForm()
    return render(request, "products/packsize_form.html", {"form": form, "product": product})


@login_required
@admin_required
def pricelist_add(request, pack_id):
    pack = get_object_or_404(PackSize, pk=pack_id)
    if request.method == "POST":
        form = PriceListForm(request.POST)
        if form.is_valid():
            price = form.save(commit=False)
            price.pack = pack
            price.save()
            messages.success(request, "Price list added successfully.")
            return redirect("product_list")
    else:
        form = PriceListForm()
    return render(request, "products/pricelist_form.html", {"form": form, "pack": pack})




@login_required
@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect("product_list")


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
