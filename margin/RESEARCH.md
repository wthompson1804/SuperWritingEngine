# Research notes (September 2026)

Desk research done to revise Margin, not user research. **Method limits:** a network proxy blocked direct page fetches for most sites (Reuters Institute, Chartbeat, Substack, Nieman Lab). Most figures below come from search-result summaries of the named sources. Where a claim came from one secondary source, it's marked *(unverified)*. The Substack export format is the exception: it was read directly from Ghost's open-source migrator code.

## Readers

| Finding | Source |
|---|---|
| ~16% of Americans read for pleasure on a given day (2023), down from 28% in 2004: a ~40% drop | Bone, Fancourt et al., *iScience* 2025, 236k ATUS respondents · https://pmc.ncbi.nlm.nih.gov/articles/PMC12496190/ |
| 30% of US adults get news from newsletters at least sometimes; skews college-educated; **62% don't read most of what they receive**; 71% take fewer than 5 | Pew, Feb 2026 · https://www.pewresearch.org/journalism/2026/02/19/email-newsletters-as-a-source-of-news/ |
| News avoidance: 29% (2017) → 39% (2024) → 42% (2026). Top reasons: mood, being worn out by the volume, war, politics | Reuters Institute DNR 2024–2026 · https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2026/dnr-executive-summary |
| 17–18% pay for online news (flat); most payers hold a single subscription | Reuters DNR 2025/2026 · https://www.mdif.org/news/reuters-digital-news-report-2025-what-it-means-for-independent-media/ |
| Pop-ups are among the most-hated patterns. Premature email-capture modals trade frustration for short-term metrics | Nielsen Norman Group · https://www.nngroup.com/articles/popups/ |
| Google demotes mobile pages with interstitials that block content on arrival (since 2017) | https://searchengineland.com/guide/interstitials-and-dialogs |
| Substack's app and network drive a large share of its growth: 50% of new subscriptions and 25% of new paid in Feb 2024; iOS app >30% of paid (Mar 2025) | Substack · https://x.com/Substack/status/1760696631156953443 ; https://www.tubefilter.com/2025/03/12/substack-five-million-paid-subscribers-journalist-reporter-newsletter/ |
| "Dark social" (messaging, copy-paste) is 77–84% of sharing, **but the data is 2014–2019** | RadiumOne et al. · https://www.media-marketing.com/en/news/84-of-social-sharing-happens-via-dark-social-platforms/ |
| Text fragments (`#:~:text=`) work in Chrome 80+, Edge, Safari 16.1+, Firefox 131+ | https://caniuse.com/url-scroll-to-text-fragment |
| **No quantitative evidence** that quote/highlight sharing drives readership | (searched; nothing found) |
| Pocket shut down July 8, 2025. Users moved to Readwise Reader, Instapaper, Matter and Raindrop, and valued simplicity, "intentionality", and no algorithmic drift | https://techcrunch.com/2025/05/22/mozilla-is-shutting-down-read-it-later-app-pocket |
| Readwise's core loop is spaced resurfacing of highlights | https://docs.readwise.io/readwise/docs/faqs/reviewing-highlights |
| Average engaged time is ~28–30s (Chartbeat 2025). Engagement rises with length up to ~2,000 words, then becomes erratic | https://chartbeat.com/resources/articles/global-audience-insights-from-the-second-quarter-of-2025/ |
| Medium read ratios of 40–70% are common and fall with length *(unverified: writer blogs)* | https://medium.com/swlh/what-is-a-good-read-ratio-on-medium-ee63d2f6fd9e |
| **No 2023–26 quantitative study** of demand for finite feeds | (searched; nothing found) |

## Writers and competitors

