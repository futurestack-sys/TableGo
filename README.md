# Golden Sun Restaurant Group: Table Reservation (Django)

Restaurants: Khloe, Golden Sun Restaurant, Lub Dub Cafe. Customers pick a table on a floor plan.

## Run
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py seed
    python manage.py runserver
Open http://127.0.0.1:8000/  (admin dashboard: /dashboard/ , Django admin: /admin/)

## Logins (created by `seed`)
| Role | Username | Password |
|---|---|---|
| Admin (all restaurants) | admin | admin12345 |
| Manager, Khloe | manager_chloe | manager123 |
| Manager, Golden Sun Restaurant | manager_goldensun | manager123 |
| Manager, Lub Dub Cafe | manager_lubdubcafe | manager123 |
| Customer | customer | customer123 |
Change these before any real use.

## Where things are
- Look and feel: booking/static/booking/site.css (colours at the top). Brand name: booking/templates/base.html and dash_base.html.
- Restaurant photos: booking/static/booking/img/<slug>.jpg
- Table maps: booking/layouts.py (Lub Dub Cafe from video, Golden Sun Restaurant from floor plan, Khloe from photos)
