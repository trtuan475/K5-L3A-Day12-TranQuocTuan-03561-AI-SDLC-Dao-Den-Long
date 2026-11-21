# Phase 4: Truy vết Ticket-04 → bằng chứng

Chạy lại:
- `bash scripts/verify.sh phase-4` sinh [REPORT.md](REPORT.md), kèm soak và kiểm tra export.
- `python3 play.py --bench-mode --seed 42 --duration 30 --out bench.json` sinh [../../../bench.json](../../../bench.json).
- `python3 soak.py --seed 7 --nights 10 --out soak.json` sinh [../../../soak.json](../../../soak.json).
- `python3 play.py --ui-tour docs/proof/phase-4/shots` (đặt `DDL_LEADERBOARD`/`DDL_SETTINGS` trỏ tới file tạm) sinh [shots/](shots/).
- `python3 play.py --demo --shots docs/proof/phase-4/shots_play` sinh [shots_play/](shots_play/).

AC/giả định: [phase-4-spec](../../notes/phase-4-spec.md).

| Yêu cầu | AC | Bằng chứng | Kết quả |
|---|---|---|---|
| Bench: 1280×720, vsync tắt, Đêm 1 đầy đủ hiệu ứng và HUD, 200 Bóng Mực `wander` + 100 đom đóm (seed 42), L1–L3 sáng 100, camera bay vòng r30/y15/15 s, khởi động 3 s, tự thoát | P4-1 | `test_scene`, `test_bench_rules_off`; [shots/bench.png](shots/bench.png) | Đạt |
| bench.json đúng định dạng và định nghĩa (avg, p1_low, p95, frames, load_ms, peak_mem) | P4-1b | bench.json (M2 Pro): **116.8 / 61.9 / 9.54 ms / 806 ms / 197 MB** | Đạt trên máy tự đo. Máy chấm của giảng viên chưa biết |
| Soak 10 Đêm, input ngẫu nhiên theo seed, crashes = 0, RSS ≤ ×1.2 | P4-2 | soak.json: 0 crash, 17.1 → 17.2 MB; `test_soak_short`; REPORT | Đạt |
| Bảng xếp hạng: nhập tên, regex, top 10, sắp xếp/bằng điểm, lưu bền, màn hình từ menu, export | P4-3 | `test_names`, `test_sort_ties_top10_persist`, `test_export_cli`; [ui_leaderboard](shots/ui_leaderboard.png) (có "Tuấn" với dấu), [ui_name_entry](shots/ui_name_entry.png) | Đạt. Việc gõ tên tiếng Việt bằng bàn phím trong InputField **chưa kiểm chứng** |
| Đổi phím mọi hành động, phát hiện trùng, khôi phục mặc định, lưu | P4-4 | [ui_keybinds](shots/ui_keybinds.png), [ui_keybind_clash](shots/ui_keybind_clash.png) | Đạt (ảnh). Lưu qua lần mở lại **chưa kiểm chứng tự động** |
| Phụ đề: Bóng Mực xuất hiện (+ mũi tên ở mép), gió, 10 s cuối, đèn < 30 | P4-5 | [shots_play/n3_2_mid](shots_play/n3_2_mid.png): sự kiện thật "Bóng Mực xuất hiện!" kèm mũi tên tím; [ui_play_captions](shots/ui_play_captions.png) (3 dòng do tour gọi) | Đạt cho Bóng Mực. Gió, 10 s cuối và dầu thấp mới thấy qua tour và code |
| Giảm chuyển động; chữ ≥ 18 px; chữ lớn ×1.25 | P4-6 | `ui_text` (scale ≥ 1, tức 0.025 × 720 = 18 px); [ui_settings](shots/ui_settings.png) | Đạt bằng code và ảnh. Hiệu ứng rung/chớp **chưa quay video** |
| Contract v1.3 | P4-7 | `test_contract` | Đạt |
| README (ảnh, yêu cầu hệ thống, 3 lệnh, điều khiển, test/headless/bench/soak), CHANGELOG 4 phase, CREDITS, LICENSE, retro | P4-8 | Các file ở gốc repo, [retro](../../notes/retro.md) | Đạt |
| Release v1.0.0 có bản chạy được + video < 5 phút | P4-8 | Đã chuẩn bị `release/` (zip mã nguồn + `run.sh`, bản PyInstaller macOS arm64) | **Người dùng cần tạo Release trên GitHub và quay video** (máy không có `gh`/`ffmpeg`) |
