"""Flask Web server for seeing orders/stations being processed"""
import json
from datetime import datetime, timedelta
import time
from typing import Optional
from flask import Flask, render_template
from .database_order_manager import DatabaseOrderManager, MAIN_DB
from .Item import ItemId, get_item_names

#  dev> flask.exe --app inventory_management_system.order_tracking_web_server --debug run
# Add --host=0.0.0.0 for external
FLASK_UPDATE_RATE_SEC = 1.0


class DataLoader:
    """Helper class to memoize calls to DB for order/station data"""

    def __init__(self) -> None:
        self.latest_data = None
        self.last_time = None
        self.update_rate_s = FLASK_UPDATE_RATE_SEC

    def get_data(self, subset):
        """Get latest data, update from DB if time since last update > update rate"""
        now = time.perf_counter()
        if (self.last_time is None
            or self.latest_data is None
                or (now - self.last_time) > self.update_rate_s):
            self.latest_data = self.get_data_from_db(subset)
            self.last_time = now
        return self.latest_data

    def get_data_from_db(self, subset: Optional[int] = None):
        dboi = DatabaseOrderManager(MAIN_DB)
        # TODO : Get all necessary orders in one SQL query
        if subset:
            open_orders = dboi.get_orders(
                limit_rows=subset, status="OPEN")
            finished_orders = dboi.get_orders(
                limit_rows=subset, status="COMPLETE", order_by='finished')
        else:
            open_orders = dboi.get_orders(status="OPEN")
            finished_orders = dboi.get_orders(status="COMPLETE", order_by='finished')
        stations_and_tasks = dboi.get_stations_and_tasks()
        return (open_orders, finished_orders, stations_and_tasks)


data_loader = DataLoader()


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


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
    dboi = DatabaseOrderManager(MAIN_DB)
    orders = dboi.get_orders()
    orders = [o for o in orders if o.is_open() or o.is_in_progress()]
    return render_template("fragment_open_orders.html", orders=orders)


@app.route("/stations")
def stations_html():
    dboi = DatabaseOrderManager(MAIN_DB)
    stations_and_tasks = dboi.get_stations_and_tasks()

    return render_template(
        "fragment_stations.html",
        stations_and_tasks=stations_and_tasks
    )


@app.route("/orders/finished")
def finished_orders_html():
    dboi = DatabaseOrderManager(MAIN_DB)
    # TODO: update get_orders to use status COMPLETE|ERROR
    orders = dboi.get_orders()
    orders = [o for o in orders if o.is_finished()]
    return render_template("fragment_finished_orders.html", orders=orders)


@app.route("/order_station_tables/full")
def get_full_json():
    return get_all_json()


@app.route("/order_station_tables")
def get_quick_json():
    return get_all_json(10)


def get_all_json(subset: Optional[int] = None):
    open_orders, finished_orders, stations_and_tasks = data_loader.get_data(
        subset)

    open_tmp = render_template(
        "fragment_open_orders.html", orders=open_orders)
    finished_tmp = render_template(
        "fragment_finished_orders.html", orders=finished_orders)
    stations_tmp = render_template(
        "fragment_stations.html",
        stations_and_tasks=stations_and_tasks,
    )
    return json.dumps({"open": open_tmp, "finished": finished_tmp, "stations": stations_tmp})


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=False)
