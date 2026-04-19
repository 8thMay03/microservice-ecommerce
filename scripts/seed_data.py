#!/usr/bin/env python3
"""
Seed sample data for Ecommerce microservices.
Requires: Docker Compose services running (docker compose up -d)
Run from project root: python scripts/seed_data.py
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PASSWORD = "Password123!"

# Category slug -> ID mapping (after seed, IDs are 1-based in creation order)
# Updated for ecommerce with subcategories (parent IDs are the root categories)
CATEGORY_SLUG_TO_ID = {
    "books": 1,
    "fiction": 2,
    "non-fiction": 3,
    "science": 4,
    "history": 5,
    "technology-books": 6,
    "electronics": 7,
    "phones-tablets": 8,
    "laptops-computers": 9,
    "audio": 10,
    "cameras": 11,
    "clothing": 12,
    "mens-clothing": 13,
    "womens-clothing": 14,
    "kids-clothing": 15,
    "shoes": 16,
    "food-beverages": 17,
    "snacks": 18,
    "beverages": 19,
    "organic": 20,
    "home-garden": 21,
    "furniture": 22,
    "kitchen": 23,
    "decor": 24,
    "sports-outdoors": 25,
    "fitness": 26,
    "outdoor": 27,
    "team-sports": 28,
}

SAMPLE_PRODUCTS = [
    # Books (Fiction / Non-fiction / Science / History / Tech)
    {"title": "Letters from M/M (Paris)", "brand": "M/M Paris", "price": 39, "category": "fiction",
     "product_type": "BOOK", "image": "https://m.media-amazon.com/images/I/81fcH8Y-oqL._AC_UF894,1000_QL80_.jpg",
     "description": "A comprehensive survey of M/M Paris — the studio that redefined the boundaries between art and commercial graphic design.",
     "sku": "BK-9780500025871", "attributes": {"author": "M/M Paris", "pages": 328, "isbn": "978-0-500-02587-1", "language": "English", "published_date": "2023-01-01"}},
    {"title": "Clean Code", "brand": "Robert C. Martin", "price": 34, "category": "technology-books",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=600&q=80",
     "description": "A handbook of agile software craftsmanship and maintainable code practices.",
     "sku": "BK-9780132350884", "attributes": {"author": "Robert C. Martin", "pages": 464, "isbn": "978-0-13-235088-4", "language": "English", "published_date": "2008-08-01"}},
    {"title": "Dieter Rams: The Complete Works", "brand": "Klaus Klemp", "price": 29, "category": "non-fiction",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80",
     "description": "The definitive monograph on Dieter Rams and his principles of good design.",
     "sku": "BK-9780714879747", "attributes": {"author": "Klaus Klemp & Keiko Ueki-Polet", "pages": 480, "isbn": "978-0-7148-7974-7", "language": "English", "published_date": "2021-01-01"}},
    {"title": "Sapiens: A Brief History of Humankind", "brand": "Yuval Noah Harari", "price": 22, "category": "history",
     "product_type": "BOOK", "image": "https://bizweb.dktcdn.net/100/418/357/products/51xyww6zexl.jpg?v=1682391845823",
     "description": "A sweeping narrative of human history, from early hunter-gatherers to the modern age.",
     "sku": "BK-9780062316097", "attributes": {"author": "Yuval Noah Harari", "pages": 498, "isbn": "978-0-06-231609-7", "language": "English", "published_date": "2015-02-10"}},
    {"title": "The Pragmatic Programmer (20th Anniversary)", "brand": "Andrew Hunt & David Thomas", "price": 38, "category": "technology-books",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=600&q=80",
     "description": "Modern software engineering wisdom: pragmatism, craftsmanship, and working effectively.",
     "sku": "BK-9780135957059", "attributes": {"author": "Andrew Hunt & David Thomas", "pages": 352, "isbn": "978-0-13-595705-9", "language": "English", "published_date": "2019-09-13"}},
    {"title": "Deep Work", "brand": "Cal Newport", "price": 18, "category": "non-fiction",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=600&q=80",
     "description": "Rules for focused success in a distracted world: attention, habits, and meaningful output.",
     "sku": "BK-9781455586691", "attributes": {"author": "Cal Newport", "pages": 304, "isbn": "978-1-4555-8669-1", "language": "English", "published_date": "2016-01-05"}},
    {"title": "A Brief History of Time", "brand": "Stephen Hawking", "price": 17, "category": "science",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1529473814998-077b4fec6770?w=600&q=80",
     "description": "From the Big Bang to black holes: an accessible tour of modern cosmology.",
     "sku": "BK-9780553380163", "attributes": {"author": "Stephen Hawking", "pages": 212, "isbn": "978-0-553-38016-3", "language": "English", "published_date": "1998-09-01"}},
    {"title": "The Martian", "brand": "Andy Weir", "price": 15, "category": "fiction",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=600&q=80",
     "description": "A survival story on Mars with engineering, humor, and relentless problem solving.",
     "sku": "BK-9780804139021", "attributes": {"author": "Andy Weir", "pages": 387, "isbn": "978-0-8041-3902-1", "language": "English", "published_date": "2014-02-11"}},
    {"title": "Atomic Habits", "brand": "James Clear", "price": 19, "category": "non-fiction",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=600&q=80",
     "description": "Tiny changes, remarkable results: practical systems for building good habits and breaking bad ones.",
     "sku": "BK-9780735211292", "attributes": {"author": "James Clear", "pages": 320, "isbn": "978-0-7352-1129-2", "language": "English", "published_date": "2018-10-16"}},
    {"title": "Guns, Germs, and Steel", "brand": "Jared Diamond", "price": 21, "category": "history",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1473186578172-c141e6798cf4?w=600&q=80",
     "description": "A provocative account of how geography and environment shaped the fates of human societies.",
     "sku": "BK-9780393317558", "attributes": {"author": "Jared Diamond", "pages": 528, "isbn": "978-0-393-31755-8", "language": "English", "published_date": "1999-03-01"}},
    {"title": "Introduction to Algorithms", "brand": "Cormen et al.", "price": 99, "category": "technology-books",
     "product_type": "BOOK", "image": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=600&q=80",
     "description": "A comprehensive reference for algorithms, data structures, and analysis.",
     "sku": "BK-9780262046305", "attributes": {"author": "Thomas H. Cormen", "pages": 1312, "isbn": "978-0-262-04630-5", "language": "English", "published_date": "2022-04-05"}},

    # Electronics (Phones/Tablets / Laptops/Computers / Audio / Cameras)
    {"title": "Sony WH-1000XM5 Wireless Headphones", "brand": "Sony", "price": 349, "category": "audio",
     "product_type": "ELECTRONICS", "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80",
     "description": "Noise canceling headphones with clear calls and long battery life.",
     "sku": "EL-SONYWH1000XM5", "attributes": {"warranty": "12 months", "connectivity": "Bluetooth 5.2", "battery_life": "30 hours", "color": "Black"}},
    {"title": "MacBook Air M3 15-inch", "brand": "Apple", "price": 1299, "category": "laptops-computers",
     "product_type": "ELECTRONICS", "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&q=80",
     "description": "Thin, light laptop with a bright display and excellent battery life.",
     "sku": "EL-APPMBAM3-15", "attributes": {"warranty": "12 months", "specs": {"cpu": "Apple M3", "ram": "8GB", "storage": "256GB SSD"}, "color": "Midnight"}},
    {"title": "iPhone 15 Pro 128GB", "brand": "Apple", "price": 999, "category": "phones-tablets",
     "product_type": "ELECTRONICS", "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&q=80",
     "description": "Pro-grade smartphone with a fast chip, advanced camera system, and titanium design.",
     "sku": "EL-APP-IP15P-128", "attributes": {"warranty": "12 months", "storage": "128GB", "color": "Natural Titanium", "connectivity": "5G"}},
    {"title": "Samsung Galaxy S24 256GB", "brand": "Samsung", "price": 899, "category": "phones-tablets",
     "product_type": "ELECTRONICS", "image": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&q=80",
     "description": "Flagship Android phone with a vivid display, fast performance, and versatile cameras.",
     "sku": "EL-SAM-S24-256", "attributes": {"warranty": "12 months", "storage": "256GB", "color": "Onyx Black", "connectivity": "5G"}},
    {"title": "iPad Air 11-inch Wi‑Fi 128GB", "brand": "Apple", "price": 599, "category": "phones-tablets",
     "product_type": "ELECTRONICS", "image": "https://images.unsplash.com/photo-1585790050230-5dd28404ccb9?w=600&q=80",
     "description": "Lightweight tablet for work and play with a sharp display and fast performance.",
     "sku": "EL-APP-IPADA11-128", "attributes": {"warranty": "12 months", "storage": "128GB", "connectivity": "Wi‑Fi", "color": "Starlight"}},
    {"title": "Dell XPS 13 (i7 / 16GB / 512GB)", "brand": "Dell", "price": 1199, "category": "laptops-computers",
     "product_type": "ELECTRONICS", "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&q=80",
     "description": "Compact premium ultrabook with a crisp display and solid keyboard.",
     "sku": "EL-DELL-XPS13-I7", "attributes": {"warranty": "12 months", "specs": {"cpu": "Intel i7", "ram": "16GB", "storage": "512GB SSD"}, "color": "Platinum Silver"}},
    {"title": "Logitech MX Master 3S Mouse", "brand": "Logitech", "price": 99, "category": "electronics",
     "product_type": "ELECTRONICS", "image": "https://images.unsplash.com/photo-1586348943529-beaae6c28db9?w=600&q=80",
     "description": "Ergonomic productivity mouse with precise scrolling and quiet clicks.",
     "sku": "EL-LOGI-MXMASTER3S", "attributes": {"warranty": "24 months", "connectivity": "Bluetooth / USB", "color": "Graphite"}},
    {"title": "Keychron K2 Mechanical Keyboard", "brand": "Keychron", "price": 89, "category": "electronics",
     "product_type": "ELECTRONICS", "image": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&q=80",
     "description": "Wireless mechanical keyboard with compact layout and multi-device switching.",
     "sku": "EL-KEYCHRON-K2", "attributes": {"warranty": "12 months", "switch_type": "Brown", "connectivity": "Bluetooth / USB-C", "layout": "75%"}},
    {"title": "Canon EOS R50 Mirrorless Camera", "brand": "Canon", "price": 679, "category": "cameras",
     "product_type": "ELECTRONICS", "image": "https://cdn.vjshop.vn/may-anh/mirrorless/canon/canon-eos-r50/black-18-45/canon-eos-r50-lens-18-45mm-500x500.jpg",
     "description": "Compact mirrorless camera for creators with fast autofocus and 4K video.",
     "sku": "EL-CAN-R50-BODY", "attributes": {"warranty": "12 months", "sensor": "APS-C", "video": "4K", "mount": "RF"}},
    {"title": "Anker 20W USB-C Charger", "brand": "Anker", "price": 19, "category": "electronics",
     "product_type": "ELECTRONICS", "image": "https://cdnv2.tgdd.vn/mwg-static/tgdd/Products/Images/9499/330020/adapter-sac-2-cong-usb-type-c-iq3-20w-anker-a2348-den-1-638893150043982173-750x500.jpg",
     "description": "Compact fast charger for phones and tablets with USB-C Power Delivery.",
     "sku": "EL-ANK-CHG-20W", "attributes": {"warranty": "18 months", "power": "20W", "ports": 1, "connector": "USB-C"}},

    # Clothing (Mens / Womens / Kids / Shoes)
    {"title": "Classic Fit Oxford Shirt", "brand": "Ralph Lauren", "price": 89, "category": "mens-clothing",
     "product_type": "CLOTHING", "image": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600&q=80",
     "description": "Breathable cotton oxford shirt in a polished classic fit.",
     "sku": "CL-RL-OXFORD-M01", "attributes": {"sizes": ["S", "M", "L", "XL"], "color": "White", "material": "100% Cotton"}},
    {"title": "Women's Premium Running Shoes", "brand": "Nike", "price": 129, "category": "shoes",
     "product_type": "CLOTHING", "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80",
     "description": "Responsive foam cushioning and breathable upper for daily training.",
     "sku": "CL-NK-RUNSH-W01", "attributes": {"sizes": ["6", "7", "8", "9", "10"], "color": "Hot Pink", "material": "Flyknit"}},
    {"title": "Men's Slim Jeans", "brand": "Levi's", "price": 79, "category": "mens-clothing",
     "product_type": "CLOTHING", "image": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600&q=80",
     "description": "Everyday slim-fit denim with comfortable stretch and classic 5-pocket styling.",
     "sku": "CL-LV-SLIMJ-M01", "attributes": {"sizes": ["30", "32", "34", "36"], "color": "Indigo", "material": "Denim"}},
    {"title": "Women's Oversized Hoodie", "brand": "Adidas", "price": 69, "category": "womens-clothing",
     "product_type": "CLOTHING", "image": "https://us.blakelyclothing.com/cdn/shop/products/2011WbeigeD-1_800x.jpg?v=1676370836",
     "description": "Soft fleece hoodie with relaxed silhouette and ribbed cuffs.",
     "sku": "CL-ADS-HOOD-W01", "attributes": {"sizes": ["XS", "S", "M", "L"], "color": "Heather Grey", "material": "Cotton blend"}},
    {"title": "Kids Cotton T‑Shirt Pack (3)", "brand": "Uniqlo", "price": 24, "category": "kids-clothing",
     "product_type": "CLOTHING", "image": "https://images.unsplash.com/photo-1520975661595-6453be3f7070?w=600&q=80",
     "description": "Soft everyday tees for kids with durable stitching and comfortable fit.",
     "sku": "CL-UNQ-KTS-3PK", "attributes": {"sizes": ["90", "100", "110", "120"], "color": "Assorted", "material": "100% Cotton"}},
    {"title": "Leather Chelsea Boots", "brand": "Clarks", "price": 149, "category": "shoes",
     "product_type": "CLOTHING", "image": "https://thursdayboots.com/cdn/shop/products/1024x1024-Men-Cavalier-Black-092121-3.4_1024x1024.jpg?v=1633034593",
     "description": "Classic pull-on boots with elastic side panels and durable outsole.",
     "sku": "CL-CLK-CHELS-M01", "attributes": {"sizes": ["7", "8", "9", "10", "11"], "color": "Dark Brown", "material": "Leather"}},
    {"title": "Women's Summer Dress", "brand": "Zara", "price": 59, "category": "womens-clothing",
     "product_type": "CLOTHING", "image": "https://images-cdn.ubuy.co.in/635e29037403ec6f010f8f6f-summer-dresses-for-women-2022-women-s.jpg",
     "description": "Lightweight dress with a flattering cut for warm-weather days.",
     "sku": "CL-ZRA-DRESS-W01", "attributes": {"sizes": ["XS", "S", "M", "L"], "color": "Floral", "material": "Viscose"}},

    # Food & Beverages (Snacks / Beverages / Organic)
    {"title": "Organic Matcha Green Tea Powder", "brand": "Jade Leaf", "price": 24, "category": "organic",
     "product_type": "FOOD", "image": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=600&q=80",
     "description": "Authentic organic matcha for lattes, smoothies, and baking.",
     "sku": "FD-JL-MATCHA100", "attributes": {"weight": "100g", "origin": "Uji, Japan", "ingredients": ["organic matcha green tea"]}},
    {"title": "Cold Brew Coffee Concentrate", "brand": "Stumptown", "price": 16, "category": "beverages",
     "product_type": "FOOD", "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&q=80",
     "description": "Smooth cold brew concentrate. Mix with water or milk for an easy iced coffee.",
     "sku": "FD-ST-CB-CONC", "attributes": {"volume": "500ml", "origin": "Blend", "caffeine": "High"}},
    {"title": "Sea Salt Dark Chocolate Bar", "brand": "Lindt", "price": 5, "category": "snacks",
     "product_type": "FOOD", "image": "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=600&q=80",
     "description": "Rich dark chocolate balanced with a hint of sea salt.",
     "sku": "FD-LDT-DS-100", "attributes": {"weight": "100g", "cocoa": "70%", "allergens": ["milk", "soy"]}},
    {"title": "Roasted Almonds (Unsalted)", "brand": "Planters", "price": 8, "category": "snacks",
     "product_type": "FOOD", "image": "https://nuts.com/images/rackcdn/ed910ae2d60f0d25bcb8-80550f96b5feb12604f4f720bfefb46d.ssl.cf1.rackcdn.com/e54713f3a6d21cf3-lts0Khbk-zoom.jpg",
     "description": "Crunchy roasted almonds. A simple snack with clean ingredients.",
     "sku": "FD-PLN-ALM-400", "attributes": {"weight": "400g", "ingredients": ["almonds"], "allergens": ["nuts"]}},
    {"title": "Sparkling Water Variety Pack", "brand": "LaCroix", "price": 12, "category": "beverages",
     "product_type": "FOOD", "image": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553?w=600&q=80",
     "description": "Refreshing flavored sparkling water with zero sugar.",
     "sku": "FD-LCR-SWP-12", "attributes": {"count": 12, "flavors": ["Lime", "Grapefruit", "Berry"], "sugar": "0g"}},
    {"title": "Organic Extra Virgin Olive Oil", "brand": "Bertolli", "price": 14, "category": "organic",
     "product_type": "FOOD", "image": "https://images.unsplash.com/photo-1514996937319-344454492b37?w=600&q=80",
     "description": "Cold-pressed organic extra virgin olive oil for cooking and salads.",
     "sku": "FD-BER-EVOO-750", "attributes": {"volume": "750ml", "origin": "Mediterranean", "ingredients": ["organic olives"]}},

    # Home & Garden (Furniture / Kitchen / Decor)
    {"title": "Scandinavian Oak Coffee Table", "brand": "IKEA", "price": 199, "category": "furniture",
     "product_type": "HOME", "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&q=80",
     "description": "Minimalist oak coffee table with clean lines and natural finish.",
     "sku": "HM-IK-OAKCTBL01", "attributes": {"dimensions": "120x60x45cm", "material": "Solid Oak", "weight": "15kg"}},
    {"title": "Ergonomic Office Chair", "brand": "Herman Miller", "price": 999, "category": "furniture",
     "product_type": "HOME", "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQvKbJs87del7Y6nBRCKm__R5HR7X62wLfdDw&s",
     "description": "Premium ergonomic chair designed for long work sessions and better posture.",
     "sku": "HM-HM-ERGOCHR01", "attributes": {"material": "Mesh", "color": "Graphite", "warranty": "12 years"}},
    {"title": "Nonstick Frying Pan 28cm", "brand": "Tefal", "price": 39, "category": "kitchen",
     "product_type": "HOME", "image": "https://images-na.ssl-images-amazon.com/images/I/71FlPCBSmoL.jpg",
     "description": "Everyday nonstick pan with even heating and comfortable handle.",
     "sku": "HM-TEF-PAN-28", "attributes": {"diameter": "28cm", "material": "Aluminum", "coating": "Nonstick"}},
    {"title": "Stainless Steel Chef Knife 8-inch", "brand": "Victorinox", "price": 49, "category": "kitchen",
     "product_type": "HOME", "image": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&q=80",
     "description": "Sharp, balanced chef knife for everyday prep in the kitchen.",
     "sku": "HM-VTX-KNIFE-8", "attributes": {"blade_length": "8-inch", "material": "Stainless Steel", "handle": "Fibrox"}},
    {"title": "Minimalist Wall Clock", "brand": "Muji", "price": 29, "category": "decor",
     "product_type": "HOME", "image": "https://images.unsplash.com/photo-1509644851169-2acc08aa25b5?w=600&q=80",
     "description": "Quiet wall clock with clean dial and easy-to-read markers.",
     "sku": "HM-MUJI-CLOCK01", "attributes": {"diameter": "25cm", "power": "AA battery", "color": "White"}},
    {"title": "Scented Candle - Vanilla", "brand": "Yankee Candle", "price": 19, "category": "decor",
     "product_type": "HOME", "image": "https://m.media-amazon.com/images/I/81HSydTuXVL.jpg",
     "description": "Warm vanilla fragrance for cozy evenings and relaxing ambience.",
     "sku": "HM-YC-VAN-CNDL", "attributes": {"burn_time": "45 hours", "scent": "Vanilla", "weight": "400g"}},

    # Sports & Outdoors (Fitness / Outdoor / Team sports)
    {"title": "Adjustable Dumbbell Set 20kg", "brand": "Bowflex", "price": 179, "category": "fitness",
     "product_type": "SPORTS", "image": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&q=80",
     "description": "Replace multiple weights with one compact adjustable set.",
     "sku": "SP-BF-DUMBBL20", "attributes": {"weight_range": "2-20kg", "material": "Steel with rubber grip"}},
    {"title": "Yoga Mat 6mm", "brand": "Manduka", "price": 79, "category": "fitness",
     "product_type": "SPORTS", "image": "https://m.media-amazon.com/images/I/41fQHCuWAsL._AC_UF894,1000_QL80_.jpg",
     "description": "Durable yoga mat with great grip for daily practice.",
     "sku": "SP-MDK-YOGAMAT6", "attributes": {"thickness": "6mm", "material": "PVC", "color": "Black"}},
    {"title": "Running Water Bottle 500ml", "brand": "Nike", "price": 14, "category": "fitness",
     "product_type": "SPORTS", "image": "https://m.media-amazon.com/images/I/61XvgOL89lL.jpg",
     "description": "Lightweight bottle with easy-sip nozzle for training sessions.",
     "sku": "SP-NK-BTTL-500", "attributes": {"volume": "500ml", "material": "BPA-free plastic"}},
    {"title": "Camping Tent 2-Person", "brand": "Coleman", "price": 119, "category": "outdoor",
     "product_type": "SPORTS", "image": "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=600&q=80",
     "description": "Quick setup tent with rainfly for weekend camping trips.",
     "sku": "SP-CLM-TENT-2P", "attributes": {"capacity": "2-person", "season": "3-season", "weight": "2.9kg"}},
    {"title": "Outdoor Hiking Backpack 30L", "brand": "Osprey", "price": 149, "category": "outdoor",
     "product_type": "SPORTS", "image": "https://ampexgear.com/cdn/shop/files/AMP6001950LBackpack_10_a9ae3989-8d05-40ac-8f03-721588f0e996.jpg?v=1692995580&width=1500",
     "description": "Comfortable daypack with breathable back panel and hydration compatibility.",
     "sku": "SP-OSP-PACK-30L", "attributes": {"capacity": "30L", "weight": "1.2kg", "color": "Blue"}},
    {"title": "Soccer Ball - Match Size 5", "brand": "Adidas", "price": 29, "category": "team-sports",
     "product_type": "SPORTS", "image": "https://images.unsplash.com/photo-1518091043644-c1d4457512c6?w=600&q=80",
     "description": "Durable size 5 ball for training and casual matches.",
     "sku": "SP-ADS-SOCC-5", "attributes": {"size": 5, "material": "PU", "color": "White/Black"}},
]

CUSTOMERS = [
    {"email": "user1@example.com", "first_name": "Alice", "last_name": "Nguyen", "phone": "0901234567", "address": "123 Hanoi"},
    {"email": "user2@example.com", "first_name": "Bob", "last_name": "Tran", "phone": "0912345678", "address": "456 Ho Chi Minh"},
    {"email": "user3@example.com", "first_name": "Carol", "last_name": "Le", "phone": "0923456789", "address": "789 Da Nang"},
    {"email": "user4@example.com", "first_name": "David", "last_name": "Pham", "phone": "0934567890", "address": "101 Can Tho"},
    {"email": "user5@example.com", "first_name": "Eve", "last_name": "Hoang", "phone": "0945678901", "address": "202 Hue"},
    {"email": "user6@example.com", "first_name": "Frank", "last_name": "Vo", "phone": "0956789012", "address": "303 Nha Trang"},
    {"email": "user7@example.com", "first_name": "Grace", "last_name": "Dang", "phone": "0967890123", "address": "404 Hai Phong"},
    {"email": "user8@example.com", "first_name": "Henry", "last_name": "Bui", "phone": "0978901234", "address": "505 Vung Tau"},
    {"email": "user9@example.com", "first_name": "Ivy", "last_name": "Do", "phone": "0989012345", "address": "606 Dalat"},
    {"email": "user10@example.com", "first_name": "Jack", "last_name": "Ly", "phone": "0990123456", "address": "707 Quy Nhon"},
]

# pass: Password123!

def run_exec(service: str, cmd: str) -> bool:
    """Run command in Docker Compose service. Returns True on success."""
    full_cmd = [
        "docker", "compose", "exec", "-T", service,
        "python", "manage.py", "shell", "-c", cmd
    ]
    try:
        result = subprocess.run(
            full_cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"  Error: {result.stderr or result.stdout}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("  Timeout")
        return False
    except FileNotFoundError:
        print("  docker compose not found. Ensure Docker is running.")
        return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False


def seed_products():
    print("2. Seeding products...")
    products_data = []
    for p in SAMPLE_PRODUCTS:
        cat_id = CATEGORY_SLUG_TO_ID.get(p["category"], 1)
        products_data.append({
            "sku": p["sku"],
            "title": p["title"],
            "brand": p["brand"],
            "price": p["price"],
            "description": p["description"],
            "cover_image": p["image"],
            "category_id": cat_id,
            "product_type": p["product_type"],
            "attributes": p["attributes"],
        })
    data_json = json.dumps(products_data)
    code = f"""
