# BUG ANALYSIS

## Whop checkout authorization / payload audit

The Belmo logs repeatedly returned `403` with `Company API key is not authorized for the checkout_configuration:create scope`.

The API key dashboard showed a Custom key with the five permissions required by Whop's current Create Checkout Configuration API. The IP allow-list shown in the dashboard screenshots was confirmed by the project owner to be empty; the displayed CIDRs were UI placeholders/examples.

The source was audited against Whop's current API reference. The checkout endpoint is `POST /api/v1/checkout_configurations`, authenticated with `Authorization: Bearer <API_KEY>`. The current API supports the existing-plan checkout variant using top-level `plan_id`; the company is derived from the selected plan. The request previously added a separate top-level `company_id`, which does not belong to the existing-plan request variant.

The checkout client has been aligned with the documented existing-plan form and now sends an idempotency key based on the Neural Gold order ID.

Next verification: redeploy the commit containing this change and perform one fresh checkout attempt. If Whop still returns the same scope-specific 403, the remaining target is the API credential itself (credential identity/permission propagation), rather than the IP allow-list or checkout payload.
