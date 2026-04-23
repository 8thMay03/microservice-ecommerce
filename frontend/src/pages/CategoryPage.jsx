import { useState, useMemo, useEffect } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { SlidersHorizontal, ChevronDown, X, Search, Loader2 } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ProductCard from "../components/ProductCard";
import CategoryFilter from "../components/CategoryFilter";
import { useProducts } from "../hooks/useProducts";
import { useCatalog } from "../hooks/useCatalog";

const SORT_OPTIONS = [
  { value: "featured", label: "Featured" },
  { value: "price-asc", label: "Price: Low to High" },
  { value: "price-desc", label: "Price: High to Low" },
  { value: "newest", label: "Newest" },
];

const PRICE_RANGES = [
  { label: "Under $25", min: 0, max: 25 },
  { label: "$25 – $40", min: 25, max: 40 },
  { label: "$40 – $60", min: 40, max: 60 },
  { label: "Over $60", min: 60, max: Infinity },
];

export default function CategoryPage() {
  const { id: categoryId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchQuery = searchParams.get("search") || "";

  const [sort, setSort] = useState("featured");
  const [sortOpen, setSortOpen] = useState(false);
  const [selectedPriceRange, setSelectedPriceRange] = useState(null);
  const [localSearch, setLocalSearch] = useState(() => searchQuery || "");
  const [showFilters, setShowFilters] = useState(false);
  const [onlyNew, setOnlyNew] = useState(false);

  const { categories } = useCatalog();
  const apiParams = useMemo(() => {
    const p = { page_size: 100 };
    if (categoryId && categoryId !== "all") p.category_id = categoryId;
    if (localSearch) p.search = localSearch;
    if (selectedPriceRange) {
      p.min_price = selectedPriceRange.min;
      p.max_price = selectedPriceRange.max === Infinity ? 9999 : selectedPriceRange.max;
    }
    return p;
  }, [categoryId, localSearch, selectedPriceRange]);

  const { results: products, loading, refetch } = useProducts(apiParams);


  const activeCategoryLabel =
    categoryId === "all"
      ? "All Products"
      : categories.find((c) => String(c.id) === String(categoryId))?.name ?? "Products";

  const filteredProducts = useMemo(() => {
    let result = [...products];
    if (onlyNew) result = result.filter((p) => p.isNew);
    switch (sort) {
      case "price-asc":
        return result.sort((a, b) => a.price - b.price);
      case "price-desc":
        return result.sort((a, b) => b.price - a.price);
      case "newest":
        return result.sort((a, b) => new Date(b.published_date || 0) - new Date(a.published_date || 0));
      default:
        return result;
    }
  }, [products, sort, onlyNew]);

  const activeFiltersCount =
    (selectedPriceRange ? 1 : 0) + (onlyNew ? 1 : 0) + (localSearch ? 1 : 0);

  const clearFilters = () => {
    setSelectedPriceRange(null);
    setOnlyNew(false);
    setLocalSearch("");
    setSearchParams({});
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (localSearch) setSearchParams({ search: localSearch });
    else setSearchParams({});
  };

  return (
    <div className="min-h-screen flex flex-col bg-stone-50">
      <Navbar />

      <main className="flex-1">
        <div className="border-b border-gray-200 bg-white animate-fade-up">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
            <nav className="flex items-center gap-2 text-xs text-gray-400 mb-4">
              <Link to="/" className="hover:text-gray-600 transition-colors">Home</Link>
              <span>/</span>
              <span className="text-gray-600">{activeCategoryLabel}</span>
            </nav>

            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
              <div>
                <h1 className="font-serif text-4xl font-medium text-gray-900">
                  {activeCategoryLabel}
                </h1>
                <p className="text-gray-500 text-sm mt-2">
                  {loading ? "Loading…" : `${filteredProducts.length} product${filteredProducts.length !== 1 ? "s" : ""} available`}
                </p>
              </div>

              <div className="overflow-x-auto scrollbar-hide">
                <CategoryFilter
                  activeCategory={categoryId ?? "all"}
                  categories={categories}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-up animate-delay-2">
          <div className="flex flex-wrap items-center gap-3 mb-8">
            <form onSubmit={handleSearchSubmit} className="flex items-center bg-white border border-gray-200 rounded-full px-4 py-2 gap-2 min-w-0 w-full sm:w-auto sm:flex-1 max-w-xs">
              <Search size={14} className="text-gray-400 shrink-0" />
              <input
                value={localSearch}
                onChange={(e) => setLocalSearch(e.target.value)}
                placeholder="Search by title, brand…"
                className="bg-transparent text-sm outline-none flex-1 text-gray-900 placeholder-gray-400"
              />
              {localSearch && (
                <button type="button" onClick={() => { setLocalSearch(""); setSearchParams({}); }} className="text-gray-400 hover:text-gray-600">
                  <X size={13} />
                </button>
              )}
            </form>

            <button
              onClick={() => setShowFilters((v) => !v)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium transition-all ${
                showFilters || activeFiltersCount > 0
                  ? "bg-gray-900 text-white border-gray-900"
                  : "bg-white border-gray-200 text-gray-700 hover:border-gray-400"
              }`}
            >
              <SlidersHorizontal size={14} />
              Filters
              {activeFiltersCount > 0 && (
                <span className="bg-[#e8392a] text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center font-bold">
                  {activeFiltersCount}
                </span>
              )}
            </button>

            <div className="relative ml-auto">
              <button
                onClick={() => setSortOpen((v) => !v)}
                className="flex items-center gap-2 px-4 py-2 rounded-full border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:border-gray-400 transition-colors"
              >
                Sort: {SORT_OPTIONS.find((o) => o.value === sort)?.label}
                <ChevronDown size={13} className={`transition-transform ${sortOpen ? "rotate-180" : ""}`} />
              </button>

              {sortOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setSortOpen(false)} />
                  <div className="absolute right-0 top-full mt-2 z-20 bg-white border border-gray-200 rounded-xl shadow-lg py-1.5 min-w-[180px]">
                    {SORT_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => { setSort(opt.value); setSortOpen(false); }}
                        className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 transition-colors ${sort === opt.value ? "text-gray-900 font-medium" : "text-gray-600"}`}
                      >
                        {opt.value === sort && <span className="mr-2">✓</span>}
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          {showFilters && (
            <div className="bg-white border border-gray-100 rounded-2xl p-6 mb-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Price Range</h3>
                <div className="flex flex-wrap gap-2">
                  {PRICE_RANGES.map((range) => {
                    const isActive = selectedPriceRange?.label === range.label;
                    return (
                      <button
                        key={range.label}
                        onClick={() => setSelectedPriceRange(isActive ? null : range)}
                        className={`pill text-xs ${isActive ? "pill-active" : "pill-inactive"}`}
                      >
                        {range.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Availability</h3>
                <button
                  onClick={() => setOnlyNew((v) => !v)}
                  className={`pill text-xs ${onlyNew ? "pill-active" : "pill-inactive"}`}
                >
                  New Arrivals Only
                </button>
              </div>

              {activeFiltersCount > 0 && (
                <div className="flex items-end">
                  <button onClick={clearFilters} className="text-sm text-red-500 hover:text-red-700 transition-colors flex items-center gap-1.5">
                    <X size={13} /> Clear all filters
                  </button>
                </div>
              )}
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-16">
              <Loader2 size={32} className="animate-spin text-gray-400" />
            </div>
          ) : filteredProducts.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-x-5 gap-y-10">
              {filteredProducts.map((product) => (
                <ProductCard key={product.id} product={product} showRating={!!product.rating} />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <Search size={22} className="text-gray-400" />
              </div>
              <h3 className="font-serif text-xl font-medium text-gray-900 mb-2">No products found</h3>
              <p className="text-gray-500 text-sm mb-6">Try adjusting your filters or search term.</p>
              <button onClick={clearFilters} className="btn-primary">Clear filters</button>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
