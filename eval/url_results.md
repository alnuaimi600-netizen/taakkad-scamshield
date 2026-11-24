# Link-only evaluation

- Run: 2026-11-24 06:59 UTC
- Mode: **rules only**, each URL checked alone (no message text)
- Data: `data/synthetic_urls.jsonl`: 60 synthetic URLs (30 phishing, 30 legitimate)

> Caveat: the URLs were written by the same team that wrote the rules, so these numbers are
> in-sample and likely optimistic. They are not a measure of real-world accuracy.

| Counting as "flagged" | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| `high_suspicion` only | 1.00 | 0.73 | 0.85 | 22 | 0 | 8 |
| `high_suspicion` or `unclear` | 0.94 | 1.00 | 0.97 | 30 | 2 | 0 |

## By trick

| label / trick | results |
|---|---|
| legitimate/official | no_visible_indicators: 12 |
| legitimate/shortener_legit | unclear: 2 |
| legitimate/unrelated | no_visible_indicators: 16 |
| phishing/at_sign | high_suspicion: 2 |
| phishing/brand_in_host | high_suspicion: 12 |
| phishing/ip_host | unclear: 2 |
| phishing/lookalike | high_suspicion: 8 |
| phishing/odd_structure | unclear: 1 |
| phishing/punycode | unclear: 2 |
| phishing/shortener | unclear: 3 |

## Per URL

