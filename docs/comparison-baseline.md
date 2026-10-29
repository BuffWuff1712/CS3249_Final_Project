# Comparison GUI baseline (#21)

Run the frontend and open `/compare`. Participants manually filter category/maximum SGD price, read product and seller records, and choose an offer. Product reviews, seller ratings/counts, returns, payment terms, specifications and fixed variants use exactly the shared `shared/cui/catalogue.json` records used by `/shop`.

The baseline calls `/api/study/catalogue`, whose server-side whitelist excludes scoring, authored advantages/compromises, personalised reasons, risk labels and diagnostic fields. Its client bundle does not import the private scenario module. Raw concerning payment terms remain visible; the baseline does not receive synthesised warnings or a preferred offer. Selection enforces the same stated budget and ordinary-checkout payment restriction; it creates no payment/order. Changing filters clears the previous selection.

This implements the interface condition, not participant assignments or study metrics. Those belong to #22–24. The standalone baseline keeps its choice in memory; assigned-task persistence is added with the study integration. Do not use the older standard/concise explanation profiles as A/B conditions.

Verification: Playwright checks the raw-data response boundary, record counts, manual selection and budget invalidation, alongside existing CUI/decision regressions. Run `npm run test:e2e -- tests/baseline.spec.ts tests/cui.spec.ts tests/decision.spec.ts` from `frontend`.
