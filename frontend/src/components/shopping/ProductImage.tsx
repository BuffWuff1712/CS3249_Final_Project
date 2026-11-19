"use client";
import { useState } from "react";
import type { Product } from "@/lib/beany";

export function ProductImage({ product }: { product: Product }) {
  const [failed, setFailed] = useState("");
  const url = product.image_url || "";
  const usable = /^https:\/\//i.test(url) && failed !== url;
  return <div className="cui-product-image" aria-label="Product image">
    {usable ? <img src={url} alt={product.image_alt || product.name} referrerPolicy="no-referrer" decoding="async" onError={() => setFailed(url)} />
      : <p className="cui-source">Product image unavailable</p>}
  </div>;
}
