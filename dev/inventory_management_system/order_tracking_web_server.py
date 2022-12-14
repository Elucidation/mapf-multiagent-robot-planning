from flask import Flask, render_template
from Order import *
from datetime import datetime, timedelta
from database_order_manager import DatabaseOrderManager
import json
from Item import get_item_names

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

item_names = get_item_names()
@app.template_filter('get_item_name')
def _jinja2_filter_get_item_name(item_id: ItemId):
    return item_names[item_id]


@app.route("/")
def order_tracking():
    return render_template("order_tracking.html")


@app.route("/orders/open")
def open_orders_html():
    dboi = DatabaseOrderManager(db_name)
    orders = dboi.get_orders()
    orders = [o for o in orders if o.is_open() or o.is_in_progress()]
    return render_template("fragment_open_orders.html", orders=orders)


@app.route("/stations")
def stations_html():
    dboi = DatabaseOrderManager(db_name)
    stations_and_tasks = dboi.get_stations_and_tasks()

    return render_template(
        "fragment_stations.html",
        stations_and_tasks=stations_and_tasks
    )


@app.route("/orders/finished")
def finished_orders_html():
    dboi = DatabaseOrderManager(db_name)
    # todo: update get_orders to use status
    orders = dboi.get_orders()
    orders = [o for o in orders if o.is_finished()]
    return render_template("fragment_finished_orders.html", orders=orders)


@app.route("/order_station_tables")
def get_all_json():
    dboi = DatabaseOrderManager(db_name)
    orders = dboi.get_orders()
    stations_and_tasks = dboi.get_stations_and_tasks()

    progress_orders = [o for o in orders if o.is_open() or o.is_in_progress()]
    finished_orders = [o for o in orders if o.is_finished()]
    a = render_template("fragment_open_orders.html", orders=progress_orders)
    b = render_template("fragment_finished_orders.html",
                        orders=finished_orders)
    c = render_template(
        "fragment_stations.html",
        stations_and_tasks=stations_and_tasks,
    )
    return json.dumps({"open": a, "finished": b, "stations": c})
