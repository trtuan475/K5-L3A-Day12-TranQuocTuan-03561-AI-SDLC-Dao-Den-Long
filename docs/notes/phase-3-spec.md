# Phase 3: Ticket-03 "Đèn cạn dầu": AC và giả định

Quyết định thiết kế: [ADR 0001](../adr/0001-lantern-fuel-and-dawn-win.md). Breaking changes: [CHANGELOG](../../CHANGELOG.md).

## Giả định (C1…)
- C1. Bóng Mực `wander` khi không có đèn yếu sẽ đi về **đèn tắt gần nhất** (bằng nhau thì id nhỏ hơn) với tốc độ 2 m/s. Không còn đèn tắt nào thì đi tới điểm ngẫu nhiên như trước (B4).
- C2. `fuel_drain` ghi cho **từng** Bóng Mực đang hút, ở mỗi tick thứ 60, 120, … tính từ lúc nó vào `drain`. `fuel` trong sự kiện là giá trị sau khi trừ ở tick đó.
- C3. Bóng Mực `drain` vẫn gây sát thương nếu Mây chạm vào nó.
- C4. Đèn đặt `lit: true` bằng scenario: mặc định `fuel` = 100, `ever_lit` = true, `deposited` = chi phí. Việc đặt này không tính vào `successful_lights`.
- C5. Châm dầu làm fuel đi từ < 30 lên ≥ 30: các Bóng Mực trong 6 m bị đẩy ra mép trong 30 tick, giống lúc đèn vừa thắp.
- C6. Thưởng bình minh mỗi đèn = 50 + floor(fuel) (fuel đo bằng đơn vị dầu, sau khi trừ ở tick cuối).

## Acceptance criteria → test
| ID | Tiêu chí | Test |
|---|---|---|
| P3-1 | Thắp thì fuel = 100, giảm 1/s; hết dầu thì tắt, `deposited` = 0, `lantern_out`, `ever_lit` | `test_fuel_decay_and_out` |
| P3-2 | Châm dầu: used = min(n, ceil((100 − f)/10)), +10 dầu mỗi đom đóm, sự kiện `refuel`; đèn đầy không được chọn | `test_refuel*` |
| P3-3 | Thắp lại tốn 5, +40, `relight: true`, `relit_count` | `test_relight` |
| P3-4 | Vùng an toàn chỉ có khi fuel ≥ 30 (đúng 30 vẫn còn) | `test_safe_threshold` |
| P3-5 | `wander` đi tới đèn yếu, vào `drain` ở ≤ 2 m, hút 5/s cộng dồn, `fuel_drain` mỗi 60 tick; thoát ra `chase` (≤ 6 m) / `wander` (đèn tắt, ≥ 30, > 2 m) | `test_drain_*` |
| P3-6 | Châm lên ≥ 30 thì đẩy Bóng Mực ra mép, không gây sát thương | `test_refuel_evicts` |
| P3-7 | Thắng `dawn_survived` khi đủ ngưỡng đèn ở bình minh; thua `dawn` khi thiếu; `no_flames` ưu tiên ở tick cuối; không thắng sớm | `test_dawn_*` |
| P3-8 | Sức chứa 10 + 2k, tối đa 20 | `test_capacity` |
| P3-9 | Điểm mới (+5/+100/+40/+5/+15, thưởng bình minh) | `test_score_*`, `test_pulse_drain_score` |
| P3-10 | Contract v1.2: trường snapshot/scenario/sự kiện mới, thời lượng 240/270/300 | `test_v12_*` |
| P3-11 | UI: thanh dầu, nhấp nháy 1 Hz khi < 30, HUD sức chứa, chế độ mù màu được lưu (viền #00B3FF, cảnh báo trắng kèm ⚠, đèn tắt xẹp 20% + giấy rách) | Ảnh + code `play.py` |
