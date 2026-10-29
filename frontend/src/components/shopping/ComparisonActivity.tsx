import type { ComparisonActivity as Activity } from "@/lib/decision";

export function ComparisonActivity({ activity }: { activity: Activity[] }) {
  return <details className="cui-activity">
    <summary>Comparison activity · {activity.filter(step => step.state === "completed").length} completed record checks</summary>
    <ol>{activity.map(step => <li key={step.id}>
      <strong>{step.state === "completed" ? "Completed" : "Unavailable"}:</strong> {step.label}
      <small>{step.evidence.length ? `Records: ${step.evidence.join(", ")}` : "No source record available."}</small>
    </li>)}</ol>
  </details>;
}
