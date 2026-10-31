# Addendum: the availability check is circular (A5 G2, audit #11)

**SECTION_4_3_CLOSED** (unchanged; the closed reports are not edited)

Added 2026-10-31T03:34:03.174286+00:00 UTC (2026-10-30T23:34:03.174286-04:00 New York). A5 `amendment_4_3_A5_20261031T023320Z.json` SHA-256 `2637654bac921c171935011a9bc7d22bd7c2168f786397c2b2376d0d0179c35b`. Source `section4_3_1_candidates.py` SHA-256 `4c8d2b528ff8b86a2885426d974e9be97fbc3d264d60b4e2bf38f16981204878`.

Lines of `load_development` that mention availability:

    available = ns(p.available_utc_assuming_minute_start)
    require((available == t + MINUTE).all(), "Availability not bar close")
    return dict(era=era, t=t, available=available, day=day, slot=slot, r=r,

    PANEL_COLUMNS = ["utc_minute_start_assumed", "available_utc_assuming_minute_start",

- The loader reads the availability column available_utc_assuming_minute_start and asserts that it equals the bar's minute-start stamp plus 60 seconds. The column name states the assumption it was built from, so the assertion tests the panel's own construction and cannot fail.
- Policy P1 R1 lists this assertion as its enforcement: 'load_development asserts available == t + 60 s for every bar; construction is trailing-only (Step 4 finds no output that reads bars after t).'. The R1 evidence about availability therefore rests on the same assumption.
- The frozen protocol states the assumption as inherited: 'Minute-start assumption inherited from Section 3; full bar available at stamp + 60 seconds', and requires: 'Later cross-asset timing must report legacy -1/0/+1 minute scenarios; primary clock remains conditional'.
- RAW has no clock-sensitivity test; the LEGACY -1/0/+1 minute sensitivity is an open Section 5 item (ledger item 5).
- Nothing in this repository tests the bar-label assumption against an independent clock.
