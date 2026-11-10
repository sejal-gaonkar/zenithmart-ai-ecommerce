"""shop_db.py - SQLite catalogue, orders and support requests for ZenithMart (DEMO DATA)."""
import os, sqlite3, random, string, datetime

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zenithmart.db")

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

A, F, J = "S,M,L,XL", "6,7,8,9,10", "28,30,32,34"
# name, category, subcategory, price(INR), rating, sizes, stock, returnable, description, specs
CAT = [
("Essential Cotton Crew Tee","Apparel","T-shirts",599,4.4,A,40,1,"Soft combed-cotton tee with a relaxed everyday fit.","100% cotton|180 GSM|Machine wash"),
("Urban Graphic Tee","Apparel","T-shirts",699,4.2,A,35,1,"Bold printed tee in breathable jersey.","Cotton blend|Regular fit|Cold wash"),
("Slim Fit Stretch Jeans","Apparel","Jeans",1799,4.5,J,28,1,"Mid-rise slim jeans with comfortable stretch denim.","98% cotton 2% elastane|Slim fit|Mid rise"),
("Windcheater Sports Jacket","Apparel","Sports jackets",2299,4.3,A,18,1,"Lightweight water-resistant jacket for training days.","Polyester|Water resistant|Zip pockets"),
("Oxford Casual Shirt","Apparel","Casual shirts",1299,4.1,A,30,1,"Classic button-down Oxford shirt, crisp yet soft.","Cotton Oxford|Regular fit|Button-down"),
("CloudRun Running Shoes","Footwear","Running shoes",3499,4.6,F,22,1,"Cushioned daily trainers with a breathable mesh upper.","Mesh upper|EVA midsole|280 g"),
("Court Classic Sneakers","Footwear","Sneakers",2499,4.4,F,25,1,"Clean low-top sneakers that go with everything.","Synthetic leather|Rubber sole|Lace-up"),
("Street Canvas Sneakers","Footwear","Sneakers",1499,4.0,F,40,1,"Easy canvas sneakers with a vulcanised sole.","Canvas|Rubber sole|Lace-up"),
("Comfort Slip-On Loafers","Footwear","Casual footwear",1799,4.2,F,20,1,"Cushioned slip-ons for relaxed weekdays.","Faux suede|Memory foam insole"),
("Trail Comfort Sandals","Footwear","Casual footwear",999,3.9,F,33,1,"Adjustable straps and a grippy sole.","EVA|Velcro straps|Lightweight"),
("Pulse Smartwatch","Electronics","Smartwatches",3999,4.5,"",15,1,"1.8in AMOLED display, heart-rate and sleep tracking.","AMOLED 1.8in|7-day battery|IP68"),
("FitBand Pro","Electronics","Smartwatches",2499,4.1,"",26,1,"Slim activity tracker with 14 sport modes.","LCD|10-day battery|Bluetooth 5.2"),
("AirTone Wireless Headphones","Electronics","Headphones",2999,4.6,"",19,1,"Over-ear headphones with deep bass and 30h playtime.","Bluetooth 5.3|30h battery|Foldable"),
("BassBox Bluetooth Speaker","Electronics","Bluetooth speakers",1999,4.3,"",24,1,"Portable speaker with punchy sound, splash-proof.","10W|12h battery|IPX5"),
("20W Fast Charger","Electronics","Mobile accessories",799,4.2,"",60,0,"Compact USB-C fast charger.","20W PD|USB-C|Overheat protection"),
("Braided USB-C Cable","Electronics","Mobile accessories",399,4.0,"",80,0,"1.5 m durable braided charging cable.","1.5 m|60W|Nylon braid"),
("Vitamin C Face Serum","Grooming","Skincare",699,4.3,"",45,0,"Brightening serum for daily use. Patch test first.","30 ml|Vitamin C 10%|All skin types"),
("Hydrating Daily Moisturiser","Grooming","Skincare",499,4.2,"",50,0,"Lightweight non-greasy moisturiser.","50 ml|Hyaluronic acid|Fragrance free"),
("Beard Grooming Kit","Grooming","Grooming kits",1299,4.4,"",21,1,"Trimmer, comb and beard oil in one gift-ready kit.","Rechargeable trimmer|Beard oil 30 ml"),
("Daily Care Combo","Grooming","Personal care",899,4.1,"",38,0,"Face wash, body wash and deodorant set.","3-piece set|Dermatologically tested"),
("Classic Analog Wristwatch","Accessories","Wristwatches",2799,4.5,"",17,1,"Minimal steel-case watch with a leather strap.","40 mm|Quartz|3 ATM"),
("Everyday Commuter Backpack","Accessories","Bags",1999,4.4,"",23,1,"Padded 20 L backpack with a laptop sleeve.","20 L|15.6in laptop sleeve|Water resistant"),
("Leather Bifold Wallet","Accessories","Wallets",899,4.2,"",42,1,"Slim bifold wallet with 6 card slots.","Genuine leather|6 card slots"),
("Crossbody Sling Bag","Accessories","Bags",1299,4.1,"",27,1,"Compact sling bag for phone and essentials.","Polyester|Adjustable strap|Zip closure"),
]

