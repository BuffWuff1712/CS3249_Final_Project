import type { Product } from "./beany";

// Presentation only: never rewrite persisted proposals or their fingerprints.
export function productTitle(product: Pick<Product, "name" | "source">): string {
  let name = product.name.replace(/\s+/g, " ").trim();
  for (let index = name.indexOf(" · "); product.source === "shopify_catalog" && index !== -1; index = name.indexOf(" · ", index + 3)) {
    const left = name.slice(0, index), right = name.slice(index + 3);
    if (left.toLowerCase() === right.toLowerCase()) { name = left; break; }
  }
  // Retailers often append colour, specifications and marketing as pipe-separated
  // segments. Keep the identifying first segment; full source text stays available.
  const core = name.split(/\s*\|\s*/)[0].trim();
  if (core.length >= 12) name = core;
  if (name.length <= 90) return name;
  const prefix = name.slice(0, 87);
  const boundary = prefix.lastIndexOf(" ");
  return prefix.slice(0, boundary >= 60 ? boundary : 87).trimEnd() + "…";
}