| id | label | trick | url | status | risk | flags |
|---|---|---|---|---|---|---|
| p01 | phishing | lookalike | `https://oasisbnak.test/login` | high_suspicion | 79 | lookalike |
| p02 | phishing | lookalike | `https://0asisbank.test/verify` | high_suspicion | 79 | lookalike |
| p03 | phishing | lookalike | `https://fa1con-express.test/track` | high_suspicion | 79 | lookalike |
| p04 | phishing | lookalike | `https://falcon-expres.test/redelivery` | high_suspicion | 79 | lookalike |
| p05 | phishing | lookalike | `https://najmtelekom.test/bill` | high_suspicion | 79 | lookalike |
| p06 | phishing | lookalike | `https://souqwahaa.test/order/7781` | high_suspicion | 79 | lookalike |
| p07 | phishing | lookalike | `http://arame0x.test/parcel` | high_suspicion | 82 | no_https, lookalike |
| p08 | phishing | lookalike | `https://emiratespostt.test/fees` | high_suspicion | 79 | lookalike |
| p09 | phishing | brand_in_host | `https://tamm-fines.test/pay` | high_suspicion | 79 | brand_in_host |
| p10 | phishing | brand_in_host | `https://uaepass.ae.login-verify.test` | high_suspicion | 79 | brand_in_host |
| p11 | phishing | brand_in_host | `https://tamm.abudhabi.services-portal.test/violations` | high_suspicion | 79 | brand_in_host |
| p12 | phishing | brand_in_host | `https://uaepass-update.example/auth` | high_suspicion | 79 | brand_in_host |
| p13 | phishing | brand_in_host | `https://oasisbank.secure-login.test/` | high_suspicion | 79 | brand_in_host |
| p14 | phishing | brand_in_host | `https://falcon-express-delivery.test/pay` | high_suspicion | 79 | brand_in_host |
| p15 | phishing | brand_in_host | `https://adpolice-fines.example/pay` | high_suspicion | 79 | brand_in_host |
| p16 | phishing | brand_in_host | `https://emiratespost-redelivery.test/form` | high_suspicion | 79 | brand_in_host |
| p17 | phishing | brand_in_host | `https://salik-topup.test/recharge` | high_suspicion | 79 | brand_in_host |
| p18 | phishing | brand_in_host | `https://rta-fines-portal.test/` | high_suspicion | 79 | brand_in_host |
| p19 | phishing | brand_in_host | `https://souqwaha-pay.test/receive` | high_suspicion | 79 | brand_in_host |
| p20 | phishing | brand_in_host | `https://najmtelecom-rewards.test/claim` | high_suspicion | 79 | brand_in_host |
| p21 | phishing | at_sign | `https://oasisbank.test@login-check.test/session` | high_suspicion | 79 | at_sign |
| p22 | phishing | at_sign | `http://tamm.abudhabi@203.0.113.7/pay` | high_suspicion | 88 | ip_host, no_https, at_sign |
| p23 | phishing | punycode | `https://xn--oasisbnk-6za.test/` | unclear | 48 | punycode, odd_structure |
| p24 | phishing | punycode | `https://xn--tmm-xla.test/fines` | unclear | 48 | punycode, odd_structure |
| p25 | phishing | ip_host | `http://192.0.2.44/oasis/verify` | unclear | 39 | ip_host, no_https |
| p26 | phishing | ip_host | `http://198.51.100.9/track.php?id=1` | unclear | 39 | ip_host, no_https |
| p27 | phishing | shortener | `https://bit.ly/3fakeUAE` | unclear | 30 | shortener |
| p28 | phishing | shortener | `https://tinyurl.com/parcel-fee-ae` | unclear | 30 | shortener |
| p29 | phishing | shortener | `https://cutt.ly/oasis-otp` | unclear | 30 | shortener |
| p30 | phishing | odd_structure | `http://secure-login-verify-account-update.test/a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p/q/r/s/t/u/v/w/x` | unclear | 30 | no_https, odd_structure |
| l01 | legitimate | official | `https://oasisbank.test/` | no_visible_indicators | 5 |  |
| l02 | legitimate | official | `https://www.oasisbank.test/cards` | no_visible_indicators | 5 |  |
| l03 | legitimate | official | `https://online.oasisbank.test/login` | no_visible_indicators | 5 |  |
| l04 | legitimate | official | `https://falcon-express.test/track?id=FX99812` | no_visible_indicators | 5 |  |
| l05 | legitimate | official | `https://www.falcon-express.test/` | no_visible_indicators | 5 |  |
| l06 | legitimate | official | `https://track.falcon-express.test/FX1200` | no_visible_indicators | 5 |  |
| l07 | legitimate | official | `https://najmtelecom.test/pay-bill` | no_visible_indicators | 5 |  |
| l08 | legitimate | official | `https://my.najmtelecom.test/` | no_visible_indicators | 5 |  |
| l09 | legitimate | official | `https://souqwaha.test/deals?ref=sms` | no_visible_indicators | 5 |  |
| l10 | legitimate | official | `https://www.souqwaha.test/orders/55120` | no_visible_indicators | 5 |  |
| l11 | legitimate | official | `http://oasisbank.test/branches` | no_visible_indicators | 15 | no_https |
| l12 | legitimate | official | `https://help.souqwaha.test/returns` | no_visible_indicators | 5 |  |
| l13 | legitimate | unrelated | `https://recipes-daily.test/machboos` | no_visible_indicators | 5 |  |
| l14 | legitimate | unrelated | `https://abudhabi-weather.example/today` | no_visible_indicators | 5 |  |
| l15 | legitimate | unrelated | `https://school-events.test/2026/sports-day` | no_visible_indicators | 5 |  |
| l16 | legitimate | unrelated | `https://family-photos.example/album/42` | no_visible_indicators | 5 |  |
| l17 | legitimate | unrelated | `https://desert-camping.test/booking` | no_visible_indicators | 5 |  |
| l18 | legitimate | unrelated | `https://cityrunners.example/club` | no_visible_indicators | 5 |  |
| l19 | legitimate | unrelated | `https://library.example/catalog?q=arabic+poetry` | no_visible_indicators | 5 |  |
| l20 | legitimate | unrelated | `https://garden-tips.test/palms` | no_visible_indicators | 5 |  |
| l21 | legitimate | unrelated | `https://football-fans.example/match/uae-ksa` | no_visible_indicators | 5 |  |
| l22 | legitimate | unrelated | `https://dubai-marathon.test/register` | no_visible_indicators | 5 |  |
| l23 | legitimate | unrelated | `https://coffee-corner.test/menu` | no_visible_indicators | 5 |  |
| l24 | legitimate | unrelated | `https://kids-coding.example/lesson-3` | no_visible_indicators | 5 |  |
| l25 | legitimate | unrelated | `http://old-forum.test/thread/991` | no_visible_indicators | 15 | no_https |
| l26 | legitimate | unrelated | `https://news.example/uae/2026/11/23/rain` | no_visible_indicators | 5 |  |
| l27 | legitimate | unrelated | `https://car-wash-booking.test/slots` | no_visible_indicators | 5 |  |
| l28 | legitimate | unrelated | `https://quran-app.example/surah/1` | no_visible_indicators | 5 |  |
| l29 | legitimate | shortener_legit | `https://bit.ly/souqwaha-sale` | unclear | 30 | shortener |
| l30 | legitimate | shortener_legit | `https://t.co/najmnews` | unclear | 30 | shortener |
