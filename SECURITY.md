# Security design and limits

## Boundaries

- Only `learn.uwaterloo.ca`, plus the authenticated loopback broker, are permitted.
- Content scripts run only in the top frame of the LEARN home page. They do not inject into password, SSO, or Duo pages.
- No cookies, webRequest, tabs, nativeMessaging, clipboard, or all-sites permissions.
- No page-to-extension messaging, external extension connections, arbitrary URL requests, redirects, POSTs to LEARN, account changes, uploads, or file downloads.
- Exact read-only route patterns are checked by both Python and JavaScript.
- Response fields are explicitly projected; HTML is reduced to text. Response headers and raw HTML pages are never forwarded.
- Only the pairing key is persisted, in a 0600 local file and Safari extension storage. Course responses remain in memory. Logs do not contain pairing keys or course bodies.
- The local server has bounded response sizes, request timeouts, pending-job limits, unpredictable job ids, and replay rejection. Host checks and origin checks prevent website and DNS-rebinding access; requests without an extension Origin are rejected. Each request and response has an HMAC-SHA256 proof, signed request nonces expire and cannot be replayed, and the pairing key is never sent over loopback. A fake local service cannot authenticate its responses or obtain the key.
- The extension uses no third-party JavaScript or remote scripts. Native messaging is disabled.

## Residual risks

An extension granted LEARN access is still powerful: changing its code could allow it to read more LEARN information. Safari host permissions cannot encode the finer API restrictions enforced by this code. A Safari vulnerability, compromised extension, malicious local process running as your user, or stolen pairing key may defeat these boundaries. Course pages are untrusted and can influence the data returned; there is no page-to-extension message channel. Safari extension storage is not a hardware-backed secret vault. Course text and links are untrusted and may include private information or misleading instructions. Your MCP client may retain returned data according to its own settings. Course data can also include sensitive text written into course materials by others; output projection is not a universal secret detector.

The local Apple Development signature establishes integrity of the built artifact and signer identity, not independent security review or Apple notarization. Gatekeeper distribution assessment is distinct from local Xcode development testing. Use only Safari’s normal signed-extension controls for this local build. Never enable unsigned extensions, disable cross-origin restrictions, remove quarantine flags, disable Gatekeeper, or enable remote automation to make it work. If Safari refuses the signed build, stop and use a properly provisioned build instead. The signed host app is sandboxed with no network or file-access entitlements; the signed extension is sandboxed with outbound networking only. Neither has a debugging entitlement.

## Verification still required

Real Safari activation, one-time website permissions, pairing, and a signed-in LEARN API request must be tested on the user's Mac. Do not treat synthetic tests as proof that live Safari authentication works. Independent human security review is recommended before relying on this for sensitive account access.

## Dependency and protocol checks (2026-11-16)

FastMCP was updated from 4.1.1 to the 4.1.2 security patch in a separate environment. All 68 installed dependencies were checked against OSV with no advisory matches at the time of the check. See SECURITY_CHECK_RESULTS.json. Fifteen Python boundary tests, JavaScript policy/proof tests, and a synthetic MCP roundtrip passed. Tests reject fake local-server responses, request tampering, old/replayed proofs, unsafe key files, unauthorized origins, URL escape attempts, and replayed job results. These checks are evidence, not certification or an independent audit.

## Request scheduling

On macOS the extension background page remains active while Safari is running and polls only the authenticated local broker, after confirming an allowed LEARN home tab exists. It dispatches native extension messages to that tab to perform same-origin reads. The page cannot dispatch broker requests or send webpage messages into the extension. No tabs/history permission is requested; the existing exact LEARN host permission supplies only matching tab information. The 0.2.1 scheduler replaces a page timer that was unreliable when Safari became inactive.
