# Flagsmith Experiments: results banner without the 95% / 5% threshold — evidence

Screenshots of the Flagsmith Cloud experiment results page, taken on 21 Nov 2026, for the issue reported to Flagsmith.

- `screenshots/flagsmith-64pct-banner.png` — 64% chance to win, green "Winner Probability Confirmed"
- `screenshots/flagsmith-control62-banner.png` — variant 38% / control 62%, yellow "Control is the winner"
- `screenshots/flagsmith-98pct-banner.png` — 98%, green banner (the case that matches the docs)

`timestamps/*.ots` are OpenTimestamps proofs made on 21 Nov 2026 for these exact files. To check one: `ots verify timestamps/flagsmith-64pct-banner.png.ots -f screenshots/flagsmith-64pct-banner.png`.

All data in these experiments is synthetic (made-up identities).
