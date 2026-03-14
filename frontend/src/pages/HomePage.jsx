import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import BookCard from "../components/BookCard";
import CategoryFilter from "../components/CategoryFilter";
import { useBooks } from "../hooks/useBooks";
import { useCatalog } from "../hooks/useCatalog";

export default function HomePage() {
  const [activeCategory, setActiveCategory] = useState("all");
  const { results: books, loading, error } = useBooks({
    page_size: 50,
    ...(activeCategory !== "all" ? { category_id: activeCategory } : {}),
  });
  const { categories } = useCatalog();

  // Fallback when API fails (backend not running, etc.)
  const safeCategories = categories.length > 0 ? categories : [{ id: "all", name: "All", slug: "all" }];

  const displayedBooks = useMemo(() => {
    if (activeCategory === "all") return books.filter((b) => b.isNew).slice(0, 6);
    return books.filter((b) => String(b.category_id) === String(activeCategory)).slice(0, 6);
  }, [books, activeCategory]);

  const editorialPicks = useMemo(() => {
    if (books.length < 2) return [];
    return [
      { label: "This Week's Editor Pick", book: books[0], accent: "from-amber-50 to-orange-100" },
      { label: "Staff Favourite", book: books[1], accent: "from-slate-50 to-gray-100" },
    ];
  }, [books]);

  return (
    <div className="min-h-screen flex flex-col bg-stone-50">
      <Navbar />

      <main className="flex-1">
        {/* ── Hero ──────────────────────────────────────────────────────── */}
        <section className="text-center px-4 pt-14 pb-10 animate-fade-up">
          <p className="text-xs font-medium tracking-[0.2em] uppercase text-gray-400 mb-5">
            Thoughtfully Curated
          </p>
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-medium text-gray-900 max-w-2xl mx-auto leading-tight">
            Discover books for{" "}
            <em className="not-italic text-gray-500">every reader.</em>
          </h1>
          <p className="mt-5 text-gray-500 text-base max-w-md mx-auto leading-relaxed">
            Explorations into books, reading culture, and the art of
            thoughtful curation.
          </p>
          <div className="flex items-center justify-center gap-3 mt-7">
            <Link to="/category/all" className="btn-primary">
              Browse all books
            </Link>
            {safeCategories[1] && (
              <Link to={`/category/${safeCategories[1].id}`} className="btn-outline">
                {safeCategories[1].name}
              </Link>
            )}
          </div>
        </section>

        {/* ── Category Filter + Grid ─────────────────────────────────── */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 animate-fade-up animate-delay-2">
          {error && (
            <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
              Không thể tải dữ liệu. Kiểm tra backend đã chạy chưa (docker compose up).
            </div>
          )}
          {/* Filter */}
          <div className="flex items-center justify-between mb-8">
            <CategoryFilter
              activeCategory={activeCategory}
              onSelect={setActiveCategory}
              categories={safeCategories}
            />
          </div>

          {/* Book grid */}
          {loading ? (
            <div className="flex justify-center py-16">
              <Loader2 size={32} className="animate-spin text-gray-400" />
            </div>
          ) : displayedBooks.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 xl:grid-cols-6 gap-x-5 gap-y-10">
              {displayedBooks.map((book) => (
                <BookCard key={book.id} book={book} />
              ))}
            </div>
          ) : (
            <div className="text-center py-20 text-gray-400">
              <p className="text-base">No books in this category yet.</p>
              <button
                onClick={() => setActiveCategory("all")}
                className="mt-4 text-sm text-gray-600 underline underline-offset-2"
              >
                Show all
              </button>
            </div>
          )}

          {/* See all CTA */}
          <div className="mt-12 text-center">
            <Link
              to={`/category/${activeCategory}`}
              className="inline-flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 border-b border-gray-300 pb-0.5 hover:border-gray-900 transition-colors"
            >
              See all
              {activeCategory !== "all"
                ? ` ${safeCategories.find((c) => c.id === activeCategory)?.name ?? ""}`
                : " books"}
              <ArrowRight size={14} />
            </Link>
          </div>
        </section>

        {/* ── Editorial Picks Banner ─────────────────────────────────── */}
        <section className="border-t border-gray-200 bg-white animate-fade-up animate-delay-3">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <div className="flex items-center justify-between mb-8">
              <h2 className="font-serif text-2xl font-medium">
                Editorial Picks
              </h2>
              <Link
                to="/category/all"
                className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 transition-colors"
              >
                View all <ArrowRight size={13} />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {editorialPicks.map((pick) => {
                const book = pick.book;
                if (!book) return null;
                return (
                  <Link
                    key={book.id}
                    to={`/book/${book.id}`}
                    className={`group relative overflow-hidden rounded-2xl bg-gradient-to-br ${pick.accent} p-8 flex gap-6 hover:shadow-md transition-shadow`}
                  >
                    <img
                      src={book.image}
                      alt={book.title}
                      className="w-24 h-32 object-cover rounded-sm shadow-md shrink-0 group-hover:shadow-lg transition-shadow"
                    />
                    <div className="flex flex-col justify-center">
                      <span className="text-xs font-semibold tracking-widest uppercase text-gray-400 mb-2">
                        {pick.label}
                      </span>
                      <h3 className="font-serif text-xl font-semibold text-gray-900 leading-tight">
                        {book.title}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">{book.author}</p>
                      <p className="mt-3 text-sm font-semibold text-gray-900">
                        ${book.price?.toFixed(2)}
                      </p>
                    </div>
                    <ArrowRight
                      size={16}
                      className="absolute top-5 right-5 text-gray-400 group-hover:text-gray-700 group-hover:translate-x-0.5 transition-all"
                    />
                  </Link>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── All Categories Strip ───────────────────────────────────── */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 animate-fade-up animate-delay-4">
          <h2 className="font-serif text-2xl font-medium mb-8">
            Browse by Category
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {safeCategories.slice(1).map((cat) => (
              <Link
                key={cat.id}
                to={`/category/${cat.id}`}
                className="group flex flex-col items-center justify-center gap-2 p-5 bg-white rounded-xl border border-gray-100 hover:border-gray-300 hover:shadow-sm transition-all text-center"
              >
                <div className="w-10 h-10 rounded-full bg-gray-50 group-hover:bg-gray-900 flex items-center justify-center transition-colors">
                  <span className="text-gray-500 group-hover:text-white transition-colors text-sm">
                    {(cat.name || cat.label || "").charAt(0)}
                  </span>
                </div>
                <span className="text-xs font-medium text-gray-700 leading-tight">
                  {cat.name}
                </span>
              </Link>
            ))}
          </div>
        </section>

        {/* ── Newsletter ─────────────────────────────────────────────── */}
        <section className="bg-gray-950 text-white animate-fade-up animate-delay-5">
          <div className="max-w-2xl mx-auto px-4 py-20 text-center">
            <p className="text-xs tracking-widest uppercase text-gray-500 mb-4">
              Newsletter
            </p>
            <h2 className="font-serif text-3xl font-medium mb-4">
              New books, every week.
            </h2>
            <p className="text-gray-400 text-sm mb-8 leading-relaxed">
              Stay in the loop on new arrivals, reading recommendations, and
              conversations with the people who make the books we love.
            </p>
            <form
              onSubmit={(e) => e.preventDefault()}
              className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto"
            >
              <input
                type="email"
                placeholder="your@email.com"
                className="flex-1 px-4 py-3 rounded-full bg-gray-900 border border-gray-800 text-white placeholder-gray-600 text-sm outline-none focus:border-gray-600 transition-colors"
              />
              <button type="submit" className="btn-primary shrink-0 py-3 px-6">
                Subscribe
              </button>
            </form>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
