# Phase 2: Ticket-02 "Ba hòn đảo": spec, thay đổi, giả định, AC

Nguồn: Ticket-02 (Contract v1.1). File này thay thế các giả định của Phase 1 ở những chỗ ticket đã chuẩn hóa.

## Thay đổi so với Phase 1 (và lý do)
| Phase 1 | Phase 2 | Lý do |
|---|---|---|
| Tuning tự chọn (lantern_cost 5, pulse 1/6 m/1 s, safe 5 m, invuln 2 s, shade 3 m/s…) | Số chuẩn của ticket | Phần 1 bắt buộc |
| +10 điểm khi **nhặt** | +10 điểm mỗi đom đóm **nạp**; thưởng thắng là `floor(s)×2 + 50×lửa`; +5 mỗi Bóng Mực trúng pulse | Điểm chuẩn hóa |
| Thắng xét ngay khi thắp đèn | Thắng/thua xét **cuối tick** (bước 11) | Thứ tự xử lý bắt buộc |
| Rào vô hình, `fall_enabled=false` | Rơi khỏi đảo (Y < −10), `fall_enabled=true` | Bản đồ chuẩn |
| Đom đóm rơi biến mất | Rơi ra vành 1.5–2.5 m, TTL 480 tick, nhặt lại được | Số chuẩn |
| 30 đom đóm ngẫu nhiên, hồi sinh sau 5 s | 20 ở điểm sinh chuẩn, +1 mỗi 240 tick, trần 30 | Số chuẩn |
| Bóng Mực có 2 trạng thái `chase`/`stunned` | `spawning/wander/chase/recoil/stunned` | Contract v1.1 |
Các test Phase 1 bị thay đổi: được viết lại theo số chuẩn trong `tests/test_sim.py`. Test nào mâu thuẫn với ticket thì được sửa và ghi chú `# Phase 2:` ngay trong test.

## Giả định mới (B1…)
- B1. **Điểm xuất phát:** Đêm 1 và Đêm 2 là (0,0,0). Đêm 3 là **(0,0,−30)**, quay mặt về +Z, vì tâm (0,0,0) nằm trong tháp chuông (ticket không nói rõ).
- B2. **Góc:** điểm ở bán kính r, góc a có tọa độ (r·cos a, y, r·sin a), tức z = r·sin a. Cách này khớp với "tầng 1 ở nửa z > 0" và các góc 20°…160°.
- B3. **Tăng tốc/dừng tức thời** (0 s, thỏa "≤ 0.1 s"). Leo bậc tối đa 0.35 m mỗi tick, nên đi được dốc nhưng không leo được vách. Khi đang trên không, vách chặn chuyển động ngang.
- B4. **`spawning`** kéo dài 60 tick: Bóng Mực đứng yên và không gây sát thương. **`wander`**: bay tới một điểm sinh đom đóm ngẫu nhiên với tốc độ 2 m/s. Bóng Mực bay ở độ cao mặt đất + 1.0 m (= tâm), bay được qua biển mây và vách, nhưng không xuyên tháp chuông.
- B5. **Chênh cao khi chạm:** đo |tâm Bóng Mực.y − chân Mây.y| ≤ 1.5. Đom đóm và bùa: |chân Mây.y − mặt đất nơi đặt.y| ≤ 1.5.
- B6. **Tương tác với đèn** đo khoảng cách XZ (như v1.0).
- B7. **Bóng Mực mới sinh** chọn ngẫu nhiên trong các điểm hợp lệ (cách người chơi ≥ 15 m). Không giới hạn chuyện 2 Bóng Mực trùng một điểm. Tổng số Bóng Mực đã sinh không vượt mức tối đa (Bóng Mực không chết).
- B8. **Trần 30 đom đóm** đếm mọi đom đóm đang có trên bản đồ (cả loại rơi). "Điểm trống" là điểm sinh chưa có đom đóm `random` đứng trên đó.
- B9. **Gió (Đêm 3):** bắt đầu ở sim_tick 1800·k (k ≥ 1), kéo dài 300 tick, hướng ngẫu nhiên là số nguyên độ (seed). Gió chỉ đẩy Mây. Báo trước 120 tick (chỉ có trong UI). Khi không có gió, `dir_deg` giữ hướng của cơn gió gần nhất (ban đầu là 0).
- B10. **Gió Lạc:** điểm sinh là các điểm sinh Bóng Mực của Đêm. Gió Lạc ở `idle` cũng cướp nếu chạm vào khi Mây mang > 0. Pulse trúng Gió Lạc đang `idle` không có tác dụng. Gió Lạc đã `removed` vẫn nằm trong snapshot với state `removed`.
- B11. `night_start` được ghi ở tick 0, trước snapshot tick 0. Dựng scenario không sinh sự kiện, nhưng đây là sự kiện của lần chạy.
- B12. Snapshot `player.invuln` là **boolean** (đang bất tử hay không). `*_cd_s`, `charm_s`, `ttl_s`, `respawn_s` là số giây còn lại (làm tròn 3 chữ số). `ttl_s` của đom đóm `random` là `null`.
- B13. **Rơi khi đang có hiệu ứng:** trong 60 tick chờ hồi sinh, Mây đứng yên ở chỗ rơi (Y < −10). Mây không nhặt, không bị chạm, không bị cướp, và Bóng Mực coi như không thấy Mây. Pulse không kích hoạt.
- B14. **Pulse trúng mọi Bóng Mực trong 5 m** (kể cả đang `spawning`/`recoil`), làm mới choáng. Lực đẩy dừng ở mép vùng an toàn và tháp chuông.
- B15. **Lướt khi đang bị bục phóng:** trong 12 tick lướt dùng vận tốc lướt, sau đó vận tốc phóng tiếp tục tới khi chạm đất. Lướt bắt đầu trên không thì giữ nguyên Y.