from products.models import Product, ProductInventory
import json
data = json.loads('''{data_json}''')
created_count = 0
updated_count = 0
for d in data:
    _, created = Product.objects.update_or_create(sku=d["sku"], defaults={{
        "title": d["title"], "brand": d["brand"], "price": d["price"],
        "description": d["description"], "cover_image": d["cover_image"],
        "category_id": d["category_id"], "product_type": d["product_type"],
        "attributes": d["attributes"], "is_active": True
    }})
    if created:
        created_count += 1
    else:
        updated_count += 1
for product in Product.objects.all():
    ProductInventory.objects.get_or_create(product=product, defaults={{"stock_quantity": 50}})
print("Products:", Product.objects.count())
print("Created:", created_count, "Updated:", updated_count)
"""
    return run_exec("product-service", code)


def seed_admin():
    print("3. Creating admin account (admin@store.com / " + DEFAULT_PASSWORD + ")...")
    code = """
from management.models import ManagerUser
u, created = ManagerUser.objects.get_or_create(
    email="admin@store.com",
    defaults={"first_name": "Admin", "last_name": "Manager", "is_active": True}
)
if created:
    u.set_password("Password123!")
    u.save()
    print("Admin created")
else:
    print("Admin already exists")
"""
    return run_exec("manager-service", code)


def seed_staff():
    print("4. Creating staff account (staff@store.com / " + DEFAULT_PASSWORD + ")...")
    code = """
