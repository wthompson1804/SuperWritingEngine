# Before a public launch

Work through this in order. Each item is something the code can't do for you.

## Configuration
- [ ] `MARGIN_PUBLIC_URL` is the final https address. Changing it later breaks fediverse identities and every link already in readers' inboxes.
- [ ] `MARGIN_SMTP_URL` and `MARGIN_MAIL_FROM` are set and a test sign-up's confirmation mail actually arrives (check spam). The `From` domain has SPF and DKIM records at your mail provider, or confirmations will be junked.
- [ ] `MARGIN_TRUST_PROXY=1` only if a reverse proxy sits in front and it *overwrites* or *appends to* `X-Forwarded-For`. If the proxy passes the header through untouched, leave this unset.
- [ ] `MARGIN_AP_INSECURE`, `MARGIN_SHOW_MAIL` and `MARGIN_DEMO_SIGNALS` are not set. (The server refuses the first two in production mode; the third is ignored, but keep the environment clean.)
- [ ] The demo writers (`mara`, `theo`, `june`, `ravi`, password `demo-password`) are deleted or their passwords changed. They are seeded into every new database. Do this before the site is reachable:
      `sqlite3 data/margin.db "DELETE FROM posts WHERE author_id IN (SELECT id FROM authors WHERE handle IN ('mara','theo','june','ravi')); DELETE FROM authors WHERE handle IN ('mara','theo','june','ravi');"`

## Network
- [ ] Only the reverse proxy can reach the app port (`HOST=127.0.0.1`, or a firewall rule).
- [ ] Outbound traffic from the app is restricted to ports 443 (federation) and your SMTP port. Margin checks addresses before connecting, but a DNS answer can change between the check and the connection; an egress firewall closes that gap.
- [ ] The proxy limits request bodies to about 52 MB (imports) and has a read timeout of at least 120 s.
- [ ] Sign-up is open to anyone. Each writer is capped at 500 images / 200 MB and 2,000 imported posts per run, but a wave of throwaway accounts is still a disk-usage risk: watch `data/` growth in the first weeks or put sign-up behind an invite.

## Data
- [ ] `data/` is on persistent storage and is the only writable path. Backups land in `data/backups/` daily; copy them off the machine on a schedule, because a backup on the same disk isn't a backup.
- [ ] Restore has been rehearsed once: stop the app, copy a backup over `data/margin.db`, delete `margin.db-wal` and `margin.db-shm`, start the app.
- [ ] Media files in `data/media/` are included in the off-machine copy (they are not inside the database).

## Operations
- [ ] `GET /healthz` is wired to the load balancer or uptime monitor.
- [ ] `MARGIN_LOG=1` output goes somewhere you will read it, and a spike in 5xx or 429 lines alerts someone.
- [ ] The process manager sends SIGTERM and waits at least 15 s (the systemd unit and Dockerfile already do).
- [ ] One process only. Two instances against one database would double-send mail and fediverse deliveries and split the rate limits.

## Policy (nothing here is enforced by code)
- [ ] A published moderation policy for margin notes, and someone who reads the flag queue on the desk.
- [ ] A privacy page that matches what the code does: no reader cookies, page views kept 90 days, email held only for confirmed follows, exports and deletion on request.
- [ ] A way for a reader to ask for their data to be deleted (reader-key blob, email follows). There is no self-service for this yet; expect to do it by hand in SQLite.
- [ ] A decision on lost reader keys. They cannot be recovered. Say so where keys are issued.

## Known limits at launch
- Tips are simulated. Don't advertise them until a payment provider is wired in.
- Federation has been tested against a local stand-in, not a live Mastodon server. Follow one writer from a real account on day one and watch the delivery log.
- The Brief is built by `npm run digest` on a schedule you set up (cron); the app doesn't run it on its own.