## Acceptance criteria → test (mỗi tính năng mới có ít nhất 1 scenario headless)
| ID | Tiêu chí | Test |
|---|---|---|
| P2-1 | Số chuẩn: tốc độ 6, nhảy 7/−20 (đỉnh 1.225 m), lướt 14 m/s × 12 tick, hồi 90 tick | `test_std_*`, `test_dash*` |
| P2-2 | Đom đóm: 20 ban đầu ở điểm chuẩn, +1 mỗi 240 tick, trần 30, nhặt theo XZ + chênh cao | `test_mote_*` |
| P2-3 | Đèn: chi phí 10, nạp nhiều lần, chọn gần nhất/id nhỏ hơn, +10/đom đóm nạp, +100/đèn | `test_deposit_*` |
| P2-4 | Vùng an toàn 6 m: chặn ở mép, đẩy ra trong ≤ 30 tick, không sát thương khi đang bị đẩy | `test_safe_*` |
| P2-5 | Pulse: chi phí 3, 3D ≤ 5 m tính từ chân + 0.8, choáng 120 tick, đẩy 4 m trong 15 tick, hồi 180 tick, +5 điểm | `test_pulse_*` |
| P2-6 | Bóng Mực: các trạng thái, phát hiện 12/bỏ đuổi 18, lịch sinh 300 + k·480/420/360, tối đa 6/8/10, recoil 2 m/60 tick, 1 hit mỗi tick theo id | `test_shade_*` |
| P2-7 | Bị đánh: −1 lửa, rơi floor(n/2) ra vành 1.5–2.5 m, TTL 480, bất tử 90 tick | `test_hit_*` |
| P2-8 | Rơi khỏi đảo: −1 lửa, mất hết đom đóm, chờ 60 tick, hồi sinh có bất tử 90 tick; hết lửa thì thua ngay | `test_fall_*` |
| P2-9 | Thắng/thua cuối tick, thưởng thắng; thắng được cả ở đúng tick hết giờ | `test_end_*` |
| P2-10 | Đêm 2: hai đảo + cầu, bục phóng đáp xuống đảo kia sau khoảng 1.4 s | `test_night2_*` |
| P2-11 | Đêm 3: tầng, vách, dốc, bục lên tầng 2, tháp chuông, gió | `test_night3_*` |
| P2-12 | Gió Lạc: idle→chase→flee→removed, cướp min(3, n), pulse làm chạy/thả đồ | `test_drifter_*` |
| P2-13 | Bùa Gió: 7.2 m/s, lướt không hồi chiêu, 600 tick, xuất hiện lại sau 2700 tick | `test_charm_*` |
| P2-14 | Pause: tick tăng nhưng sim_tick và đồng hồ đứng yên, state `paused`, có sự kiện | `test_pause` |
| P2-15 | Contract v1.1: các trường snapshot, `--night 1..3`, sự kiện mới, cả đêm ≤ 30 s | `test_cli_*`, `verify.sh` |
| P2-16 | Chuỗi 3 Đêm, menu, pause/cài đặt lưu lại, âm thanh, HUD, bảng màu, ánh sáng môi trường | Ảnh + kiểm tra tay (TRACE) |
| P2-17 | ≥ 30 FPS ở 1280×720 | `play.py --bench` |
