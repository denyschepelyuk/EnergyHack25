from typing import List, Dict

class OrderBook:
    def __init__(self):
        self.orders: Dict[str, Dict] = {
            "ord_101": {"order_id": "ord_101", "price": 50, "quantity": 100, "ds": 1600000000, "de": 1600003600},
            "ord_102": {"order_id": "ord_102", "price": 45, "quantity": 200, "ds": 1600000000, "de": 1600003600},
            "ord_103": {"order_id": "ord_103", "price": 60, "quantity": 50,  "ds": 1600000000, "de": 1600003600},
            "ord_104": {"order_id": "ord_104", "price": 55, "quantity": 150, "ds": 1700000000, "de": 1700003600},
        }

    def add_order(self, order: Dict) -> bool:
        oid = order.get("order_id")
        if oid in self.orders:
            return False
        
        self.orders[oid] = order
        return True

    def remove_order(self, order_id: str) -> bool:

        if order_id in self.orders:
            del self.orders[order_id]
            return True
        return False

    def get_orders_by_contract(self, delivery_start: int, delivery_end: int) -> List[Dict]:

        matches = [
            o for o in self.orders.values()
            if o['ds'] == delivery_start and o['de'] == delivery_end
        ]
        
        matches.sort(key=lambda x: x['price'])
        
        return matches