def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,name TEXT,category TEXT,subcategory TEXT,price INT,mrp INT,rating REAL,sizes TEXT,stock INT,returnable INT,description TEXT,specs TEXT);
        CREATE TABLE IF NOT EXISTS orders(order_id TEXT PRIMARY KEY,cust TEXT,name TEXT,phone TEXT,address TEXT,city TEXT,pincode TEXT,shipping TEXT,subtotal INT,ship_fee INT,total INT,status TEXT,tracking TEXT,payment TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id TEXT,product_id TEXT,name TEXT,qty INT,size TEXT,price INT,returnable INT);
        CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id TEXT,type TEXT,reason TEXT,status TEXT,created_at TEXT);
        """)
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            for i, p in enumerate(CAT, 1):
                mrp = int(p[3] * 1.25 // 10 * 10) if i % 3 == 0 else p[3]
                c.execute("INSERT INTO products VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                          (f"ZM{i:03d}", p[0], p[1], p[2], p[3], mrp, p[4], p[5], p[6], p[7], p[8], p[9]))

def _prod(r):
    d = dict(r); d["sizes"] = [s for s in d["sizes"].split(",") if s]
    d["specs"] = d["specs"].split("|"); d["returnable"] = bool(d["returnable"]); return d

def products(q="", category="", lo=0, hi=10**9, sort=""):
    sql, a = "SELECT * FROM products WHERE price BETWEEN ? AND ?", [lo, hi]
    if q: sql += " AND (name LIKE ? OR subcategory LIKE ?)"; a += [f"%{q}%"] * 2
    if category: sql += " AND category=?"; a.append(category)
    sql += {"price_asc": " ORDER BY price", "price_desc": " ORDER BY price DESC", "rating": " ORDER BY rating DESC"}.get(sort, " ORDER BY id")
    with conn() as c: return [_prod(r) for r in c.execute(sql, a)]

def product(pid):
    with conn() as c:
        r = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    return _prod(r) if r else None

def place_order(cust, d):
    with conn() as c:
        sub, lines = 0, []
        for it in d["items"]:
            p = c.execute("SELECT * FROM products WHERE id=?", (it["product_id"],)).fetchone()
            if not p: raise ValueError("Unknown product in cart")
            if p["sizes"] and it.get("size") not in p["sizes"].split(","): raise ValueError(f"Please choose a size for {p['name']}")
            if it["qty"] > p["stock"]: raise ValueError(f"Only {p['stock']} of {p['name']} left in stock")
            sub += p["price"] * it["qty"]; lines.append((p, it["qty"], it.get("size", "")))
        fee = 99 if d["shipping"] == "fast" else (0 if sub >= 499 else 49)
        oid = "ZM" + datetime.date.today().strftime("%y%m%d") + "".join(random.choices(string.digits, k=5))
        trk = "ZMTRK" + "".join(random.choices(string.digits, k=10))
        c.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (oid, cust, d["name"], d["phone"], d["address"], d["city"], d["pincode"], d["shipping"], sub, fee, sub + fee,
                   "Pending", trk, "Simulated payment (demo)", datetime.datetime.now().isoformat(timespec="seconds")))
        for p, q, s in lines:
            c.execute("INSERT INTO order_items(order_id,product_id,name,qty,size,price,returnable) VALUES(?,?,?,?,?,?,?)",
                      (oid, p["id"], p["name"], q, s, p["price"], p["returnable"]))
            c.execute("UPDATE products SET stock=stock-? WHERE id=?", (q, p["id"]))
    return oid

def _order(c, r):
    o = dict(r)
    o["items"] = [dict(x) for x in c.execute("SELECT * FROM order_items WHERE order_id=?", (o["order_id"],))]
    o["requests"] = [dict(x) for x in c.execute("SELECT * FROM requests WHERE order_id=? ORDER BY id", (o["order_id"],))]
    return o

def orders(cust):
    with conn() as c:
        return [_order(c, r) for r in c.execute("SELECT * FROM orders WHERE cust=? ORDER BY created_at DESC", (cust,))]

def order(oid, cust):
    with conn() as c:
        r = c.execute("SELECT * FROM orders WHERE order_id=? AND cust=?", (oid, cust)).fetchone()
        return _order(c, r) if r else None

def advance(oid, cust):
    nxt = {"Pending": "Shipped", "Shipped": "Delivered"}
    with conn() as c:
        r = c.execute("SELECT status FROM orders WHERE order_id=? AND cust=?", (oid, cust)).fetchone()
        if not r or r["status"] not in nxt: raise ValueError("Order cannot move forward")
        c.execute("UPDATE orders SET status=? WHERE order_id=?", (nxt[r["status"]], oid))

def add_request(oid, cust, kind, reason):
    with conn() as c:
        o = c.execute("SELECT * FROM orders WHERE order_id=? AND cust=?", (oid, cust)).fetchone()
        if not o: raise ValueError("Order not found")
        if c.execute("SELECT 1 FROM requests WHERE order_id=? AND type=?", (oid, kind)).fetchone():
            raise ValueError("A request of this type already exists for this order")
        if kind == "cancel":
            if o["status"] != "Pending": raise ValueError("Only Pending orders can be cancelled")
            for i in c.execute("SELECT product_id,qty FROM order_items WHERE order_id=?", (oid,)):
                c.execute("UPDATE products SET stock=stock+? WHERE id=?", (i["qty"], i["product_id"]))
            c.execute("UPDATE orders SET status='Cancelled' WHERE order_id=?", (oid,))
        else:
            if o["status"] != "Delivered": raise ValueError("Returns and exchanges open after delivery")
            if c.execute("SELECT 1 FROM order_items WHERE order_id=? AND returnable=0", (oid,)).fetchone():
                raise ValueError("This order has items that are not eligible for return or exchange")
        c.execute("INSERT INTO requests(order_id,type,reason,status,created_at) VALUES(?,?,?,?,?)",
                  (oid, kind, reason, "Approved" if kind == "cancel" else "Submitted", datetime.datetime.now().isoformat(timespec="seconds")))