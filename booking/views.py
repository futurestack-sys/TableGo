from datetime import date as dt
from functools import wraps
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import RestaurantForm, TableForm
from .models import LIVE, SLOTS, Reservation, Restaurant, Table

OCCASIONS = ["", "Birthday", "Anniversary", "Business meeting", "Date night", "Family gathering"]


# ---------- Customer ----------
def home(request):
    return render(request, "home.html", {"restaurants": Restaurant.objects.filter(active=True)})


def restaurants(request):
    return render(request, "restaurants.html", {"restaurants": Restaurant.objects.filter(active=True)})


def register(request):
    form = UserCreationForm(request.POST or None)
    form.fields["username"].help_text = ""
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


def reserve(request, slug):
    """3 steps kept in the query string: 1 details -> 2 pick table -> 3 confirm (POST)."""
    rest = get_object_or_404(Restaurant, slug=slug, active=True)
    src = request.POST if request.method == "POST" else request.GET
    today = timezone.localdate()
    try:
        d = dt.fromisoformat(src.get("date", ""))
    except ValueError:
        d = None
    t = src.get("time") if src.get("time") in SLOTS else SLOTS[0]
    try:
        g = max(1, min(20, int(src.get("guests", 2))))
    except ValueError:
        g = 2
    occ, phone = src.get("occasion", "")[:30], src.get("phone", "")[:30]
    session_key = f"reservation_name_{slug}"
    default_name = request.user.get_full_name() if request.user.is_authenticated else ""
    name_value = src.get("customer_name", request.session.get(session_key, default_name))
    customer_name = (name_value or "").strip()[:100]
    step, cells, pick = 1, [], None
    if d and d >= today:
        step = 2
        busy = set(rest.reservation_set.filter(date=d, time=t, status__in=LIVE).values_list("table_id", flat=True))
        cells = [{"t": x, "state": "taken" if x.pk in busy else "small" if x.seats < g else "free"} for x in rest.table_set.all()]
        pick = next((c["t"] for c in cells if str(c["t"].pk) == src.get("table") and c["state"] == "free"), None)
        if pick:
            step = 3
    elif d:
        messages.error(request, "Pick today or a later date.")
    if request.method == "POST" and src.get("confirm") != "1":
        if customer_name:
            request.session[session_key] = customer_name
        else:
            messages.error(request, "Enter your name to continue.")
            step, cells, pick = 1, [], None
    if request.method == "POST" and src.get("confirm") == "1" and step == 3 and request.user.is_authenticated:
        if not customer_name:
            messages.error(request, "Enter your name to confirm the reservation.")
            step = 1
        else:
            res = Reservation.objects.create(customer=request.user, customer_name=customer_name, restaurant=rest,
                                             table=pick, date=d, time=t, guests=g, phone=phone, occasion=occ)
            request.session.pop(session_key, None)
            messages.success(request, f"Reservation RSV-{res.pk + 1000} requested at {rest.name} (table {pick.name}). Awaiting confirmation.")
            return redirect("my")
    sel = {"date": d if d and d >= today else today, "time": t, "guests": g, "occasion": occ,
           "phone": phone, "customer_name": customer_name}
    return render(request, "reserve.html", {"rest": rest, "step": step, "cells": cells, "pick": pick, "sel": sel,
                                            "slots": SLOTS, "occasions": OCCASIONS, "today": today})


@login_required
def my_reservations(request):
    today, tab = timezone.localdate(), request.GET.get("tab", "upcoming")
    qs = list(Reservation.objects.filter(customer=request.user).select_related("restaurant", "table"))
    groups = {"upcoming": [r for r in qs if r.status in LIVE and r.date >= today],
              "completed": [r for r in qs if r.status in LIVE and r.date < today],
              "cancelled": [r for r in qs if r.status in ("cancelled", "declined")]}
    return render(request, "my.html", {"tab": tab, "items": groups.get(tab, []), "counts": {k: len(v) for k, v in groups.items()}})


@login_required
@require_POST
def cancel(request, pk):
    r = get_object_or_404(Reservation, pk=pk, customer=request.user)
    if r.status in LIVE:
        r.status = "cancelled"
        r.save()
    return redirect("my")


# ---------- Dashboard (admin = all restaurants, manager = own restaurant) ----------
def dash_only(fn):
    @wraps(fn)
    @login_required
    def wrapper(request, *a, **k):
        if request.user.is_staff:
            rests, is_admin = Restaurant.objects.all(), True
        elif getattr(request.user, "manager", None):
            rests, is_admin = Restaurant.objects.filter(pk=request.user.manager.restaurant_id), False
        else:
            raise PermissionDenied
        return fn(request, rests, is_admin, *a, **k)
    return wrapper


