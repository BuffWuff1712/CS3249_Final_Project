import type { Category, Needs, NeedKey, Priority } from "./decision";
import type { Fact } from "./beany";
import { categoryOf, priorities, validateNeed } from "./shoppingNeeds";

export type IntentResult = {
  needs: Needs; ready: boolean; reply: string; options: string[];
  seller?: "another" | "cheapest"; newTask: boolean;
};

export function interpretPurchase(text: string, current: Needs, questions: number): IntentResult {
  const headphones = /headphone/i.test(text);
  const shoes = /running shoes|\btrainers\b|\bshoes\b/i.test(text);
  const category: Category | undefined = headphones ? "Headphones" : shoes ? "Running shoes" : undefined;
  const newTask = !!category && category !== categoryOf(current);
  const needs: Needs = newTask ? {} : { ...current };
  const set = (key: NeedKey, value: string, source: Fact["source"] = "confirmed", hard = false) => {
    needs[key] = { value, source, hard };
  };
  const ask = (reply: string, options: string[] = []): IntentResult => ({ needs, ready: false, reply, options, newTask });
  if (headphones && shoes) return ask("Which category should we compare first?", ["Headphones", "Running shoes"]);
  if (/\blaptop|\bbackpack|\bphone\b|\bwatch\b/i.test(text)) return ask("This fictional catalogue supports headphones and running shoes. Which would you like?", ["Headphones", "Running shoes"]);
  if (category) set("category", category, "confirmed", true);
  const activeCategory = categoryOf(needs);
  if (/commut|train journey|\btrain\b/i.test(text)) set("usage", "daily train commute");
  else if (/\bhome\b/i.test(text)) set("usage", "home listening");
  else if (/\bwork\b|office/i.test(text)) set("usage", "work");
  else if (/road|daily.{0,12}run/i.test(text)) set("usage", "daily road runs");
  else if (/race|racing/i.test(text)) set("usage", "road racing");

  const currencyAmounts = [...text.matchAll(/(?:SGD|USD|S\$|US\$|\$)\s*(-?\d+(?:,\d+)*(?:\.\d+)?)/gi)];
  if (new Set(currencyAmounts.map(match => match[1])).size > 1) return ask("You mentioned more than one amount. Which spending limit should I use? Your previous limit is unchanged.", currencyAmounts.map(match => `Under SGD${match[1]}`));
  const amount = currencyAmounts[0] || text.match(/(?:under|below|budget(?:\s+is)?(?:\s+now)?(?:\s+to)?|at most|up to)\s*(-?\d+(?:,\d+)*(?:\.\d+)?)/i);
  if (amount) {
    const value = amount[1].replaceAll(",", "");
    const invalidGrouping = amount[1].includes(",") && !/^\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?$/.test(amount[1]);
    const error = validateNeed("budget", value, needs);
    if (error || invalidGrouping) return ask(error || "Use a valid amount, for example SGD300 or SGD1,000.");
    set("budget", value, "confirmed", true);
  }
  if (/\bUSD|US\$/i.test(text)) set("currency", "USD", "confirmed", true);
  else if (/SGD|S\$/i.test(text)) set("currency", "SGD", "confirmed", true);
  else if (!needs.currency) set("currency", "SGD", "suggested", true);

  const preferred: Priority[] = activeCategory === "Running shoes" ? ["cushioning", "light weight"] : ["noise cancellation", "comfort"];
  const terms: Record<Priority, RegExp> = {
    "noise cancellation": /noise cancellation|noise.?cancelling|blocking.{0,12}noise/i,
    comfort: /comfort|cushioned pads/i,
    cushioning: /cushion/i,
    "light weight": /light.?weight|lighter|\bspeed\b/i,
  };
  const negated = (priority: Priority) => new RegExp(`(?:not|don't|do not|without).{0,12}${priority}|${priority}\\s+(?:is not|does not|doesn't|isn't)`, "i").test(text);
  const explicit = preferred.find(priority => {
    const term = priority === "light weight" ? "(?:light.?weight|lighter|speed)" : priority;
    return !negated(priority) && new RegExp(`${term}\\s+(?:(?:matters?|is)\\s+)?(?:first|more|over)|prioriti[sz]e\\s+${term}|^${term}$`, "i").test(text.trim());
  });
  const mentioned = preferred.filter(priority => terms[priority].test(text) && !negated(priority));
  if (!explicit && mentioned.length > 1 && /equally|both|as important|and|versus|\bvs\b/i.test(text)) {
    delete needs.priority;
    return ask(`These models trade ${preferred[0]} against ${preferred[1]}. Which priority should decide?`, preferred.map(priority => `${priority[0].toUpperCase()}${priority.slice(1)} first`));
  }
  if (explicit || mentioned.length === 1) set("priority", explicit || mentioned[0]);
  if (/cheapest|lowest price|save.{0,8}(?:money|SGD|\$)|price first/i.test(text)) set("sellerPreference", "lowest price");
  else if (/longer returns|return.{0,12}(?:first|more|important)|flexible returns/i.test(text)) set("sellerPreference", "longer returns");
  if (needs.currency?.value === "USD") return ask("This catalogue is priced in SGD. I kept your stated amount and needs; use that amount in SGD or enter a different SGD budget. No conversion is performed.", ["Use SGD"]);
  if (!activeCategory) return ask("What would you like to compare?", ["Headphones", "Running shoes"]);
  const browse = /show (?:me )?options|browse|not sure|don't know|no budget|any is fine|skip/i.test(text);
  if (/no budget|without (?:a )?(?:limit|budget)|remove (?:my |the )?budget/i.test(text)) delete needs.budget;
  if (!browse && (newTask ? 0 : questions) < 2) {
    if (!needs.usage) return ask(activeCategory === "Headphones" ? "What will you mainly use the headphones for?" : "What kind of running are the shoes for?", activeCategory === "Headphones" ? ["Commuting", "Home listening", "Show options"] : ["Daily road runs", "Road racing", "Show options"]);
    if (!needs.budget) return ask("What spending limit should I use? You can also browse without a limit.", [activeCategory === "Headphones" ? "Under SGD300" : "Under SGD200", "Show options"]);
  }
  const seller = /another (?:seller|merchant)|different (?:seller|merchant)|change (?:the )?seller/i.test(text) ? "another" : /cheapest|lowest price/i.test(text) ? "cheapest" : undefined;
  if (!browse && !seller && JSON.stringify(needs) === JSON.stringify(current)) {
    // An explicitly repeated criterion is a meaningful request to explain an unchanged winner.
    if (!explicit && !amount && !category && !/longer returns|use SGD/i.test(text)) return ask(`I could not map that request to this catalogue. You can change the budget, ${priorities[activeCategory].join(" or ")}, or seller.`, ["Show options"]);
  }
  if (!needs.usage) set("usage", activeCategory === "Headphones" ? "everyday listening" : "road running", "suggested");
  if (!needs.priority) set("priority", priorities[activeCategory][0], "suggested");
  return { needs, ready: true, reply: "", options: [], seller, newTask };
}
