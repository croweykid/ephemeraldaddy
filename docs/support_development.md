# Supporting EphemeralDaddy development

## Adopted approach

EphemeralDaddy does not embed a payment form, payment SDK, analytics pixel, or
supporter account system. The application-menu action **Support this app's
ongoing development** first explains the privacy boundary and then, only with
explicit confirmation, asks the operating system to open the project's existing
Patreon page in the user's default browser.

This is deliberately a browser handoff rather than an in-app donation pipeline:

- EphemeralDaddy never receives payment-card or billing details.
- The app does not acquire a network dependency merely to display the menu.
- No donation status is stored in the charts database or application settings.
- Paying does not unlock features, remove limits, or change update access.
- Payment, refund, tax, account, and identity checks remain with the external
  provider under its current terms and privacy policy.
- The creator can present the public `croweykid` project handle, although the
  provider may still require the creator's legal/tax identity privately and may
  disclose information as legally required. “Relative anonymity” must never be
  represented as guaranteed anonymity.

The destination is centralized in
`ephemeraldaddy/gui/support_content.py` and must remain aligned with
`.github/FUNDING.yml`. Changing providers therefore requires an explicit code
and repository-funding change rather than a remotely controlled redirect.

## Intended use of optional support

The dialog states that support may fund release infrastructure including Apple
Developer membership for a signed/notarized macOS build, hosting, and
code-signing expenses. This is an explanation rather than a restricted-purpose
escrow or promise that any particular contribution will purchase a certificate.

## Security and dependency rationale

Using `QDesktopServices.openUrl` avoids adding a payment processor SDK, browser
engine, API token, webhook secret, or financial database to the desktop app.
The fixed HTTPS URL is shipped with the source and visible to packagers. The
confirmation dialog names the provider before opening it and cancellation makes
no network request.

Before changing the destination or offering recurring support publicly, review
the provider's then-current fees, payout availability, tax handling, public
profile behavior, privacy terms, and account-identity requirements. Those facts
are external and can change independently of an EphemeralDaddy release.

## Future options

GitHub Sponsors, Liberapay, Open Collective, Ko-fi, or another provider can be
added later as additional **external links** after their current privacy,
identity, fee, geographic, and open-source-project tradeoffs are reviewed. Do
not embed multiple payment SDKs merely to offer more choices. If fiscal
transparency becomes more important than creator privacy, an Open Collective or
similar public-ledger structure can be evaluated separately.

