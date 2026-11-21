# Phase 3: Truy vết Ticket-03 → bằng chứng

Chạy lại:
- `bash scripts/verify.sh phase-3` sinh [REPORT.md](REPORT.md).
- `python3 play.py --demo --shots docs/proof/phase-3/shots` sinh ảnh; thêm `--colorblind` để có bộ ảnh [shots_colorblind/](shots_colorblind/).
- [fps.txt](fps.txt): 119.3 FPS ở 1280×720, Đêm 3.

Quyết định thiết kế: [ADR 0001](../../adr/0001-lantern-fuel-and-dawn-win.md) · Breaking changes: [CHANGELOG](../../../CHANGELOG.md) · AC/giả định: [phase-3-spec](../../notes/phase-3-spec.md)

| Yêu cầu Ticket-03 | AC | Kiểm chứng | Kết quả |
|---|---|---|---|
| Nhiên liệu: thắp thì 100, hao 1/s (số nguyên 1/60), hết dầu thì tắt + `lantern_out`, `deposited` = 0, `ever_lit` | P3-1 | `test_fuel_decay_and_out` | Đạt |
| Châm dầu: công thức `used`, sự kiện `refuel`, đèn đầy không được chọn | P3-2 | `test_refuel`, `test_refuel_full_not_selected` | Đạt |
| Thắp lại tốn 5, +40, `relight`, `relit_count` | P3-3 | `test_relight` | Đạt |
| Vùng an toàn chỉ có khi fuel ≥ 30 (đúng 30 vẫn còn) | P3-4 | `test_safe_threshold` | Đạt |
| Bóng Mực `drain`: chọn đèn yếu, ≤ 2 m, 5/s cộng dồn, `fuel_drain` mỗi 60 tick, thoát ra chase/wander | P3-5 | `test_drain`, `test_drain_breaks_to_chase` | Đạt |
| Châm lên ≥ 30 thì đẩy Bóng Mực ra, không gây sát thương | P3-6 | `test_refuel_evicts_and_stops_drain` | Đạt |
| Thắng `dawn_survived` theo ngưỡng 3/5, 4/6, 5/7; thua `dawn`; `no_flames` ưu tiên; không thắng sớm | P3-7 | `test_dawn_*`, `test_thresholds`, `test_no_early_win`, scenario CLI `win.json` | Đạt |
| Sức chứa 10 + 2k, tối đa 20, hiển thị trên HUD | P3-8 | `test_capacity`; ảnh `shots/n1_3_late.png` ("Đom đóm 4/12") | Đạt |
| Điểm mới | P3-9 | `test_dawn_win_score`, `test_relight`, `test_refuel`, `test_pulse_drain_score` | Đạt |
| Contract v1.2: tuning, snapshot (`fuel`/`ever_lit`/`relit_count`/`capacity`), thời lượng 240/270/300 | P3-10 | `test_v11_snapshot_fields` (đã mở rộng), `test_initial_state`, REPORT | Đạt |
| Mù màu: viền/mắt #00B3FF, cảnh báo trắng + ⚠, được lưu | P3-11 | So sánh [shots/n1_3_late.png](shots/n1_3_late.png) (#7A3CFF) với [shots_colorblind/n1_3_late.png](shots_colorblind/n1_3_late.png) (#00B3FF) | Đạt phần viền. Biểu tượng ⚠ (tam giác trắng có "!") và việc lưu cài đặt **chưa kiểm chứng** |
| Thanh dầu, nhấp nháy 1 Hz khi < 30; đèn tắt xẹp 20% + giấy rách | P3-11 | Code `World.sync` trong play.py | **Chưa kiểm chứng bằng ảnh** (không ảnh nào có đèn sáng trong khung) |
| Bot sống tới bình minh và thắng | | REPORT: bot thắng Đêm 1 seed 3 với `dawn_survived` | Đạt Đêm 1. Đêm 2/3 bot thua |
| Test cũ bị luật mới thay thế | DoD | Đã viết lại kèm lý do trong test và CHANGELOG; không có test nào bị skip | Đạt |
