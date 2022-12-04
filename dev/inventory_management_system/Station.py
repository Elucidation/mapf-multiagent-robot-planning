class Station():
    """Stations process partial orders"""
    def __init__(self, station_id, order_id=None):
        self.station_id = station_id
        self.order_id = order_id

    def assign_order_id(self, order_id):
        self.order_id = order_id

    def clear_station(self):
        self.order_id = None

    def is_available(self):
        return self.order_id is None
    
    def __repr__(self):
        if self.is_available():
            return f'Station {self.station_id}: AVAILABLE'
        return f'Station {self.station_id}: Order {self.order_id}'