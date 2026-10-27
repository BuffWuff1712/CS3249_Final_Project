import type { Needs, NeedKey } from "./decision";
import type { Fact } from "./beany";

export type IntentResult = { needs: Needs; ready: boolean; reply: string; options: string[] };

export function interpretPurchase(text: string, current: Needs, questions: number): IntentResult {
  const needs = { ...current };
  const set = (key: NeedKey, value: string, source: Fact["source"] = "confirmed", hard = false) => {
    needs[key] = { value, source, hard };
  };
  const ask = (reply: string, options: string[]): IntentResult => ({ needs, ready: false, reply, options });
  if (/\bUSD\b|US\$/i.test(text)) return ask("This catalogue is priced in SGD. Which currency should I use?", ["Use SGD"]);
  if (/headphone/i.test(text)) set("category", "Headphones", "confirmed", true);
  if (/commut|train/i.test(text)) set("usage", "daily train commute");
  else if (/\bhome\b/i.test(text)) set("usage", "home listening");
  else if (/\bwork\b|office/i.test(text)) set("usage", "work");
  const amount = text.match(/(?:under|below|budget|at most|up to)\s*(?:SGD|S\$|\$)?\s*(\d+(?:\.\d+)?)/i)
    || text.match(/(?:SGD|S\$|\$)\s*(\d+(?:\.\d+)?)/i);
  if (amount && Number(amount[1]) > 0 && Number.isFinite(Number(amount[1]))) set("budget", amount[1], "confirmed", true);
  if (/SGD|S\$/i.test(text)) set("currency", "SGD", "confirmed", true);
  else if (!needs.currency) set("currency", "SGD", "suggested", true);
  if (/comfort.{0,20}(?:first|more|over)|prioriti[sz]e.{0,10}comfort|^(?:comfort|lighter weight)$/i.test(text.trim())) set("priority", "comfort");
  else if (/noise cancellation|blocking.{0,12}noise/i.test(text)) set("priority", "noise cancellation");
  if (!needs.category) return ask("What would you like to compare? This catalogue currently supports headphones.", ["Headphones"]);
  const browse = /show (?:me )?options|browse|not sure|don't know|no budget|any is fine|skip/i.test(text);
  if (!browse && questions < 2) {
    if (!needs.usage) return ask("What will you mainly use the headphones for?", ["Commuting", "Home listening", "Show options"]);
    if (!needs.budget) return ask("What spending limit should I use? You can also browse without a limit.", ["Under SGD300", "Show options"]);
  }
  if (!needs.usage) set("usage", "everyday listening", "suggested");
  if (!needs.priority) set("priority", "noise cancellation", "suggested");
  return { needs, ready: true, reply: "I compared the catalogue using these needs. You can correct any assumption.", options: [] };
}
