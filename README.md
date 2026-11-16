# Waterloo Safari Reader

A local, read-only MCP server that uses your existing Safari LEARN sign-in. Authentication remains in Safari. The extension never reads or exports cookies, passwords, authorization headers, or login-page contents.

## Status

Version 0.3.0 is enabled and paired on the original Mac. Live MCP sign-in checks succeeded with the LEARN home tab inactive, including reconnection after restarting the local server and a repeated request. The developer signature, exact sandbox entitlements, source-to-build match, automated boundary tests, and dependency advisory scan were verified. Unsigned extensions, remote automation, cross-origin bypasses, and private browsing access remain disabled. No purchase or new enrollment was needed on that Mac. This remains experimental software, not an independently audited or absolutely safe product.

## How it works

Keep a signed-in `https://learn.uwaterloo.ca/d2l/home` tab open in Safari. The extension background process polls the authenticated local broker and dispatches each requested read to an isolated content script in the LEARN home tab. The tab can be inactive. An MCP request becomes a GET to one of an exact API route allowlist. Safari attaches its own authentication internally. The extension returns only selected course-data fields, not response headers or the original response body. Nothing is fetched just because you sign in, and document binaries are never persisted. Explicit planner progress/history and source checkpoints are stored privately when requested.

The broker listens only on `127.0.0.1:18766` while the MCP server is running. It uses a randomly generated 256-bit local key to authenticate each request and response, checks Host and Origin, rejects replayed requests, and keeps requests and responses only in memory. The key itself never crosses the loopback connection. Ordinary websites cannot use it. The key is entered once into Safari extension storage and is never built into the extension or committed to Git.

## Setup on your Mac

Requires Python 3.11+, Xcode, and an Apple Development signing identity.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python setup_local.py
DEVELOPMENT_TEAM=YOUR_TEAM_ID SIGNING_IDENTITY='YOUR_APPLE_DEVELOPMENT_IDENTITY' .venv/bin/python build_safari.py
```

Copy the built app to your Applications folder. The builder verifies the developer signature and exact signed sandbox entitlements. This is a local development build, not a notarized distribution build; no purchase or new enrollment was needed on the original Mac. Use Safari’s normal extension controls only. If Safari refuses to enable it, stop rather than weakening protections. Enable **Waterloo Safari Reader** in Safari Settings → Extensions. Allow it on **learn.uwaterloo.ca**; it also needs access to its local connection at **127.0.0.1**. Do not enable it in private browsing. No broad website access is needed.

Run `.venv/bin/python setup_local.py --show-pairing-key` locally. Enter that key in the extension popup and choose **Pair locally**. Do not send the key to anyone or include it in screenshots, logs, issues, or commits.

Configure your local MCP client with the absolute path to `.venv/bin/python` as the command and the absolute path to `safari_server.py` as its argument. This is a stdio server; it does not expose MCP over the network. Sign in to LEARN normally in Safari and leave the home tab open. Reload the tab once after initial enablement or an extension update so the current content script is loaded.

## Supported data

Courses, calendar due dates, grades, assignments, submission metadata, announcements, content trees, and topic descriptions. LEARN tools are read-only. Course-bound PDF, PPTX, DOCX, HTML and text documents up to 4 MiB are extracted by a protected local worker with no network or private-file access, no document execution, and time/memory/output bounds. Extraction can be partial; inspect pagination and warnings. Quiz completion remains unknown. Other Waterloo services and recordings remain unsupported. One additional tool writes only the private local planner tracker.

## Tests

```sh
.venv/bin/python safari-reader/test_security.py
node safari-reader/test_extension.cjs
.venv/bin/python safari-reader/test_protocol.py
```

These use synthetic data and do not access your university account.

## Disconnect

Disable the extension or choose **Disconnect** in its popup. Stop the MCP client to close the local listener. To revoke a potentially exposed pairing key, stop the server, delete `safari-reader/token`, run setup again, and pair again. Safari sign-out ends account access; queued course data is discarded after completion or timeout.

## Credits

LEARN data formatters are adapted from [ariobarin/waterloo-mcp](https://github.com/ariobarin/waterloo-mcp), used under its MIT license. See LICENSE.

## Minimal live check

After one-time pairing and LEARN website permission, run `.venv/bin/python verify_live.py` and keep a signed-in LEARN home tab open. It checks the identity API and reports success without printing your identity, course data, or pairing key. It closes the local listener when done. Your MCP client starts the normal listener when needed.

For a matching macOS arm64 / Python 3.13 environment, `requirements-macos-py313.lock` pins the exact downloaded wheel hashes. Other platforms must resolve and audit their own environment.

## Morning planner

Read [MORNING_PLANNER.md](MORNING_PLANNER.md) for the full agent workflow. On the paired Mac run `.venv/bin/python morning_context.py --materials 5` through an authorized local tool. `--summary` provides a coverage-only smoke test. This starts and closes the local connection for the request; run one collector at a time. The collector gathers LEARN context, not the complete briefing. Calendar, mail and public research use separate authorized connectors. It does not install a schedule or detect wake time. Say “Morning run” in a chat with these tools and these operating instructions.

`planner_state.py` stores bounded private progress/deduplication history in ignored `planner_state/` (directory 0700, file 0600, atomic updates). Never commit that directory. No calendar events or messages are changed by the collector.