def dash(request, tpl, is_admin, nav, **ctx):
    return render(request, tpl, {"is_admin": is_admin, "nav": nav, **ctx})


@dash_only
def dashboard(request, rests, is_admin):
    res = Reservation.objects.filter(restaurant__in=rests)
    cur = rests.filter(slug=request.GET.get("r")).first() or rests.first()
    cells = []
    if cur:
        booked = set(res.filter(restaurant=cur, date=timezone.localdate(), status__in=LIVE).values_list("table_id", flat=True))
        cells = [{"t": t, "state": "taken" if t.pk in booked else "free"} for t in cur.table_set.all()]
    custs = User.objects.filter(is_staff=False).count() if is_admin else res.values("customer").distinct().count()
    stats = [("Total Reservations", res.count()), ("Tables", Table.objects.filter(restaurant__in=rests).count()),
             ("Pending Approval", res.filter(status="pending").count()), ("Total Customers", custs)]
    latest = res.select_related("customer", "restaurant", "table").order_by("-created")
    return dash(request, "dash.html", is_admin, "dashboard", rests=rests.annotate(nt=Count("table")), cur=cur, cells=cells,
                stats=stats, recent=latest[:5], activity=latest[:5])


@dash_only
def d_reservations(request, rests, is_admin):
    status, slug = request.GET.get("status", ""), request.GET.get("r", "")
    items = Reservation.objects.filter(restaurant__in=rests).select_related("customer", "restaurant", "table").order_by("-date", "-time")
    if status:
        items = items.filter(status=status)
    if slug:
        items = items.filter(restaurant__slug=slug)
    return dash(request, "d_reservations.html", is_admin, "reservations", rests=rests, items=items, status=status, slug=slug)


@dash_only
@require_POST
def d_status(request, rests, is_admin, pk, status):
    if status in ("confirmed", "declined"):
        Reservation.objects.filter(pk=pk, restaurant__in=rests).update(status=status)
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/dashboard") else "dashboard")


@dash_only
def d_restaurants(request, rests, is_admin):
    if not is_admin:
        raise PermissionDenied
    form = RestaurantForm()
    if request.method == "POST":
        if request.POST.get("action") == "toggle":
            r = get_object_or_404(Restaurant, pk=request.POST.get("pk"))
            r.active = not r.active
            r.save()
            return redirect("d_restaurants")
        form = RestaurantForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("d_restaurants")
    today = timezone.localdate()
    rows = rests.annotate(nt=Count("table", distinct=True))
    for r in rows:
        r.today = r.reservation_set.filter(date=today, status__in=LIVE).count()
        r.pend = r.reservation_set.filter(status="pending").count()
    return dash(request, "d_restaurants.html", is_admin, "restaurants", rows=rows, form=form)


@dash_only
def d_tables(request, rests, is_admin):
    cur = rests.filter(slug=request.GET.get("r") or request.POST.get("r")).first() or rests.first()
    form = TableForm()
    if request.method == "POST" and cur:
        a, pk = request.POST.get("action"), request.POST.get("pk")
        back = redirect(f"{reverse('d_tables')}?r={cur.slug}")
        if a == "add_table":
            form = TableForm(request.POST)
            if form.is_valid():
                form.instance.restaurant = cur
                form.save()
                return back
        elif a == "del_table":
            Table.objects.filter(pk=pk, restaurant=cur).delete()
            return back
        elif a == "edit_table":
            try:
                n = lambda v, lo, hi: max(lo, min(hi, int(v)))
                Table.objects.filter(pk=pk, restaurant=cur).update(x=n(request.POST["x"], 0, 100), y=n(request.POST["y"], 0, 100), seats=n(request.POST["seats"], 1, 30))
            except (ValueError, KeyError):
                messages.error(request, "Enter whole numbers.")
            return back
    tables = cur.table_set.all() if cur else []
    return dash(request, "d_tables.html", is_admin, "tables", rests=rests, cur=cur, form=form, tables=tables,
                cells=[{"t": t, "state": "free"} for t in tables])


@dash_only
def d_customers(request, rests, is_admin):
    if not is_admin:
        raise PermissionDenied
    users = User.objects.filter(is_staff=False).annotate(n=Count("reservation")).order_by("-date_joined")
    return dash(request, "d_customers.html", is_admin, "customers", users=users)
