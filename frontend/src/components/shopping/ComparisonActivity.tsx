import type { ComparisonActivity as Activity } from "@/lib/decision";
import { CheckCircleIcon, InfoIcon } from "./ShoppingIcons";

export function ComparisonActivity({ activity, excludedCount = 0 }: { activity: Activity[]; excludedCount?: number }) {
  const products = activity.find(step => step.id === "products");
  const sellers = activity.find(step => step.id === "sellers");
  const unavailable = activity.filter(step => step.state === "unavailable");
  return <section className="cui-activity" aria-label="Comparison activity">
    <h2>Completed</h2>
    <ul className="cui-checks">
      {products && <li><CheckCircleIcon weight="fill" aria-hidden="true" /><div><strong>Compared {products.evidence.length} models</strong><p>Used your needs to compare fictional product records.</p></div></li>}
      {sellers && <li><CheckCircleIcon weight="fill" aria-hidden="true" /><div><strong>Checked {sellers.evidence.length} seller records</strong><p>Compared supplied return periods and payment terms.</p></div></li>}
      {!!excludedCount && <li><CheckCircleIcon weight="fill" aria-hidden="true" /><div><strong>{excludedCount} seller{excludedCount === 1 ? "" : "s"} excluded</strong><p>Blocked for the supplied outside-checkout payment terms.</p></div></li>}
    </ul>
    {!!unavailable.length && <p className="cui-activity-unknown"><InfoIcon aria-hidden="true" />Some evidence is unavailable; missing terms remain unknown.</p>}
    <details className="cui-activity-details"><summary>Comparison activity · {activity.filter(step => step.state === "completed").length} completed record checks</summary>
      <ol>{activity.map(step => <li key={step.id}><strong>{step.state === "completed" ? "Completed" : "Unavailable"}:</strong> {step.label}<small>{step.evidence.length ? `Records: ${step.evidence.join(", ")}` : "No source record available."}</small></li>)}</ol>
    </details>
  </section>;
}
