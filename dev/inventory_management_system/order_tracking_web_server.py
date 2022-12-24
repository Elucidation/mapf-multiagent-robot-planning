from flask import Flask, render_template
from Order import *
from Station import Station
from datetime import datetime, timedelta
from collections import Counter
from database_order_manager import DatabaseOrderManager
import json

# flask.exe --app order_tracking_web_server --debug run

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

db_name = "orders.db"

@app.template_filter('strftime')
def _jinja2_filter_datetime(date: datetime):
    return date.strftime('%H:%M:%S')

@app.template_filter('strftimedelta')
def _jinja2_filter_timedelta(delta: timedelta):
    return f'{delta.total_seconds():0.1f}s'


@app.route("/")
def order_tracking():
    dboi = DatabaseOrderManager(db_name)
    orders = dboi.get_orders()
    orders_by_id = {o.order_id: o for o in orders}
    # stations = dboi.get_stations()

    stations_and_tasks = dboi.get_stations_and_tasks()
    return render_template(
        "order_tracking.html",
        stations_and_tasks=stations_and_tasks,
        orders_by_id=orders_by_id,
    )


@app.route("/orders/open")
def open_orders_html():
    dboi = DatabaseOrderManager(db_name)
    orders = dboi.get_orders()
    print(orders)
    orders = [o for o in orders if o.is_open() or o.is_in_progress()]
    return render_template("fragment_open_orders.html", orders=orders)


@app.route("/stations")
def stations_html():
    dboi = DatabaseOrderManager(db_name)
    orders = dboi.get_orders()
    orders_by_id = {o.order_id: o for o in orders}
    stations_and_tasks = dboi.get_stations_and_tasks()

    return render_template(
        "fragment_stations.html",
        stations_and_tasks=stations_and_tasks,
        orders_by_id=orders_by_id,
    )


@app.route("/orders/finished")
def finished_orders_html():
    dboi = DatabaseOrderManager(db_name)
    orders = dboi.get_orders()
    orders = [o for o in orders if o.is_finished()]
    return render_template("fragment_finished_orders.html", orders=orders)


@app.route("/order_station_tables")
def get_all_json():
    dboi = DatabaseOrderManager(db_name)
    orders = dboi.get_orders()
    orders_by_id = {o.order_id: o for o in orders}
    stations_and_tasks = dboi.get_stations_and_tasks()
    
    progress_orders = [o for o in orders if o.is_open() or o.is_in_progress()]
    finished_orders = [o for o in orders if o.is_finished()]
    a = render_template("fragment_open_orders.html", orders=progress_orders)
    b = render_template("fragment_finished_orders.html",
                        orders=finished_orders)
    c = render_template(
        "fragment_stations.html",
        stations_and_tasks=stations_and_tasks,
        orders_by_id=orders_by_id,
    )
    return json.dumps({"open": a, "finished": b, "stations": c})
