import type { ComparisonActivity as Activity } from "@/lib/decision";
import { CheckCircleIcon, InfoIcon } from "./ShoppingIcons";

export function ComparisonActivity({ activity, excludedCount = 0 }: { activity: Activity[]; excludedCount?: number }) {
  const products = activity.find(step => step.id === "products");
  const sellers = activity.find(step => step.id === "sellers");
  const unavailable = activity.filter(step => step.state === "unavailable");
  const summary = [products && (products.state === "completed" ? `Compared ${products.evidence.length} models` : "Product checks unavailable"), sellers && (sellers.state === "completed" ? `Checked ${sellers.evidence.length} sellers` : "Seller checks unavailable"), !!excludedCount && `Excluded ${excludedCount}`].filter(Boolean).join(" · ") || "Comparison outcome";
  return <section className="cui-activity" aria-label="Comparison activity">
    <details className="cui-activity-details"><summary>{summary}</summary>
    <ul className="cui-checks">
      {products && <li>{products.state === "completed" ? <CheckCircleIcon weight="fill" aria-hidden="true" /> : <InfoIcon aria-hidden="true" />}<div><strong>{products.state === "completed" ? `Compared ${products.evidence.length} models` : "Product checks unavailable"}</strong><p>{products.state === "completed" ? "Used your needs to compare fictional product records." : "Product records could not be compared."}</p></div></li>}
      {sellers && <li>{sellers.state === "completed" ? <CheckCircleIcon weight="fill" aria-hidden="true" /> : <InfoIcon aria-hidden="true" />}<div><strong>{sellers.state === "completed" ? `Checked ${sellers.evidence.length} seller records` : "Seller checks unavailable"}</strong><p>{sellers.state === "completed" ? "Compared supplied return periods and payment terms." : "Seller records could not be checked."}</p></div></li>}
      {!!excludedCount && <li><CheckCircleIcon weight="fill" aria-hidden="true" /><div><strong>{excludedCount} seller{excludedCount === 1 ? "" : "s"} excluded</strong><p>Blocked for the supplied outside-checkout payment terms.</p></div></li>}
    </ul>
      <ol>{activity.map(step => <li key={step.id}><strong>{step.state === "completed" ? "Completed" : "Unavailable"}:</strong> {step.label}<small>{step.evidence.length ? `Records: ${step.evidence.join(", ")}` : "No source record available."}</small></li>)}</ol>
    </details>
    {!!unavailable.length && <p className="cui-activity-unknown"><InfoIcon aria-hidden="true" />Some evidence is unavailable; missing terms remain unknown.</p>}
  </section>;
}