| Finding | Source |
|---|---|
| Substack: >5M paid subscriptions (Mar 2025), ~50M total; ~$45M revenue on ~$450M writer gross (10% fee) | https://sacra.com/c/substack/ |
| Substack's in-network share fell from ~50% to ~40% of new subscriptions, and ~15% of paid *(unverified relay)* | https://escapethecubicle.substack.com/p/substack-just-revealed-40-of-new |
| Writer complaints: moderation (a July 2025 push alert promoted a Nazi newsletter), the 10% fee at scale, the "visibility labor" of Notes, being forced into the app | https://digiday.com/media/creators-are-ditching-substack-over-ideological-shift-in-2025/ ; https://www.niemanlab.org/2025/10/top-substack-writers-depart-for-patreon/ |
| Ghost 6 (Aug 2025): every site is an ActivityPub profile, followable from Mastodon and Threads; 0% fee | https://ghost.org/changelog/6/ |
| Beehiiv: Boosts drive ~10–20% of net-new growth at ~$1.63 per subscriber; median free-to-paid conversion is **0.62%** | https://www.beehiiv.com/features/boosts ; https://www.beehiiv.com/blog/the-state-of-paid-newsletters-2026 |
| **Substack export format** (verified in code): `posts.csv` with `post_id,post_date,is_published,email_sent_at,type,audience,title,subtitle,podcast_url`; `posts/<post_id>.html`; `email_list.*.csv` with `email,active_subscription,expiry,email_disabled,prefer_digests,created_at` | https://github.com/TryGhost/migrate/tree/main/packages/mg-substack |
| Webrings are "a slow burn, not a spike." There's **no quantitative evidence** that webrings, blogrolls, or Bear Blog's Discover drive meaningful traffic, and Bear's Discover got gamed | https://webringstudio.com/will-a-webring-boost-my-traffic-in-2025-maybe-but-not-like-you-think/ ; https://herman.bearblog.dev/discovery-feed-changes/ |
| Open rates are broken: Apple Mail had ~49% of opens and inflates them. Medium measures reading time instead | https://www.beehiiv.com/blog/apple-mpp-open-rate ; https://help.medium.com/hc/en-us/articles/360036691193 |
| Stripe's 2.9% + 30¢ takes 8.8% of a $5 tip and ~18% of a $2 tip. No public tip conversion data | https://checkoutpage.com/blog/stripe-processing-fees |

## Usability, by persona (round 2)

| Finding | Persona | Source |
|---|---|---|
| Presbyopia affects >80% of Americans by 45 and ~100% from ~52. ~128M US presbyopes | R2 | AOA · https://www.aoa.org/news/clinical-eye-care/diseases-and-conditions/for-128-million-us-presbyopes-doctors-of-optometry-can-provide-treatment-options |
| 16px is the floor for body text; larger helps older users (18px for 50+ *(unverified: secondary)*) | R2 | NN/g via https://www.greadme.com/blog/seo/best-font-sizes-for-readability-complete-guide |
| ~55 characters per line read most easily on screen (Dyson & Kipping 1998; Dyson & Haselgrove 2001) | R2 | https://www.sciencedirect.com/science/article/abs/pii/S1071581901904586 |
| 30–40%+ of iOS users change the default text size *(unverified: developer blogs)* | R2 | https://lickability.com/blog/dynamic-type-and-in-app-font-scaling/ |
| iOS Safari's selection menu can't be suppressed, and custom tooltips "fight" it. Android's floating toolbar sits over content | R2, R3 | https://discuss.prosemirror.net/t/how-to-disable-the-mobile-safari-selection-menu/2581 |
| Readwise Reader on mobile: double-tap a paragraph to highlight it | R2 | https://docs.readwise.io/reader/docs/faqs/highlights-tags-notes |
| Double opt-in: Mailchimp saw ~61% never confirm and switched to single opt-in (2017). Beehiiv sends a "Smart Nudge" reminder | R1 → follower | https://mjtsai.com/blog/2017/11/21/mailchimp-switches-to-single-opt-in/ ; https://www.beehiiv.com/support/article/13081072798743-how-to-enable-double-opt-in-and-smart-nudge |
| Dark text on light reads and proofreads better, for young and old readers, especially at small sizes. NN/g: follow the OS setting, and offer a switch | R2 | https://pubmed.ncbi.nlm.nih.gov/25135324/ ; https://www.nngroup.com/articles/dark-mode/ |
| Monospace prose reads more slowly; fine for short labels | all | https://practicaltypography.com/monospaced-fonts.html |
| Substack's 2023 "Follow" (no email) confused readers, and writers had to explain that "follow ≠ newsletter" | R1, R2, W3 | https://techcrunch.com/2023/08/15/substack-expands-further-into-social-networking-with-a-new-follow-button/ |
| Writers complain about drafts not syncing or getting lost, and about Substack's lack of tables and footnotes. No ranked survey found | W1–W3 | https://postolithic.substack.com/p/substack-mobile-vs-desktop-what-gives |
| No peer-reviewed evidence that reading progress bars raise completion | R1 | (searched; nothing found) |

## What this changed

See [DESIGN.md §0](DESIGN.md#0-what-v3-changed-and-why).
