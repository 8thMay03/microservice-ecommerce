import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ShoppingBag,
  Heart,
  BookOpen,
  Building2,
  Calendar,
  Hash,
  Share2,
  ChevronRight,
  Check,
  Loader2,
  Star,
  Send,
  Trash2,
  MessageSquare,
  Pencil,
  X,
} from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ProductCard from "../components/ProductCard";
import StarRating from "../components/StarRating";
import { productsApi } from "../api/products";
import { reviewsApi } from "../api/reviews";
import { useCatalog } from "../hooks/useCatalog";
import { normalizeProduct } from "../utils/productUtils";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";

function InteractiveStars({ value, onChange, disabled }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <button
          key={s}
          type="button"
          disabled={disabled}
          onClick={() => onChange(s)}
          onMouseEnter={() => setHover(s)}
          onMouseLeave={() => setHover(0)}
          className="p-0.5 transition-colors disabled:cursor-not-allowed"
        >
          <Star
            size={22}
            className={`transition-colors ${
              s <= (hover || value)
                ? "text-yellow-400 fill-yellow-400"
                : "text-gray-300"
            }`}
          />
        </button>
      ))}
    </div>
  );
}

export default function ProductDetailPage() {
  const { id } = useParams();
  const [book, setBook] = useState(null);
  const [relatedProducts, setrelatedProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { addToCart } = useCart();
  const { user, token, isAuthenticated } = useAuth();
  const { categories } = useCatalog();
  const [added, setAdded] = useState(false);
  const [wishlisted, setWishlisted] = useState(false);

  const [comments, setComments] = useState([]);
  const [ratingSummary, setRatingSummary] = useState(null);
  const [myRating, setMyRating] = useState(0);
  const [ratingLoading, setRatingLoading] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [commentLoading, setCommentLoading] = useState(false);
  const [editingComment, setEditingComment] = useState(null);
  const [editText, setEditText] = useState("");

  const loadReviews = useCallback(async (bookId) => {
    try {
      const [commentsData, summaryData] = await Promise.all([
        reviewsApi.getComments(bookId),
        reviewsApi.getRatingSummary(bookId),
      ]);
      setComments(Array.isArray(commentsData) ? commentsData : commentsData.results ?? []);
      setRatingSummary(summaryData);
    } catch { /* ignore */ }
  }, []);

  const loadMyRating = useCallback(async (bookId, customerId) => {
    try {
      const data = await reviewsApi.getMyRating(bookId, customerId);
      const list = Array.isArray(data) ? data : data.results ?? [];
      if (list.length > 0) setMyRating(list[0].score);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      setComments([]);
      setRatingSummary(null);
      setMyRating(0);
      setCommentText("");
      try {
        const detailRes = await productsApi.get(id);
        if (cancelled) return;
        const b = normalizeProduct(detailRes);
        setBook(b);
        let related = [];
        try {
          const listRes = await productsApi.list({ page_size: 20 });
          if (!cancelled) {
            related = (listRes.results || [])
              .map(normalizeProduct)
              .filter((r) => r && r.id !== b.id && r.category_id === b.category_id)
              .slice(0, 4);
          }
        } catch {
          /* related block is optional; detail must still render */
        }
        if (!cancelled) setrelatedProducts(related);
        loadReviews(id);
        if (user?.id) loadMyRating(id, user.id);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [id, loadReviews, loadMyRating, user?.id]);

  const handleRate = async (score) => {
    if (!isAuthenticated || !user?.id) return;
    setRatingLoading(true);
    try {
      await reviewsApi.postRating(
        { product_id: Number(id), customer_id: user.id, score },
        token
      );
      // Always refresh from server so it reflects the real saved value
      await Promise.all([
        loadMyRating(id, user.id),
        (async () => {
          const summary = await reviewsApi.getRatingSummary(id);
          setRatingSummary(summary);
        })(),
      ]);
    } catch (err) {
      // Ít nhất log lỗi để dễ debug, và không nuốt luôn lỗi
      // eslint-disable-next-line no-console
      console.error("Failed to save rating", err);
    } finally {
      setRatingLoading(false);
    }
  };

  const handleComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim() || !isAuthenticated || !user?.id) return;
    setCommentLoading(true);
    try {
      const customerName = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email || "";
      await reviewsApi.postComment({
        product_id: Number(id),
        customer_id: user.id,
        customer_name: customerName,
        content: commentText.trim(),
      }, token);
      setCommentText("");
      await loadReviews(id);
    } catch { /* ignore */ }
    setCommentLoading(false);
  };

  const handleEditComment = async (commentId) => {
    if (!editText.trim()) return;
    try {
      await reviewsApi.updateComment(commentId, { content: editText.trim() }, token);
      setEditingComment(null);
      setEditText("");
      await loadReviews(id);
    } catch { /* ignore */ }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await reviewsApi.deleteComment(commentId, token);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch { /* ignore */ }
  };

  const categoryLabel = book
    ? categories.find((c) => String(c.id) === String(book.category_id))?.name ?? ""
    : "";

  const handleAddToCart = () => {
    addToCart(book);
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col bg-stone-50">
        <Navbar />
        <div className="flex-1 flex items-center justify-center py-24">
          <Loader2 size={40} className="animate-spin text-gray-400" />
        </div>
        <Footer />
      </div>
    );
  }

  if (error || !book) {
    return (
      <div className="min-h-screen flex flex-col bg-stone-50">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-4">
          <BookOpen size={40} className="text-gray-300" />
          <h1 className="font-serif text-2xl font-medium text-gray-900">Product not found</h1>
          <p className="text-gray-500">This product doesn&apos;t exist or may have been removed.</p>
          <Link to="/category/all" className="btn-primary mt-2">Browse all products</Link>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-stone-50">
      <Navbar />

      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-2 animate-fade-up">
          <nav className="flex items-center gap-1.5 text-xs text-gray-400">
            <Link to="/" className="hover:text-gray-600 transition-colors">Home</Link>
            <ChevronRight size={12} />
            <Link to={`/category/${book.category_id}`} className="hover:text-gray-600 transition-colors">
              {categoryLabel}
            </Link>
            <ChevronRight size={12} />
            <span className="text-gray-600 truncate max-w-[200px]">{book.title}</span>
          </nav>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-up animate-delay-1">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16">
            <div className="lg:col-span-5 xl:col-span-4">
              <div className="sticky top-24">
                <div className="relative bg-white rounded-2xl overflow-hidden shadow-sm">
                  {book.isNew && (
                    <span className="absolute top-4 left-4 z-10 bg-[#e8392a] text-white text-xs font-semibold px-3 py-1.5 rounded-full">
                      New
                    </span>
                  )}
                  <img src={book.image} alt={book.title} className="w-full aspect-[4/5] object-cover" />
                </div>
                <div className="flex gap-2 mt-3">
                  {[book.image, book.image, book.image].map((src, i) => (
                    <button
                      key={i}
                      className={`w-16 h-20 rounded-lg overflow-hidden border-2 transition-colors ${
                        i === 0 ? "border-gray-900" : "border-transparent hover:border-gray-300"
                      }`}
                    >
                      <img src={src} alt="" className="w-full h-full object-cover opacity-80" />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="lg:col-span-7 xl:col-span-8 space-y-6">
              <Link
                to={`/category/${book.category_id}`}
                className="inline-block text-xs font-semibold tracking-widest uppercase text-gray-400 hover:text-gray-700 transition-colors"
              >
                {categoryLabel}
              </Link>

              <div>
                <h1 className="font-serif text-3xl sm:text-4xl font-medium text-gray-900 leading-tight">
                  {book.title}
                </h1>
                <p className="text-gray-600 mt-2 text-lg">by {book.author}</p>
              </div>

              {ratingSummary && ratingSummary.total_ratings > 0 && (
                <StarRating rating={ratingSummary.average_score} reviewCount={ratingSummary.total_ratings} size="md" />
              )}

              <div className="flex items-baseline gap-3 pt-1">
                <span className="font-serif text-4xl font-semibold text-gray-900">
                  ${book.price?.toFixed(2)}
                </span>
                <span className="text-sm text-gray-400">Free shipping over $50</span>
              </div>

              <hr className="border-gray-100" />

              <div className="flex gap-3">
                <button
                  onClick={handleAddToCart}
                  className={`flex-1 flex items-center justify-center gap-2.5 py-3.5 rounded-full font-medium text-sm transition-all duration-200 ${
                    added ? "bg-green-600 text-white" : "bg-gray-900 text-white hover:bg-gray-700"
                  }`}
                >
                  {added ? (
                    <><Check size={16} /> Added to cart!</>
                  ) : (
                    <><ShoppingBag size={16} /> Add to Cart — ${book.price?.toFixed(2)}</>
                  )}
                </button>

                <button
                  onClick={() => setWishlisted((v) => !v)}
                  className={`w-12 h-12 rounded-full border flex items-center justify-center transition-all duration-150 shrink-0 ${
                    wishlisted ? "bg-red-50 border-red-200 text-red-500" : "border-gray-200 text-gray-500 hover:border-gray-400 hover:text-gray-700"
                  }`}
                  aria-label={wishlisted ? "Remove from wishlist" : "Add to wishlist"}
                >
                  <Heart size={17} fill={wishlisted ? "currentColor" : "none"} />
                </button>

                <button
                  className="w-12 h-12 rounded-full border border-gray-200 flex items-center justify-center text-gray-500 hover:border-gray-400 hover:text-gray-700 transition-colors shrink-0"
                  aria-label="Share"
                >
                  <Share2 size={17} />
                </button>
              </div>

              <hr className="border-gray-100" />

              <div>
                <h2 className="font-serif text-lg font-semibold mb-3 text-gray-900">About this product</h2>
                <p className="text-gray-600 leading-relaxed text-sm">{book.description || "No description available."}</p>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <h3 className="text-sm font-semibold text-gray-900 mb-4">Product Details</h3>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
                  {[
                    { icon: BookOpen, label: "Pages", value: book.pages },
                    { icon: Building2, label: "Language", value: book.language },
                    { icon: Calendar, label: "Published", value: book.published_date },
                    { icon: Hash, label: "ISBN", value: book.isbn },
                  ].filter(({ value }) => value != null).map(({ icon: Icon, label, value }) => (
                    <div key={label} className="flex items-start gap-2.5">
                      <Icon size={14} className="text-gray-400 mt-0.5 shrink-0" />
                      <div>
                        <dt className="text-xs text-gray-400">{label}</dt>
                        <dd className="text-sm font-medium text-gray-700 mt-0.5">{value}</dd>
                      </div>
                    </div>
                  ))}
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* ── Reviews & Ratings ────────────────────────────────────── */}
        <section className="border-t border-gray-200 bg-white animate-fade-up animate-delay-3">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
            <div className="max-w-3xl">
              {/* Header */}
              <div className="flex items-center justify-between mb-8">
                <h2 className="font-serif text-2xl font-medium">Reviews & Ratings</h2>
                {ratingSummary && ratingSummary.total_ratings > 0 && (
                  <div className="flex flex-col items-end gap-1">
                    <div className="flex items-center gap-2">
                      <span className="font-serif text-3xl font-semibold text-gray-900">
                        {ratingSummary.average_score.toFixed(1)}
                      </span>
                      <div>
                        <StarRating rating={ratingSummary.average_score} showCount={false} size="sm" />
                        <p className="text-xs text-gray-500 mt-0.5">
                          {ratingSummary.total_ratings} rating{ratingSummary.total_ratings !== 1 ? "s" : ""}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Rate this product */}
              <div className="bg-gray-50 rounded-2xl p-5 mb-8">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Rate this product</h3>
                {isAuthenticated ? (
                  <div className="flex items-center gap-4">
                    <InteractiveStars value={myRating} onChange={handleRate} disabled={ratingLoading} />
                    {myRating > 0 && (
                      <span className="text-sm text-gray-500">
                        Your rating: <span className="font-medium text-gray-700">{myRating}/5</span>
                        <span className="ml-1.5 text-xs text-gray-400">(click to change)</span>
                      </span>
                    )}
                    {ratingLoading && <Loader2 size={16} className="animate-spin text-gray-400" />}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">
                    <Link to="/login" className="text-gray-900 font-medium hover:underline">Sign in</Link> to Rate this product.
                  </p>
                )}
              </div>

              {/* Write a comment */}
              <div className="mb-8">
                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <MessageSquare size={15} />
                  Leave a Comment
                </h3>
                {isAuthenticated ? (
                  <form onSubmit={handleComment} className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-900 text-white text-xs font-semibold flex items-center justify-center shrink-0 mt-0.5">
                      {user?.first_name?.charAt(0)?.toUpperCase() || "U"}
                    </div>
                    <div className="flex-1 relative">
                      <textarea
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder="Share your thoughts About this product…"
                        rows={3}
                        className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-200 text-sm bg-white outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-200 transition-colors resize-none"
                      />
                      <button
                        type="submit"
                        disabled={!commentText.trim() || commentLoading}
                        className="absolute right-3 bottom-3 p-1.5 rounded-lg bg-gray-900 text-white hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        {commentLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                      </button>
                    </div>
                  </form>
                ) : (
                  <p className="text-sm text-gray-500">
                    <Link to="/login" className="text-gray-900 font-medium hover:underline">Sign in</Link> to leave a comment.
                  </p>
                )}
              </div>

              {/* Comment list */}
              {comments.length > 0 ? (
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
                    {comments.length} comment{comments.length !== 1 ? "s" : ""}
                  </p>
                  {comments.map((c) => {
                    const isOwner = user?.id && c.customer_id === user.id;
                    const isEditing = editingComment === c.id;
                    const displayName = isOwner
                      ? [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email
                      : c.customer_name || `User #${c.customer_id}`;
                    const initial = displayName.charAt(0).toUpperCase();
                    const date = new Date(c.created_at).toLocaleDateString("en-US", {
                      year: "numeric", month: "short", day: "numeric",
                    });
                    return (
                      <div key={c.id} className="border-b border-gray-100 pb-5 mb-5 last:border-0 last:mb-0">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-600 text-xs font-semibold flex items-center justify-center">
                              {initial}
                            </div>
                            <div>
                              <span className="text-sm font-medium text-gray-900">{displayName}</span>
                              {isOwner && (
                                <span className="ml-2 text-[10px] font-medium bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">You</span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400">{date}</span>
                            {isOwner && !isEditing && (
                              <>
                                <button
                                  onClick={() => { setEditingComment(c.id); setEditText(c.content); }}
                                  className="p-1 text-gray-400 hover:text-blue-500 transition-colors"
                                  title="Edit comment"
                                >
                                  <Pencil size={13} />
                                </button>
                                <button
                                  onClick={() => handleDeleteComment(c.id)}
                                  className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                                  title="Delete comment"
                                >
                                  <Trash2 size={13} />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                        {isEditing ? (
                          <div className="ml-11 flex gap-2">
                            <textarea
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              rows={2}
                              className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-200 resize-none"
                            />
                            <div className="flex flex-col gap-1">
                              <button
                                onClick={() => handleEditComment(c.id)}
                                disabled={!editText.trim()}
                                className="p-1.5 rounded-lg bg-gray-900 text-white hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                                title="Save"
                              >
                                <Check size={14} />
                              </button>
                              <button
                                onClick={() => { setEditingComment(null); setEditText(""); }}
                                className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-100 transition-colors"
                                title="Cancel"
                              >
                                <X size={14} />
                              </button>
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm text-gray-600 leading-relaxed ml-11">{c.content}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  <MessageSquare size={28} className="mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No comments yet. Be the first to share your thoughts!</p>
                </div>
              )}
            </div>
          </div>
        </section>

        {relatedProducts.length > 0 && (
          <section className="border-t border-gray-200 animate-fade-up animate-delay-4">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
              <div className="flex items-center justify-between mb-8">
                <h2 className="font-serif text-2xl font-medium">You might also like</h2>
                <Link
                  to={`/category/${book.category_id}`}
                  className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 transition-colors"
                >
                  More in {categoryLabel}
                  <ChevronRight size={14} />
                </Link>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-5 gap-y-10">
                {relatedProducts.map((b) => (
                  <ProductCard key={b.id} product={b} showRating={!!b.rating} />
                ))}
              </div>
            </div>
          </section>
        )}
      </main>

      <Footer />
    </div>
  );
}
