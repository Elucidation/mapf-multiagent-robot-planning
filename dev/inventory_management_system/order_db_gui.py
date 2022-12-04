import sqlite3 as sl
import time
import os


class OrderGUI:
    """Create GUI on the Order database"""

    # order_query = 'SELECT * FROM "Order" LIMIT 0, ?;'
    order_query = """SELECT "Order".*, sum(quantity) as item_count FROM "Order" 
                     INNER JOIN "OrderItem" ON "OrderItem".order_id = "Order".order_id
                     GROUP BY "Order".order_id LIMIT 0, ?;"""

    def __init__(self, db_filename):
        self.con = sl.connect(db_filename)

    def get_all_orders(self, N=49999):
        c = self.con.cursor()
        # c.execute('SELECT * FROM "Order" LIMIT 0, ?', (N,))
        c.execute(self.order_query, (N,))

        rows = c.fetchall()
        return rows

    def run(self, update_rate_sec=1):
        while True:
            os.system("cls")
            print("Orders")
            for row in order_gui.get_all_orders(N=100):
                print(row)
            time.sleep(update_rate_sec)


if __name__ == "__main__":
    order_gui = OrderGUI("orders.db")
    # print(order_gui.get_all_orders())

    order_gui.run()
