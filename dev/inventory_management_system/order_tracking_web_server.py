from flask import Flask, render_template
from Order import *
from Station import Station
import datetime
from collections import Counter


def get_orders():
    order1 = Order(
        created_by=1,
        created=datetime.datetime.now(),
        items=Counter([1, 2, 2, 4]),
        description="order with 3 items",
        order_id=1,
        status="IN_PROGRESS"
    )
    order2 = Order(
        created_by=3,
        created=datetime.datetime.now(),
        finished=datetime.datetime.now() + datetime.timedelta(minutes=1, seconds=3),
        items=Counter([1, 1, 3, 4]),
        description="order with several items",
        order_id=2,
        status="COMPLETE"
    )
    order3 = Order(
        created_by=3,
        created=datetime.datetime.now(),
        items=Counter([3, 2, 4, 4, 4, 6, 6]),
        description="order with 4 items",
        order_id=3,
    )
    
    return [order1, order2, order3]


def get_stations():
    station1 = Station(1)
    station2 = Station(2)
    return [station1, station2]


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


orders = get_orders()
stations = get_stations()
po1 = PartialOrder.from_order(orders[0])
stations[0].assign_partial_order(po1)
po1.add_item(2)
po1.add_item(4)


@app.route("/")
def order_tracking():
    return render_template("order_tracking.html", orders=orders, stations=stations)