from staff.models import StaffMember
u, created = StaffMember.objects.get_or_create(
    email="staff@store.com",
    defaults={"first_name": "Staff", "last_name": "User", "role": "SALES", "is_admin": True, "is_active": True}
)
if created:
    u.set_password("Password123!")
    u.save()
    print("Staff created")
else:
    print("Staff already exists")
"""
    return run_exec("staff-service", code)


def seed_customers():
    print("5. Creating 10 customer accounts (user1@example.com ... user10@example.com / " + DEFAULT_PASSWORD + ")...")
    customers_json = json.dumps(CUSTOMERS)
    code = f"""
from customers.models import Customer
import json
data = json.loads('''{customers_json}''')
for d in data:
    u, created = Customer.objects.get_or_create(
        email=d["email"],
        defaults={{"first_name": d["first_name"], "last_name": d["last_name"], "phone": d.get("phone", ""), "address": d.get("address", ""), "is_active": True}}
    )
    if created:
        u.set_password("Password123!")
        u.save()
print("Customers:", Customer.objects.count())
"""
    return run_exec("customer-service", code)


def seed_orders():
    print("6. Creating sample orders for customers...")
    products_mini = [{"id": i+1, "title": p["title"], "price": p["price"]} for i, p in enumerate(SAMPLE_PRODUCTS)]
    products_json = json.dumps(products_mini)
    
    code = f"""
