from fastapi import FastAPI, Request, Response
from src.GalacticBuf_serialization.serialization import (
    GBObject, GBValue, serialize_message
)
from storage import OrderBook

app = FastAPI()
order_book = OrderBook()

@app.get("/orders")
async def get_orders(request: Request):
    # 1. Parse Query Params
    query_params = request.query_params
    ds_str = query_params.get("delivery_start")
    de_str = query_params.get("delivery_end")

    if not ds_str or not de_str:
        return Response(status_code=400)

    try:
        delivery_start = int(ds_str)
        delivery_end = int(de_str)
    except ValueError:
        return Response(status_code=400)

    # 2. Fetch Data (will be empty initially)
    orders = order_book.get_orders_by_contract(delivery_start, delivery_end)

    # 3. Serialize to GalacticBuf
    gb_order_items = []
    for o in orders:
        order_obj = GBObject([
            ("order_id", GBValue.make_string(o['order_id'])),
            ("price", GBValue.make_int(o['price'])),
            ("quantity", GBValue.make_int(o['quantity'])),
            ("delivery_start", GBValue.make_int(o['ds'])),
            ("delivery_end", GBValue.make_int(o['de']))
        ])
        gb_order_items.append(GBValue.make_object(order_obj))

    # Wrap in the top-level "orders" list
    response_obj = GBObject([
        ("orders", GBValue.make_list(GBValue.TYPE_OBJECT, gb_order_items))
    ])

    return Response(
        content=serialize_message(response_obj),
        media_type="application/x-galacticbuf",
        status_code=200
    )