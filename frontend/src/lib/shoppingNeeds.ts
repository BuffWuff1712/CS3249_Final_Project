import type { Category, NeedKey, Needs, Priority } from "./decision";

export const priorities: Record<Category, Priority[]> = {
  Headphones: ["noise cancellation", "comfort"],
  "Running shoes": ["cushioning", "light weight"],
};
export function categoryOf(needs: Needs): Category | undefined {
  const value = needs.category?.value;
  return value === "Headphones" || value === "Running shoes" ? value : undefined;
}
export function validateNeed(key: NeedKey, value: string, needs: Needs): string | null {
  if (!value.trim() || value.length > 120) return "Enter a preference between 1 and 120 characters.";
  if (key === "budget" && (!/^\d+(?:\.\d{1,2})?$/.test(value) || Number(value) <= 0 || Number(value) > 1000000)) return "Enter a positive budget up to SGD1000000 with at most two decimal places.";
  if (key === "currency" && value !== "SGD") return "This fictional catalogue uses SGD; no currency conversion is available.";
  if (key === "category" && !["Headphones", "Running shoes"].includes(value)) return "Choose headphones or running shoes.";
  const category = categoryOf(needs);
  if (key === "priority" && (!category || !priorities[category].includes(value as Priority))) return `Choose ${category === "Headphones" ? "comfort or noise cancellation" : category ? priorities[category].join(" or ") : "a category first"} for this comparison.`;
  if (key === "sellerPreference" && !["longer returns", "lowest price"].includes(value)) return "Choose longer returns or lowest price.";
  return null;
}
