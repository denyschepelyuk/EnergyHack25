from typing import List, Dict

class OrderBook:
    def __init__(self):
        # Initialize as empty Dictionary (Acting as a Set for O(1) lookups)
        # Structure: { "order_id": { ...order_data... } }
        self.orders: Dict[str, Dict] = {}

    def add_order(self, order: Dict) -> bool:
        """
        Adds an order to the book.
        Returns False if order_id already exists (enforcing Set uniqueness).
        """
        oid = order.get("order_id")
        if oid in self.orders:
            return False
        
        self.orders[oid] = order
        return True

    def remove_order(self, order_id: str) -> bool:
        """
        Removes an order by ID (e.g., when a trade is executed).
        """
        if order_id in self.orders:
            del self.orders[order_id]
            return True
        return False

    def get_orders_by_contract(self, delivery_start: int, delivery_end: int) -> List[Dict]:
        """
        Returns orders matching the window, sorted by price (ascending).
        """
        # 1. Filter
        matches = [
            o for o in self.orders.values()
            if o['ds'] == delivery_start and o['de'] == delivery_end
        ]
        
        # 2. Sort (Cheapest first)
        matches.sort(key=lambda x: x['price'])
        
        return matches