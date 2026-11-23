# Evaluation results

- Run: 2026-11-23 15:43 UTC
- Mode: **rules only**
- Data: `data/synthetic_messages.jsonl` — 60 synthetic messages (30 scam, 14 legit, 8 code-delivery, 8 ambiguous; 12 ask for card/OTP)

> Caveat: the messages were written by the same team that wrote the rules, so these numbers are
> in-sample and likely optimistic. They are not a measure of real-world accuracy.

| Metric | Result |
|---|---|
| False alarms: benign (legit + code-delivery) rated high_suspicion | 1/22 (5%) |
| Benign rated unclear | 0/22 (0%) |
| Misses: scam rated no_visible_indicators | 0/30 (0%) |
| Scam rated high_suspicion | 30/30 (100%) |
| Scam rated unclear | 0/30 (0%) |
| Card/OTP requests rated high_suspicion | 12/12 (100%) |
| Code-delivery messages rated high_suspicion | 1/8 (12%) |
| Unclear rate (all messages) | 3/60 (5%) |
| Ambiguous messages (no single right answer) | {'no_visible_indicators': 5, 'unclear': 3} |

## Per message

| id | lang | category | card/OTP | status | reasons |
|---|---|---|---|---|---|
| s01 | ar | scam |  | high_suspicion | link_unknown_for_claim, payment_request, urgency |
| s02 | ar | scam | yes | high_suspicion | asks_card, link_mismatch_claimed, brand_in_host |
| s03 | en | scam |  | high_suspicion | link_mismatch_claimed, brand_in_host, payment_request |
| s04 | en | scam | yes | high_suspicion | asks_card, link_mismatch_claimed, brand_in_host |
| s05 | ar | scam | yes | high_suspicion | asks_card, receive_money_link, brand_in_host |
| s06 | en | scam | yes | high_suspicion | asks_card, receive_money_link, link_mismatch_claimed |
| s07 | ar | scam | yes | high_suspicion | asks_otp |
| s08 | en | scam | yes | high_suspicion | asks_otp |
| s09 | ar | scam | yes | high_suspicion | asks_card, asks_otp, link_mismatch_claimed |
| s10 | en | scam | yes | high_suspicion | asks_otp, link_mismatch_claimed, lookalike |
| s11 | ar | scam |  | high_suspicion | link_mismatch_claimed, brand_in_host, payment_request |
| s12 | en | scam |  | high_suspicion | link_mismatch_claimed, brand_in_host, payment_request |
| s13 | ar | scam |  | high_suspicion | link_mismatch_claimed, payment_request, prize |
| s14 | en | scam |  | high_suspicion | shortener, payment_request, prize |
| s15 | ar | scam |  | high_suspicion | link_mismatch_claimed, brand_in_host, urgency |
| s16 | en | scam |  | high_suspicion | link_mismatch_claimed, lookalike, urgency |
| s17 | ar | scam | yes | high_suspicion | asks_card, link_mismatch_claimed, lookalike |
| s18 | en | scam |  | high_suspicion | link_mismatch_claimed, brand_in_host, no_https |
| s19 | ar | scam |  | high_suspicion | link_mismatch_claimed, ip_host, payment_request |
| s20 | en | scam |  | high_suspicion | asks_personal, link_mismatch_claimed, brand_in_host |
| s21 | ar | scam |  | high_suspicion | link_mismatch_claimed, brand_in_host, payment_request |
| s22 | en | scam |  | high_suspicion | link_mismatch_claimed, unusual_tld, payment_request |
| s23 | ar | scam |  | high_suspicion | asks_personal |
| s24 | en | scam | yes | high_suspicion | asks_otp |
| s25 | ar | scam |  | high_suspicion | link_mismatch_claimed, punycode, payment_request |
| s26 | en | scam |  | high_suspicion | link_unknown_for_claim, shortener, payment_request |
| s27 | ar | scam | yes | high_suspicion | asks_card, asks_otp, link_mismatch_claimed |
| s28 | en | scam |  | high_suspicion | link_mismatch_claimed, brand_in_host, payment_request |
| s29 | ar | scam | yes | high_suspicion | asks_otp, link_mismatch_claimed, brand_in_host |
| s30 | en | scam |  | high_suspicion | link_mismatch_claimed, brand_in_host, payment_request |
| l01 | ar | legit |  | no_visible_indicators |  |
| l02 | en | legit |  | no_visible_indicators |  |
| l03 | en | legit |  | no_visible_indicators |  |
| l04 | ar | legit |  | no_visible_indicators |  |
| l05 | ar | legit |  | no_visible_indicators |  |
| l06 | en | legit |  | no_visible_indicators |  |
| l07 | en | legit |  | no_visible_indicators |  |
| l08 | ar | legit |  | no_visible_indicators |  |
| l09 | ar | legit |  | no_visible_indicators |  |
| l10 | en | legit |  | no_visible_indicators |  |
| l11 | en | legit |  | no_visible_indicators |  |
| l12 | ar | legit |  | no_visible_indicators |  |
| l13 | en | legit |  | no_visible_indicators |  |
| l14 | ar | legit |  | no_visible_indicators |  |
| o01 | ar | otp_delivery |  | no_visible_indicators |  |
| o02 | en | otp_delivery |  | no_visible_indicators |  |
| o03 | en | otp_delivery |  | no_visible_indicators |  |
| o04 | ar | otp_delivery |  | no_visible_indicators |  |
| o05 | en | otp_delivery |  | no_visible_indicators |  |
| o06 | ar | otp_delivery |  | no_visible_indicators |  |
| o07 | en | otp_delivery |  | high_suspicion | asks_otp |
| o08 | ar | otp_delivery |  | no_visible_indicators |  |
| a01 | en | ambiguous |  | no_visible_indicators |  |
| a02 | ar | ambiguous |  | unclear | shortener |
| a03 | en | ambiguous |  | unclear | urgency, payment_request |
| a04 | ar | ambiguous |  | no_visible_indicators |  |
| a05 | en | ambiguous |  | unclear | payment_request, no_https |
| a06 | ar | ambiguous |  | no_visible_indicators |  |
| a07 | en | ambiguous |  | no_visible_indicators |  |
| a08 | ar | ambiguous |  | no_visible_indicators |  |
