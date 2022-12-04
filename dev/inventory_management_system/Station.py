class Station():
    """Stations process partial orders"""
    def __init__(self, station_id):
        self.station_id = station_id
        self.partial_order = None

    def assign_partial_order(self, partial_order):
        self.partial_order = partial_order

    def clear_station(self):
        self.partial_order = None

    def is_available(self):
        return self.partial_order is None
        