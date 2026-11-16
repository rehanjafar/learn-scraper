# Waterloo Safari Reader

A local, read-only MCP server that uses your existing Safari LEARN sign-in. Authentication remains in Safari. The extension never reads or exports cookies, passwords, authorization headers, or login-page contents.

## Status

Experimental security-sensitive software. Automated boundary tests pass, including a simulated MCP roundtrip. The initial local Apple Development build passed signature checks but was rejected by Gatekeeper; it has not been enabled. A properly accepted build and a real Safari permission, pairing, and signed-in LEARN roundtrip must still be verified. This has not received an independent security audit and is not a guarantee of extreme safety.

## How it works

Keep a signed-in `https://learn.uwaterloo.ca/d2l/home` tab open in Safari. The isolated content script polls the extension, which polls a local broker. An MCP request becomes a GET to one of ten exact API route patterns. Safari attaches its own authentication internally. The extension returns only selected course-data fields, not response headers or the original response body. Nothing is fetched just because you sign in, and no course data is stored by this server.

The broker listens only on `127.0.0.1:18766` while the MCP server is running. It requires a randomly generated 256-bit local key, checks Host and Origin, and keeps requests and responses only in memory. Ordinary websites cannot use it. The key is entered once into Safari extension storage and is never built into the extension or committed to Git.

## Setup on your Mac

Requires Python 3.11+, Xcode, and an Apple Development signing identity.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python setup_local.py
DEVELOPMENT_TEAM=YOUR_TEAM_ID SIGNING_IDENTITY='YOUR_APPLE_DEVELOPMENT_IDENTITY' .venv/bin/python build_safari.py
```

Copy the built app to your Applications folder and open it. Enable **Waterloo Safari Reader** in Safari Settings → Extensions. Allow it on **learn.uwaterloo.ca**; it also needs access to its local connection at **127.0.0.1**. Do not enable it in private browsing. No broad website access is needed.

Run `.venv/bin/python setup_local.py --show-pairing-key` locally. Enter that key in the extension popup and choose **Pair locally**. Do not send the key to anyone or include it in screenshots, logs, issues, or commits.

Configure your local MCP client with the absolute path to `.venv/bin/python` as the command and the absolute path to `safari_server.py` as its argument. This is a stdio server; it does not expose MCP over the network. Sign in to LEARN normally in Safari and leave the home tab open.

## Supported data

Courses, calendar due dates, grades, assignments, submission metadata, announcements, content trees, and topic descriptions. All tools are read-only. Quiz completion is reported as unknown. File downloads and other Waterloo services are deliberately unsupported.

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
