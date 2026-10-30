import type { ComparisonActivity as Activity } from "@/lib/decision";
import type { LiveShopActivity } from "@/lib/shopBackend";
import { CheckCircleIcon, InfoIcon } from "./ShoppingIcons";

export function ActivitySteps({ activity, stopped = false }: { activity: LiveShopActivity[]; stopped?: boolean }) {
  return <ol className="cui-live-steps">{activity.map(step => {
    const running = step.state === "running" && !stopped;
    return <li key={step.id} className={running ? "is-running" : step.state === "unavailable" || step.state === "running" ? "is-unavailable" : "is-complete"}>
      {running ? <span className="cui-step-spinner" aria-hidden="true" /> : step.state === "completed" ? <CheckCircleIcon weight="fill" aria-hidden="true" /> : <InfoIcon aria-hidden="true" />}
      <div><span className="sr-only">{running ? "In progress: " : step.state === "completed" ? "Done: " : "Not completed: "}</span><strong>{step.label}</strong>
        {!!step.evidence.length && <small>{step.evidence.join(" · ")}</small>}
      </div>
    </li>;
  })}</ol>;
}

export function ComparisonActivity({ activity, excludedCount = 0 }: { activity: Activity[]; excludedCount?: number }) {
  const summary = activity.filter(step => ["search", "inspection"].includes(step.id)).map(step => step.label).join(" · ") || "What Beany checked";
  return <section className="cui-activity" aria-label="Comparison activity"><details className="cui-activity-details"><summary>{summary}{excludedCount ? ` · ${excludedCount} excluded` : ""}</summary><ActivitySteps activity={activity} /></details></section>;
}
