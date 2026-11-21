# Phase 4: Ticket-04 "Bình minh: phát hành v1.0.0": AC và giả định

## Giả định (D1…)
- D1. `load_ms` được đo từ dòng lệnh đầu tiên của `play.py` (ngay sau khi interpreter khởi động, khoảng vài chục ms) tới khung hình đầu tiên của cảnh bench.
- D2. `peak_mem_mb` lấy từ `getrusage(RUSAGE_SELF).ru_maxrss`, tức đỉnh RSS của cả tiến trình. Giá trị này ≥ đỉnh trong lúc đo, nên là cận trên an toàn.
- D3. Trong cảnh bench, Bóng Mực theo luật `wander` bình thường (C1: đi về đèn tắt gần nhất) và vẫn có thể chuyển sang `chase` khi Mây ở trong 12 m, nhưng không gây sát thương. Mây không được điều khiển.
- D4. "Rải đều trên đảo" nghĩa là phân bố đều theo diện tích (bán kính lấy theo căn bậc hai) trong 3–39 m, dùng seed 42. Đom đóm rải trong 2–38 m.
- D5. Soak: "hướng di chuyển ngẫu nhiên" là một góc đều trong [0, 2π). Các nút được gửi mỗi tick dưới dạng boolean theo xác suất, và chỉ kích hoạt khi chuyển false → true.
- D6. Tên trên bảng xếp hạng dùng `\w{3,12}` (Unicode), nên chấp nhận cả tiếng Việt có dấu (điểm cộng). Nếu bằng điểm thì xếp theo `achieved_at` tăng dần.
- D7. Có thể lưu điểm sau màn Bình Minh, hoặc sau khi thua ở bất kỳ Đêm nào (nút "Lưu điểm"). Điểm lưu là tổng điểm các Đêm đã thắng trong lượt chơi.
- D8. Phím Esc luôn mở tạm dừng (phòng trường hợp đổi phím Tạm dừng sang phím khó bấm). Phím đổi được là `pause` (mặc định là P).

## Acceptance criteria → bằng chứng
| ID | Tiêu chí | Kiểm chứng |
|---|---|---|
| P4-1 | Cảnh bench chuẩn: 200 Bóng Mực `wander`, 100 đom đóm, L1–L3 sáng với fuel 100, tắt spawn/sát thương/nhặt/hao dầu/kết thúc | `test_scene`, `test_bench_rules_off`; [bench.json](../../bench.json); ảnh `shots/bench.png` |
| P4-1b | bench.json: avg ≥ 60, p1 ≥ 30, load ≤ 10000 (số tự đo) | bench.json |
| P4-2 | Soak 10 Đêm: crashes = 0, mem_end ≤ 1.2 × mem_start | `test_soak_short`; [soak.json](../../soak.json) |
| P4-3 | Bảng xếp hạng: tên hợp lệ, top 10, sắp xếp, lưu bền, export đúng thứ tự | `test_names`, `test_sort_ties_top10_persist`, `test_export_cli`; ảnh `ui_leaderboard`, `ui_name_entry` |
| P4-4 | Đổi phím cho mọi hành động, báo phím trùng, khôi phục mặc định, được lưu | Ảnh `ui_keybinds`, `ui_keybind_clash` |
| P4-5 | Phụ đề: Bóng Mực xuất hiện (+ mũi tên ở mép), gió, 10 s cuối, đèn < 30 | Ảnh `ui_play_captions` (dòng chữ do tour tự gọi); code hook sự kiện |
| P4-6 | Giảm chuyển động (tắt rung camera và chớp màn hình); chữ ≥ 18 px; tùy chọn chữ lớn ×1.25 | Code `ui_text` (scale ≥ 1, tức 0.025 × 720 = 18 px); ảnh `ui_settings` |
| P4-7 | Contract v1.3 (`bench_cmd`, `soak_cmd`) | `test_contract` |
| P4-8 | README, CHANGELOG (4 phase), CREDITS, LICENSE, Release v1.0.0, retro, video | Các file trong repo; Release và video do người dùng tạo |