from orders.models import Order, OrderItem
from decimal import Decimal
import json
import random

if Order.objects.exists():
    print("Deleting old orders to create fresh ones...")
    Order.objects.all().delete()

products = json.loads('''{products_json}''')
statuses = ["PENDING", "CONFIRMED", "PAID", "SHIPPED", "DELIVERED", "CANCELLED", "REFUNDED"]
addresses = [
    "123 Hanoi", "456 Ho Chi Minh", "789 Da Nang", "101 Can Tho", "202 Hue",
    "303 Nha Trang", "404 Hai Phong", "505 Vung Tau", "606 Dalat", "707 Quy Nhon"
]
orders_created = 0
for cid in range(1, 11):
    num_orders = random.randint(6, 10)
    for _ in range(num_orders):
        status = random.choice(statuses)
        address = addresses[cid - 1]
        order = Order.objects.create(
            customer_id=cid,
            status=status,
            total_amount=0,
            shipping_address=address,
            payment_method=random.choice(["CREDIT_CARD", "PAYPAL", "CASH_ON_DELIVERY"])
        )
        
        total = Decimal('0.00')
        num_items = random.randint(1, 4)
        items = random.sample(products, num_items)
        for item in items:
            qty = random.randint(1, 3)
            price = Decimal(str(item["price"]))
            total += price * qty
            OrderItem.objects.create(
                order=order,
                product_id=item["id"],
                product_title=item["title"],
                quantity=qty,
                unit_price=price
            )
        order.total_amount = total
        order.save()
        orders_created += 1
        
print("Orders created:", orders_created)
"""
    return run_exec("order-service", code)


def main():
    print("=" * 50)
    print("Ecommerce Store Seed Data Script")
    print("=" * 50)
    print("Ensure Docker Compose is running: docker compose up -d")
    print()

    ok = True
    ok &= seed_products()
    ok &= seed_admin()
    ok &= seed_staff()
    ok &= seed_customers()
    ok &= seed_orders()

    print()
    if ok:
        print("Done! Summary:")
        print("  - Admin:  admin@store.com / " + DEFAULT_PASSWORD)
        print("  - Staff:  staff@store.com / " + DEFAULT_PASSWORD)
        print("  - Users:  user1@example.com ... user10@example.com / " + DEFAULT_PASSWORD)
        print("  - Sample orders created for users!")
    else:
        print("Some steps failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
