from app.repositories.rooms_repo import RoomsRepo

r = RoomsRepo()
for city, max_price in [("Paris", None), ("Paris", 120), ("Paris", 200)]:
    rows = r.search(city=city, max_price=max_price, occupancy=2, topk=5)
    print(city, max_price, "→", len(rows), "rows")
    for x in rows:
        print("  ", x["hotel"], x["room_type"], x["price"])
