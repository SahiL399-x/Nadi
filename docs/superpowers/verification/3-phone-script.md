# NADI 3-phone demo verification

Runnable acceptance checklist for the live cross-device demo (spec §5) plus the
low-end smoothness gate (spec §6). Re-run this end to end against the real LAN
stack before the demo. **Do not call the demo build "done" until every box passes.**

Phones:
- **A = patient** — new +91 number self-signs up (always patient).
- **B = doctor** — login `+915000000001`, OTP `123456`.
- **C = pharmacy** — login `+915000020000`, OTP `123456`.

> Portal navigation note: Plans 05 (doctor portal) and 06 (pharmacy portal) add a
> dashboard landing for B and C and relocate the queue to the doctor **Queue** tab
> and the inbox to the pharmacy **Orders**/inbox tab. The booked-patient (step 5)
> and new-order (step 10) still appear there within one poll cycle (~4 s).

## Pre-run setup (LAN stack)

1. Bring up the real backend (auto-migrates + seeds, ADR-0003):
   ```bash
   docker compose -f infra/docker-compose.yml up -d --build
   ```
2. From a phone's browser confirm `GET http://<LAN-IP>:8000/health` → `{"status":"ok"}`.
3. Point the app at the LAN host — `apps/mobile/.env`:
   ```
   EXPO_PUBLIC_API_URL=http://<LAN-IP>:8000
   ```
4. Build the **dev client** on each phone (MapLibre + Jitsi need a native dev build,
   not Expo Go):
   ```bash
   cd apps/mobile && npx expo run:android
   ```

## Acceptance checklist (run every box end to end)

1. [ ] A: new +91 number → OTP `123456` + name → green patient home.
2. [ ] A: enter "chest pain and breathlessness" → Analyzing → **RED emergency view**
       with Call-108 button. (Back out.)
3. [ ] A: enter "fever and cough", add one report photo → tile shows "Ready"
       (uploaded to MinIO) → Analyzing → Result with specialty + drivers.
4. [ ] A: doctors list loads; toggle **Map** → MapLibre map with doctor pins; pick a
       doctor → slot → Book → Booked.
5. [ ] A → B: within ~4 s B's queue shows the new booked patient, acuity-sorted.
6. [ ] A & B: both tap Join/Start consultation → same jit.si room → video connects
       (camera/mic allowed).
7. [ ] B: open the case → NADI Note (acuity, confidence %, drivers) + labs render →
       write a prescription → Issue.
8. [ ] B → A: A's prescription screen (was "waiting…") now shows the medicines within ~3 s.
9. [ ] A: choose a pharmacy (nothing pre-ticked) → Send → status shows.
10. [ ] A → C: within ~4 s C's inbox/orders shows the order → open → Accept.
11. [ ] C → A: A's prescription status flips to ACCEPTED within ~3 s.
12. [ ] Repeat 9–11 choosing a closed/declining pharmacy → C declines →
        "forwarded to the next pharmacy" → the next consented pharmacy receives it.

Fix any failure before proceeding.

## Low-end device smoothness gate (spec §6)

Run on the **cheapest available physical Android phone** (not the emulator):

- [ ] Scroll the doctor list, doctor queue, and pharmacy inbox — no dropped-frame
      stutter (target 60 fps / 16 ms frames; FlashList recycling + expo-image caching
      should hold this).
- [ ] Navigation transitions and the "analysing" animation stay smooth while a fetch
      is in flight (Reanimated runs them on the UI thread).
- [ ] Toggle the doctor map — it lazy-mounts without freezing the list.
- [ ] The whole patient → doctor → pharmacy loop completes with no jank, blank screen,
      or raw spinner.

Device model tested: `__________________________` (record here each run).

## Automated gate (spec §5) — run before the device session

```bash
cd apps/mobile && npm test && npm run typecheck
cd apps/api && .venv/Scripts/python -m pytest
```
All green.

## Done criteria

- `npm test` + `npm run typecheck` (mobile) green; `pytest` (api) green.
- The acceptance checklist passes end to end on the real LAN stack.
- The low-end-device smoothness gate passes, device model recorded above.

At this point the demo build is complete: all three roles, real backend, real upload,
real video, real cross-device sync, MapLibre map, and the performance gate met — all at
$0 with no billing account. Remaining project work (trained ML models, Phases 3–5;
deployment) is out of scope per the spec and tracked separately.
