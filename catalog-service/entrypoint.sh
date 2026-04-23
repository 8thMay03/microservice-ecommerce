#!/bin/sh

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 0.2
done
echo "PostgreSQL is ready."

python manage.py migrate --noinput
python manage.py shell -c "
from catalog.models import Category

if not Category.objects.exists():
    # ── Books ──
    books = Category.objects.create(name='Books', slug='books', description='Books & Literature')
    Category.objects.create(name='Fiction', slug='fiction', description='Fiction novels', parent=books)
    Category.objects.create(name='Non-Fiction', slug='non-fiction', description='Non-fiction books', parent=books)
    Category.objects.create(name='Science', slug='science', description='Science books', parent=books)
    Category.objects.create(name='History', slug='history', description='History books', parent=books)
    Category.objects.create(name='Technology', slug='technology-books', description='Tech & programming books', parent=books)

    # ── Electronics ──
    electronics = Category.objects.create(name='Electronics', slug='electronics', description='Electronic devices & accessories')
    Category.objects.create(name='Phones & Tablets', slug='phones-tablets', description='Smartphones and tablets', parent=electronics)
    Category.objects.create(name='Laptops & Computers', slug='laptops-computers', description='Laptops and desktop computers', parent=electronics)
    Category.objects.create(name='Audio', slug='audio', description='Headphones, speakers, and audio equipment', parent=electronics)
    Category.objects.create(name='Cameras', slug='cameras', description='Digital cameras and accessories', parent=electronics)

    # ── Clothing ──
    clothing = Category.objects.create(name='Clothing', slug='clothing', description='Fashion & apparel')
    Category.objects.create(name='Men', slug='mens-clothing', description='Men clothing', parent=clothing)
    Category.objects.create(name='Women', slug='womens-clothing', description='Women clothing', parent=clothing)
    Category.objects.create(name='Kids', slug='kids-clothing', description='Kids clothing', parent=clothing)
    Category.objects.create(name='Shoes', slug='shoes', description='Footwear', parent=clothing)

    # ── Food & Beverages ──
    food = Category.objects.create(name='Food & Beverages', slug='food-beverages', description='Food, snacks, and drinks')
    Category.objects.create(name='Snacks', slug='snacks', description='Snacks & confectionery', parent=food)
    Category.objects.create(name='Beverages', slug='beverages', description='Drinks & beverages', parent=food)
    Category.objects.create(name='Organic', slug='organic', description='Organic & natural food', parent=food)

    # ── Home & Garden ──
    home = Category.objects.create(name='Home & Garden', slug='home-garden', description='Home decor, furniture, and garden')
    Category.objects.create(name='Furniture', slug='furniture', description='Home furniture', parent=home)
    Category.objects.create(name='Kitchen', slug='kitchen', description='Kitchen tools & appliances', parent=home)
    Category.objects.create(name='Decor', slug='decor', description='Home decoration', parent=home)

    # ── Sports & Outdoors ──
    sports = Category.objects.create(name='Sports & Outdoors', slug='sports-outdoors', description='Sports equipment & outdoor gear')
    Category.objects.create(name='Fitness', slug='fitness', description='Fitness & gym equipment', parent=sports)
    Category.objects.create(name='Outdoor', slug='outdoor', description='Outdoor & camping gear', parent=sports)
    Category.objects.create(name='Team Sports', slug='team-sports', description='Team sports equipment', parent=sports)

    print('Created ecommerce categories with subcategories')
"
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
