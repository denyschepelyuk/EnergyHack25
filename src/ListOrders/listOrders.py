from GalacticBuf_serialization.serialization import GBObject, GBValue, serialize_message
from typing import List

def handle_get_orders(delivery_start: int, delivery_end: int, orders: List[dict]) -> bytes:
    """
    Handles the logic for GET /orders
    1. Filters orders by delivery window
    2. Sorts by price ascending
    3. Serializes to GalacticBuf
    """
    
    filtered_orders = [
        o for o in orders 
        if o['ds'] == delivery_start and o['de'] == delivery_end
    ]
    
    filtered_orders.sort(key=lambda x: x['price'])
    
    gb_order_list_items = []
    
    for o in filtered_orders:
        order_obj = GBObject()
        order_obj.fields.append(("order_id", GBValue.make_string(o['order_id'])))
        order_obj.fields.append(("price", GBValue.make_int(o['price'])))
        order_obj.fields.append(("quantity", GBValue.make_int(o['quantity'])))
        order_obj.fields.append(("delivery_start", GBValue.make_int(o['ds'])))
        order_obj.fields.append(("delivery_end", GBValue.make_int(o['de'])))
        
        gb_order_list_items.append(GBValue.make_object(order_obj))

    response_obj = GBObject()
    
    response_obj.fields.append((
        "orders", 
        GBValue.make_list(GBValue.TYPE_OBJECT, gb_order_list_items)
    ))
    
    return serialize_message(response_obj)