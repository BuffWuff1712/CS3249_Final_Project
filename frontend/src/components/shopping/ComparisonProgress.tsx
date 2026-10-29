import { presentationStatus, type PresentationState } from "@/lib/shoppingPresentation";
import { CheckCircleIcon, InfoIcon } from "./ShoppingIcons";
import { DotsThreeIcon } from "@phosphor-icons/react/dist/csr/DotsThree";

export function ComparisonProgress({ presentation }: { presentation: PresentationState }) {
  const pending = presentation.pending;
  if (!pending) return null;
  const activity = presentation.current.result?.activity || [];
  const excluded = presentation.current.result?.decision?.concerns.filter(concern => concern.blocked).length || 0;
  const steps = pending.kind === "comparison" ? activity.filter(step => pending.step >= 2 && step.id === "products" || pending.step >= 3 && (step.id === "sellers" || step.id === "eligibility")) : [];
  return <div className="cui-turn cui-turn--assistant cui-progress" aria-label={pending.kind === "comparison" ? "Preparing comparison" : "Preparing reply"}>
    <span className="cui-avatar" aria-hidden="true">b.</span>
    <div className="cui-turn-body"><p className="cui-progress-label"><DotsThreeIcon className="cui-typing" weight="bold" aria-hidden="true" />{presentationStatus(presentation)}</p>
      {(!!steps.length || pending.kind === "comparison" && pending.step >= 3 && !!excluded) && <ul className="cui-progress-steps">{steps.map(step => <li key={step.id}>{step.state === "completed" ? <CheckCircleIcon aria-hidden="true" weight="fill" /> : <InfoIcon aria-hidden="true" />}<span>{step.label}</span></li>)}{pending.kind === "comparison" && pending.step >= 3 && !!excluded && <li><CheckCircleIcon aria-hidden="true" weight="fill" /><span>Excluded {excluded} blocked seller offer{excluded === 1 ? "" : "s"}.</span></li>}</ul>}
      {pending.kind === "comparison" && <small>Presenting a local comparison. No websites are visited.</small>}
    </div>
  </div>;
}
