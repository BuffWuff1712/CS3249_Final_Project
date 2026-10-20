"use client";
import { Action } from "@/lib/beany";
export function MerchantDetails({ action }: { action: Action }) {
  const m = action.merchant_details,
    r = action.risk;
  if (!m) return null;
  return (
    <section className="merchant-details">
      {r && r.evidence.length > 0 && (
        <div
          className={
            r.recommended_decision === "BLOCK"
              ? "review warning"
              : "review safe"
          }
        >
          <strong>
            Merchant assessment · {r.level.toLowerCase()} predicted risk
          </strong>
          <p>{r.explanation}</p>
          <p>
            You can inspect the evidence, reject this offer, find another
            merchant, or cancel. Continuing is available only when policy
            permits.
          </p>
        </div>
      )}
      <details>
        <summary>Review merchant details: {m.name}</summary>
        <p>
          <strong>Simulated website:</strong> {m.website} · never visited
        </p>
        <p>{m.description}</p>
        <dl>
          <dt>Business contact</dt>
          <dd>{m.contact || "Not supplied"}</dd>
          <dt>Verification indicator</dt>
          <dd>
            {m.verified_business
              ? "Present in the fictional record"
              : "Not present"}
          </dd>
          <dt>Reviews (simulated)</dt>
          <dd>
            {m.review_count} reviews · {m.review_rating ?? "No rating"}
          </dd>
          <dt>Return policy</dt>
          <dd>{m.return_policy}</dd>
          <dt>Payment channels</dt>
          <dd>{m.payment_methods.join(", ")}</dd>
          <dt>Requested information</dt>
          <dd>{m.requested_information.join(", ") || "None"}</dd>
        </dl>
        {r && (
          <details>
            <summary>Observable evidence ({r.evidence.length})</summary>
            {r.evidence.length ? (
              <ul>
                {r.evidence.map((e) => (
                  <li key={e.rule_id}>{e.evidence}</li>
                ))}
              </ul>
            ) : (
              <p>
                No configured signals detected. This does not guarantee safety.
              </p>
            )}
          </details>
        )}
      </details>
    </section>
  );
}
