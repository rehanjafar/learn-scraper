# Security design and limits

## Boundaries

- Only `learn.uwaterloo.ca`, plus the authenticated loopback broker, are permitted.
- Content scripts run only in the top frame of the LEARN home page. They do not inject into password, SSO, or Duo pages.
- No cookies, webRequest, tabs, nativeMessaging, clipboard, or all-sites permissions.
- No page-to-extension messaging, external extension connections, arbitrary URL requests, redirects, POSTs to LEARN, account changes, uploads, or file downloads.
- Exact read-only route patterns are checked by both Python and JavaScript.
- Response fields are explicitly projected; HTML is reduced to text. Response headers and raw HTML pages are never forwarded.
- Only the pairing key is persisted, in a 0600 local file and Safari extension storage. Course responses remain in memory. Logs do not contain pairing keys or course bodies.
- The local server has bounded response sizes, request timeouts, pending-job limits, unpredictable job ids, and replay rejection. Host checks and origin checks prevent website and DNS-rebinding access; bearer authentication also protects requests without an Origin header.
- The extension uses no third-party JavaScript or remote scripts. Native messaging is disabled.

## Residual risks

An extension granted LEARN access is still powerful: changing its code could allow it to read more LEARN information. Safari host permissions cannot encode the finer API restrictions enforced by this code. A compromised LEARN page, Safari vulnerability, compromised extension, malicious local process running as your user, or stolen pairing key may defeat these boundaries. Safari extension storage is not a hardware-backed secret vault. Course text and links are untrusted and may include private information or misleading instructions. Your MCP client may retain returned data according to its own settings. Course data can also include sensitive text written into course materials by others; output projection is not a universal secret detector.

The local Apple Development signature establishes integrity of the built artifact and signer identity, not independent security review or Apple notarization. Do not bypass Gatekeeper or Safari security restrictions to run it. If Safari requires an unsafe developer setting for this build, stop and use a properly provisioned build instead.

## Verification still required

Real Safari activation, one-time website permissions, pairing, and a signed-in LEARN API request must be tested on the user's Mac. Do not treat synthetic tests as proof that live Safari authentication works. Independent human security review is recommended before relying on this for sensitive account access.
