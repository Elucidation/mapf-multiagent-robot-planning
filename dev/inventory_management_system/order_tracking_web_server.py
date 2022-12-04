from flask import Flask, render_template
from Order import *
from Station import Station
from datetime import datetime
from collections import Counter
from database_order_manager import DatabaseOrderManager


# def get_orders():
#     order1 = Order(
#         created_by=1,
#         created=datetime.now(),
#         items=Counter([1, 2, 2, 4]),
#         description="order with 3 items",
#         order_id=1,
#         status="IN_PROGRESS"
#     )
#     order2 = Order(
#         created_by=3,
#         created=datetime.now(),
#         finished=datetime.now() + datetime.timedelta(minutes=1, seconds=3),
#         items=Counter([1, 1, 3, 4]),
#         description="order with several items",
#         order_id=2,
#         status="COMPLETE"
#     )
#     order3 = Order(
#         created_by=3,
#         created=datetime.now(),
#         items=Counter([3, 2, 4, 4, 4, 6, 6]),
#         description="order with 4 items",
#         order_id=3,
#     )
    
#     return [order1, order2, order3]


# def get_stations():
#     station1 = Station(1)
#     station2 = Station(2)
#     return [station1, station2]

# orders = get_orders()
# stations = get_stations()

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


dboi = DatabaseOrderManager("test2.db")

orders = dboi.get_orders()
orders_by_id = {o.order_id: o for o in orders}
stations = dboi.get_stations()

partial_orders = dboi.get_partial_orders()
partial_orders_by_id = {p.order_id: p for p in partial_orders}


@app.route("/")
def order_tracking():
    return render_template("order_tracking.html", stations=stations, orders_by_id=orders_by_id, partial_orders_by_id=partial_orders_by_id)
