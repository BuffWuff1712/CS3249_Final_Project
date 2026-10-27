"use client";
import { Action } from "@/lib/beany";
function RiskNotice({ action }: { action: Action }) {
  const r = action.risk;
  if (!r || !r.evidence.length) return null;
  return (
    <div
      className={
        r.recommended_decision === "BLOCK" ? "review warning" : "review safe"
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
  );
}
function LiveEvidence({ action }: { action: Action }) {
  const e = action.product.web_evidence;
  if (!e) return null;
  const seller = e.seller;
  const rows: [string, string][] = (
    [
      ["Seller", seller.name],
      ["About the seller", seller.about],
      ["Seller badges", seller.badges.join(", ")],
      ["Seller rating (as shown)", seller.rating],
      ["Business name", seller.business_name],
      ["Registration number", seller.registration_number],
      ["Address", seller.address],
      ["Contact", [seller.email, seller.phone].filter(Boolean).join(" · ")],
      ["Ships from", seller.ships_from],
      ["Return policy", e.return_policy],
      ["Refund promises", e.refund_claims.join(" · ")],
      ["Warranty", e.warranty],
      ["Payment methods listed", e.payment_methods.join(", ")],
      ["Off-site payment instructions", e.off_platform_payment.join(" · ")],
      ["Personal information requested", e.personal_data_requests.join(" · ")],
      ["Urgency claims", e.urgency_claims.join(" · ")],
      ["Text aimed at AI assistants", e.agent_directed_text.join(" · ")],
      ["Shipping", e.shipping],
      ["Page notices", e.notices.join(" · ")],
    ] as [string, string][]
  ).filter(([, v]) => v.trim());
  return (
    <details>
      <summary>Captured seller and policy details ({rows.length})</summary>
      {rows.length ? (
        <dl>
          {rows.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p>No seller or policy details were visible on the captured pages.</p>
      )}
      {(seller.page_url || e.return_policy_url) && (
        <p>
          {seller.page_url && <a className="action-link" href={seller.page_url} target="_blank" rel="noopener noreferrer">Seller page ↗</a>}
          {seller.page_url && e.return_policy_url && " · "}
          {e.return_policy_url && <a className="action-link" href={e.return_policy_url} target="_blank" rel="noopener noreferrer">Return policy ↗</a>}
        </p>
      )}
      <p>
        Details not shown on the page were left blank and were not used in the
        risk assessment.
      </p>
    </details>
  );
}
export function MerchantDetails({ action }: { action: Action }) {
  const m = action.merchant_details,
    r = action.risk;
  if (!m) return null;
  if (action.product.source === "browser_use") return (
    <section className="merchant-details">
      <RiskNotice action={action} />
      <strong>Live listing · merchant information unverified</strong>
      <p>Source: <a className="action-link" href={action.product.source_url} target="_blank" rel="noopener noreferrer">{m.name} ↗</a></p>
      <p>Captured: {action.product.observed_at ? new Date(action.product.observed_at).toLocaleString() : "Unknown"}</p>
      <p>Prices and availability may change. Seller and policy details below were captured from the listing pages and have not been verified. Demo payment options apply only to Beany’s simulated checkout.</p>
      <LiveEvidence action={action} />
      {r && (
        <details>
          <summary>Automated risk review evidence ({r.evidence.length})</summary>
          {r.evidence.length ? (
            <ul>
              {r.evidence.map((e) => (
                <li key={e.rule_id}>{e.evidence}</li>
              ))}
            </ul>
          ) : (
            <p>
              No risk signals were found in the captured details. This does
              not guarantee safety.
            </p>
          )}
        </details>
      )}
    </section>
  );
  return (
    <section className="merchant-details">
      <RiskNotice action={action} />
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
