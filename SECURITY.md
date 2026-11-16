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

## Live verification (2026-11-16)

The signed 0.2.1 app was installed and enabled through Safari’s normal controls on the original Mac. LEARN-only website permission and one-time local pairing were completed. A real MCP sign_in_status call verified Safari connection and LEARN sign-in while a different Safari tab was active, with cookies_exported false. Reconnection after a local server restart and a second request also passed. No identity or course data was printed by these checks. No unsigned-extension setting, remote automation, cross-origin bypass, quarantine removal, or Gatekeeper override was used. The local listener closed when the test client exited. These live checks are not an independent security audit.

## Dependency and protocol checks (2026-11-16)

FastMCP was updated from 4.1.1 to the 4.1.2 security patch in a separate environment. All 68 installed dependencies were checked against OSV with no advisory matches at the time of the check. See SECURITY_CHECK_RESULTS.json. Fifteen Python boundary tests, JavaScript policy/proof tests, and a synthetic MCP roundtrip passed. Tests reject fake local-server responses, request tampering, old/replayed proofs, unsafe key files, unauthorized origins, URL escape attempts, and replayed job results. These checks are evidence, not certification or an independent audit.

## Request scheduling

On macOS the extension background page remains active while Safari is running and polls only the authenticated local broker, after confirming an allowed LEARN home tab exists. It dispatches native extension messages to that tab to perform same-origin reads. The page cannot dispatch broker requests or send webpage messages into the extension. No tabs/history permission is requested; the existing exact LEARN host permission supplies only matching tab information. The 0.2.1 scheduler replaces a page timer that was unreliable when Safari became inactive.

## Protected course documents and planner state (0.3.0)
Course files must belong to the requested LEARN course, remain on the exact LEARN origin, and pass size/type checks. Redirects, external service URLs and path escapes are rejected. Binary data is bounded to 4 MiB, carried only over the authenticated loopback bridge and never persisted. PDF/Office/HTML text extraction runs in a separate macOS process sandbox denying network, private files, file writes and unrelated executables. CPU, wall time, resident memory and output are bounded; unavailable enforcement fails closed. XML entities/DTDs and macro-enabled formats are rejected. Parsing software can still contain vulnerabilities; this is defense in depth, not a guarantee or independent security audit.

Document text is untrusted input. The agent workflow must ignore embedded commands and requests for data disclosure or external actions. Partial extraction and unavailable sources must be reported. Private planner history is bounded, owner-only, atomically saved and Git-ignored. No document binary, credential, private progress or real course content belongs in this repository. The collector does not post, apply to jobs, write calendars, create a timer or detect wake time.
