import type { MerchantConcern } from "@/lib/decision";

export function MerchantCaution({ concern, label = "Merchant caution" }: { concern: MerchantConcern; label?: string }) {
  return <section className="cui-caution" aria-label={label}>
    <h3>{concern.blocked ? "Choose a different payment offer" : "A term is unknown"}</h3>
    <p>{concern.observation} {concern.consequence}</p>
    <p><strong>Recommended next step:</strong> {concern.nextStep}</p>
    <p className="cui-source">Source: fictional seller record {concern.offerId}. This is a simulated assessment of visible terms.</p>
  </section>;
}
