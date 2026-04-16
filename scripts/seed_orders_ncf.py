#!/usr/bin/env python3
"""
Seed sample order data for NCF training.
Creates patterns:
- Users 1-5: Prefer Photography (category 7) and Architecture (category 4)
- Users 6-10: Prefer Graphic Design (category 2) and Fine Arts (category 5)
"""
import json
import subprocess
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def run_exec(service: str, cmd: str) -> bool:
    full_cmd = [
        "docker", "compose", "exec", "-T", service,
        "python", "manage.py", "shell", "-c", cmd
    ]
    try:
        result = subprocess.run(full_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  Error in {service}: {result.stderr or result.stdout}")
            return False
        return True
    except Exception as e:
        print(f"  Exception: {e}")
        return False

def seed_orders():
    print("Seeding ~100 orders with patterns for NCF...")
    
    # Define patterns (customer_id: [preferred_book_ids])
    # Note: Book IDs from seed_data.py are generally 1-10
    # Categorization based on seed_data.py:
    # 1: Paris (Graphic - 2)
    # 2: Floating Signifiers (Photo - 7)
    # 3: Maputo (Archi - 4)
    # 4: Sierra (Photo - 7)
    # 5: Dieter Rams (Product - 3)
    # 6: Indergarten (Graphic - 2)
    # 7: Concrete Poetry (Fine Arts - 5)
    # 8: Forms of Inquiry (Graphic - 2)
    # 9: Alexandra (Science - 6)
    # 10: Japanese Archi (Archi - 4)
    
    group_a_books = [2, 3, 4, 10] # Photo + Archi
    group_b_books = [1, 6, 7, 8]  # Graphic + Arts
    others = [5, 9]

    order_commands = []
    
    # 10 customers (IDs 1-10)
    for cid in range(1, 11):
        num_orders = random.randint(8, 12) # 8-12 orders per user
        for _ in range(num_orders):
            if cid <= 5:
                # Group A preference
                weights = [0.2] * 4 + [0.05] * 4 + [0.1] * 2
                pool = group_a_books + group_b_books + others
            else:
                # Group B preference
                weights = [0.05] * 4 + [0.2] * 4 + [0.1] * 2
                pool = group_a_books + group_b_books + others
            
            # Pick 1-2 items per order
            bids = random.choices(pool, weights=weights, k=random.randint(1, 2))
            bids = list(set(bids)) # unique
            
            items_json = []
            total_amount = 0
            for bid in bids:
                price = random.randint(20, 50)
                qty = random.randint(1, 2)
                total_amount += price * qty
                items_json.append({
                    "book_id": bid,
                    "book_title": f"Book {bid}",
                    "quantity": qty,
                    "unit_price": price
                })
            
            order_data = {
                "customer_id": cid,
                "status": "DELIVERED",
                "total_amount": total_amount,
                "shipping_address": "Sample Address",
                "payment_method": "CREDIT_CARD",
                "items": items_json
            }
            order_commands.append(order_data)

    print(f"Generated {len(order_commands)} order records. Injecting to order-service...")
    
    # Split into chunks to avoid command line length limits
    chunk_size = 20
    for i in range(0, len(order_commands), chunk_size):
        chunk = order_commands[i:i+chunk_size]
        data_json = json.dumps(chunk)
        code = f"""
from orders.models import Order, OrderItem
import json
data = json.loads('''{data_json}''')
for d in data:
    items = d.pop('items')
    o = Order.objects.create(**d)
    for it in items:
        OrderItem.objects.create(order=o, **it)
print("Created {len(chunk)} orders")
"""
        if not run_exec("order-service", code):
            print("Failed to inject chunk")
            return False
            
    print("Successfully seeded orders for NCF training.")
    return True

if __name__ == "__main__":
    seed_orders()
