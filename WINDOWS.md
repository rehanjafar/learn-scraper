# Windows host

Windows can host the same on-demand planner without a Mac. This implementation uses Chrome or Edge for LEARN authentication and an existing WSL2 Ubuntu installation for the local Python service. No browser cookies, passwords or profile databases are exported. Apple Calendar remains available through the separately authorized iCloud connector; it does not require the Mac Calendar app to be running.

## Setup

Install Python dependencies in a private WSL directory from `requirements.txt` using official PyPI binary wheels. The Linux environment requires bubblewrap (`bwrap`), `prlimit`, Python venv support and user namespaces. Install those from the distribution's official repositories if missing. Run `setup_local.py` once inside WSL; keep its new per-install key separate from any Mac pairing key. Do not copy credentials between browsers or computers.

In Chrome/Edge's extension settings, use Load unpacked to load `chromium-extension`. It is a local development extension, not a store-distributed package. Use normal browser controls only, retain security warnings/protections, and inspect the narrow host permissions: `https://learn.uwaterloo.ca/*` and `http://127.0.0.1:18766/*`. No cookie, history, broad tab, native messaging, debugger or external messaging permission is requested. Sign into LEARN normally and leave a home tab open. Enter the per-install pairing key in the extension popup privately; never send it to a chat or include it in a screenshot.

Invoke the WSL Python executable and `morning_context.py --materials 5` through the authorized Desktop Commander Windows device. This launches and closes the authenticated loopback broker for the collection; only one collector may run at a time. Verify both WSL and Windows forwarding listeners are loopback-only. Do not add a firewall exception, public tunnel or router port forwarding. Manifest V3 alarms recover polling after a service worker restart; allow up to 70 seconds for a cold-start request. The collector is the LEARN portion, not unattended execution of the entire briefing.

## Protected extraction

The Linux parser runs under bubblewrap with a new network/PID/user namespace and dropped capabilities. Only read-only system libraries/binaries, the dedicated Python virtual environment, and the worker script are mounted. Host home directories, Windows drive mounts, pairing keys and planner state are absent. The filesystem for temporary work is ephemeral. `prlimit` imposes hard limits before the parser starts: 768 MiB address space, 5 CPU seconds, zero file output size, and 64 file descriptors. The parent caps input/output and kills the process group at the wall-time limit. Document extraction fails closed if isolation cannot run. Document content remains untrusted and must never direct agent actions.

Test with `safari-reader/test_linux_documents.py`, the existing broker/protocol/planner tests, and `node safari-reader/test_chromium.cjs`. Keep synthetic tests separate from real-account verification. Dependency advisories and distribution security updates should be reviewed separately; a clean scan is not a security guarantee.

## Phone approvals and availability

A phone can handle browser actions through a separately paired remote-screen connection to the Windows computer. Complete initial pairing directly on that computer, keep its account/PIN private, and verify it from the phone. Remote control grants broad access to that computer; protect the account with strong authentication. Remote software cannot guarantee every secure-desktop or pre-boot prompt will be accessible. Never disable Windows protections to work around a prompt.

The Windows host must remain powered, awake and online with Desktop Commander running and a signed-in LEARN home tab available. Closing the Mac no longer matters once the Windows live checks pass and the workflow is pointed at Windows. Power settings, recurring schedules and phone wake-trigger execution are separate setup steps; do not claim they are installed automatically.

## CS135 course site (0.4.1)

The public reader uses exact official CS135 page URLs and refuses redirects, including Waterloo SSO redirects. It extracts the course calendar with dated lecture/assignment events, the lesson index and assessment information. Current-month coverage is checked so an old term is not silently treated as current. Assignment due times follow the explicit course-calendar convention and use America/Toronto. Reading the lesson index does not mean the linked slides were read or that the student completed the lesson.

Protected assignment pages and lecture PDFs use a separate content script restricted to `https://student.cs.uwaterloo.ca/~cs135/*`. Reload the local extension, grant only the additional official CS host, sign into the CS assignment page normally and leave it open. Requests are same-origin GETs with redirects refused; no browser cookie APIs, passwords or login form contents are exported. Only fixed page names and scoped PDF paths are accepted. Course PDF text uses the same protected parser. The collector includes public CS context and, when authorized browser access works, the assignment index and the nearest scheduled lecture's first pages. Pagination and partial coverage remain explicit.
