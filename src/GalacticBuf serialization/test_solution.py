from solution import GBObject, GBValue, serialize_message, parse_cli_args_to_object

# Simulate CLI args: user_id=1001, name=Alice, scores=[100,200,300]
# args = ["user_id=1001", "name=Alice", "scores=[100,200,300]"]
args = [
        "timestamp=1698765432",
        "trades=[{id:1, price:100}, {id:2, price:200}]"
]

obj = parse_cli_args_to_object(args)
data = serialize_message(obj)

print("Length:", len(data))
print("Hex:   ", " ".join(f"{b:02X}" for b in data))
