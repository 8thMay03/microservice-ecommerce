const PLACEHOLDER_IMAGE = "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=600&q=80";

const PRODUCT_TYPE_IMAGES = {
  BOOK: "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=600&q=80",
  ELECTRONICS: "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=600&q=80",
  CLOTHING: "https://images.unsplash.com/photo-1445205170230-053b83016050?w=600&q=80",
  FOOD: "https://images.unsplash.com/photo-1606787366850-de6330128bfc?w=600&q=80",
  HOME: "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=600&q=80",
  SPORTS: "https://images.unsplash.com/photo-1461896836934-bd45ba8a0ce4?w=600&q=80",
};

const PRODUCT_TYPE_LABELS = {
  BOOK: "Book",
  ELECTRONICS: "Electronics",
  CLOTHING: "Clothing",
  FOOD: "Food & Beverages",
  HOME: "Home & Garden",
  SPORTS: "Sports & Outdoors",
};

/** Map API product to frontend format for ProductCard/ProductDetailPage */
export function normalizeProduct(apiProduct) {
  if (!apiProduct) return null;
  const created = apiProduct.created_at ? new Date(apiProduct.created_at) : null;
  const isNew = created && (Date.now() - created) < 90 * 24 * 60 * 60 * 1000;
  const productType = apiProduct.product_type || "BOOK";
  const attrs = apiProduct.attributes || {};
  return {
    id: apiProduct.id,
    title: apiProduct.title,
    brand: apiProduct.brand || attrs.author || "",
    // Keep 'author' for backward compat in display
    author: attrs.author || apiProduct.brand || "",
    price: Number(apiProduct.price),
    image: apiProduct.cover_image || PRODUCT_TYPE_IMAGES[productType] || PLACEHOLDER_IMAGE,
    isNew,
    rating: apiProduct.rating ?? null,
    reviewCount: apiProduct.review_count ?? null,
    description: apiProduct.description || "",
    category_id: apiProduct.category_id,
    product_type: productType,
    product_type_label: PRODUCT_TYPE_LABELS[productType] || productType,
    sku: apiProduct.sku || "",
    attributes: attrs,
    inventory: apiProduct.inventory,
    // Backward compat fields for books
    pages: attrs.pages,
    isbn: attrs.isbn || apiProduct.sku,
    published_date: attrs.published_date || apiProduct.published_date,
    language: attrs.language,
  };
}

export { PRODUCT_TYPE_LABELS, PRODUCT_TYPE_IMAGES, PLACEHOLDER_IMAGE };
