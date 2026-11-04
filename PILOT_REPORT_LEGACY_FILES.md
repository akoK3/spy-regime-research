# Files behind PILOT_REPORT_LEGACY.md

Written 2026-11-04T00:20:36.298674+00:00 UTC under `AMENDMENT_A14.md` (audit finding 22). `PILOT_REPORT_LEGACY.md` is a closed record and is not edited; its writer script is not recoverable and was not recreated. The hashes below are of the files as they are now.

| File | SHA-256 now |
|---|---|
| `PILOT_REPORT_LEGACY.md` | `8b4f675258ad85035a7e5286a8e5d237a9b24128b122a1bb0975426ca00f4901` |
| `section5/s5_legacy_pilot.py` | `bdb7e662bc7f2004027b2e9c8946df2ccdd80519fac4d15ff42f9127b9c4c923` |
| `section5/s5_legacy_resume_check.py` | `dba45caadb0a57f5fd03115c92c47f7920fe56973fdad06aa964d6337147c8ea` |
| `section5/results/legacy_build.json` | `354523600da1d49d0c1fa0bca6568ecc4bcb423080f75c19651c59eb7f261f7b` |
| `section5/results/legacy_build_log.txt` | `e99dc484973a905ae4c0d35c45ac605a1c537ea9f6f51eeaf426ad515c38ac98` |
| `section5/results/legacy_mem.json` | `2125b8b219d705d68d010108647d6d227e7eb255133e0355951481c707dd4b3e` |
| `section5/results/legacy_pilot_results_run_1793580880.json` | `fbd20e50ca8ef1ae945fc4d9fb9579d17121acf41dcf77dd0d41ed1292d8ab9c` |
| `section5/results/legacy_resume_check.json` | `e613304287dc77e8192e8b65e369cb96037f7b895a7895435195f48742452382` |
| `section5/results/legacy_run1_log.txt` | `13afedc342c93d2ed9714c6e0cf5cd5dc76c427de3f42e329ee692fb0d71fb3a` |
| `section5/results/legacy_run2_log.txt` | `beca34228426b2840b7128a231eb34faa199ab702f12b8c62c3c65ca4d18676f` |

Code modules the pilot imported, compared with their version at the pilot commit `889d6cc`:

| Module | Hash at pilot commit | Hash now | Changed since the pilot |
|---|---|---|---|
| `section5/s5_lib.py` | `bd91387861974903148e8a0e0bbcafd48722583f80ed70933f894c6a02a89d20` | `bd91387861974903148e8a0e0bbcafd48722583f80ed70933f894c6a02a89d20` | no |
| `section5/s5_models.py` | `8c0f9acbe0fb0a9d83e43bcf4d657518cd24114fd3ff9f2213d51c9ddbd91daf` | `837b2c9206c91ae3ff472bd7652866a6c91a2ec3c07acdce318edfda0505a640` | yes |
| `section5/s5_events.py` | `25b3e7c713942966f26e8ec6262ab6113ee684f2bb825eae56b094735d50665e` | `81491e8a142fb83b74dd06219dca565c08fac76703f19f3bd18e70a2ce45e1e8` | yes |
| `section5/s5_eval.py` | `d37ea9b0fe6ecc6ae650790f67a4e1caf5512a2433b542ca1dfd7ec9b9af3ef6` | `88107ffaff297abd32c8c282274ab7221da381eb5b5fd3434ffc2213c9d7ef47` | yes |
| `section5/s5_sweep.py` | `dfb7fe2264df396d68c2c797f929aeeab6aeea910063cfc635c8e4d6f22f9b00` | `41353c22f222d4f85cf64c25ced24991f0ceb17ed1b9cc5b8c1ab9b37afb4f4e` | yes |
| `section5/s5_fast.py` | `8132aabb8b66d64c0fa8d815990d33da83ba97247f9a9b65311e10654f54523c` | `9666ad37e8d1f10826c7adb1fd35ea3ed5d59b0417e87e67c435b3dfe2590fe7` | yes |
| `section5/s5_a6.py` | `ed1e04f17f9c47b758cc489c6d01a61046d130eac81cafde3252a03034c268f9` | `0d6afb70d7a62839d8fdd4216512c6f71a09e83cc7558df873314bc9e769c741` | yes |
| `section5/s5_a7.py` | `84b6f42a200b02b047cba393b5b9bb7aee953961331c5d6e92d4b2e5e671f01e` | `84b6f42a200b02b047cba393b5b9bb7aee953961331c5d6e92d4b2e5e671f01e` | no |
| `section5/s5_d2.py` | `de822812d38d1b152a179ef37cd7fc2b77a1144fadf8d97be6e8300f8d761a02` | `487e48174e58cf7ec07bea0f9b333adc0e00f3e81fdf5b818fac5ff2a8f7b9cc` | yes |
| `section5/s5_d2_stable.py` | `600a3a5ea0815a91cd7b9681d2412f69fa60ef7079038f47e41059e5eb0b53db` | `600a3a5ea0815a91cd7b9681d2412f69fa60ef7079038f47e41059e5eb0b53db` | no |
| `section5/s5_pilot.py` | `3706267fb06d0a269a240d4d7704159b42d6724cb700dd28272debb992f77764` | `3706267fb06d0a269a240d4d7704159b42d6724cb700dd28272debb992f77764` | no |
| `section5/s5_legacy_pilot.py` | `bdb7e662bc7f2004027b2e9c8946df2ccdd80519fac4d15ff42f9127b9c4c923` | `bdb7e662bc7f2004027b2e9c8946df2ccdd80519fac4d15ff42f9127b9c4c923` | no |

The pilot results were computed with the pilot-commit versions; modules marked 'yes' were changed later (amendments A8 to A14), so rerunning the pilot script today does not reproduce them.
