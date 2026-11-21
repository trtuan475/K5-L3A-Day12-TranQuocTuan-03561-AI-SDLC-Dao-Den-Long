# Nhật ký dùng AI và đánh giá

Công cụ: Claude Code (Claude Opus 5.5) trong VS Code. Harness: [AGENTS.md](../../AGENTS.md), Stop hook chạy test, skill `verify`, CI.

## Phase 1

**Cách làm:** đọc PRD-0 → viết [spec + giả định + AC](phase-1-spec.md) trước khi code → lõi `sim.py` + `headless.py` → 32 test theo AC → bot sinh bằng chứng → bản 3D Ursina → `verify.sh` → tag.

**Token/chi phí (ước tính):** khoảng 150k token cho cả phiên Phase 1, phần lớn rơi vào việc gỡ lỗi chụp ảnh của Ursina. Cách đã tiết kiệm:
- Chỉ đọc README, SUBMISSION, RUBRIC, GUIDE một lần.
- Viết lõi trong một lần, sửa bằng các patch nhỏ.
- Test headless không cần Ursina nên chạy dưới 1 giây.

**Lỗi của AI và cách phát hiện:**
| Lỗi | Phát hiện | Sửa / chỉnh harness |
|---|---|---|
| Bất tử thực tế kéo dài 121 tick thay vì 120 (lệch 1 tick) | Đọc output headless thử: hai lần bị chạm cách nhau 121 tick | Sửa thứ tự giảm bộ đếm. Thêm `test_invuln` kiểm đúng `invuln_s × 60` |
| `time_left_s` không bị trừ ở bước kết thúc game (lệch công thức của contract) | `test_win` đỏ (350 ≠ 349) | Trừ đồng hồ ngay đầu mỗi bước. Ghi vào A9 |
| Test choáng kiểm sai tick (do lỗi của chính AI khi viết test) | `test_pulse_stun_push` đỏ; đối chiếu lại mô hình tick | Sửa test, ghi lý do trong comment. Thêm quy tắc mô hình tick vào AGENTS.md |
| Dùng API không tồn tại `color.lerp` (Ursina 7) | Chạy bản 3D bị crash | Tự viết hàm `mix` |
| `camera.look_at` làm camera bị lăn | Xem ảnh chụp: cột đèn nghiêng | Đặt `camera.rotation` theo pitch/yaw |
| Font thiếu glyph ♥ ←→ | Cảnh báo trong log + ảnh | Đổi sang ký tự ASCII |

**Đánh giá Phase 1 (viết cuối Phase 1):**
- Đạt toàn bộ AC1–AC11 (xem [TRACE](../proof/phase-1/TRACE.md)).
- Rủi ro lớn nhất là bộ test ẩn hiểu khác các giả định A1–A11, ví dụ pulse trừ vào đom đóm đang mang, hoặc đom đóm rơi thì biến mất. Tất cả đã được ghi lại và khai báo nhất quán.
- Cần chỉnh: bot thắng quá dễ (khoảng 50 giây), có thể cần cân bằng lại nếu ticket sau yêu cầu. Bước chụp ảnh nên chạy sớm hơn để tránh mất nhiều vòng gỡ lỗi.

## Phase 2 (Ticket-02, contract v1.1)

**Cách làm:** viết [phase-2-spec](phase-2-spec.md) trước, gồm bảng thay đổi so với Phase 1, giả định B1–B15 và AC P2-1…P2-17. Sau đó làm theo thứ tự ưu tiên điểm:
1. Lõi sim viết lại theo đúng 12 bước của ticket, kèm `maps.py`.
2. 50 test, trong đó mỗi tính năng mới có ít nhất 1 scenario.
3. Bot điều hướng 3 Đêm.
4. UI (menu, HUD, pause/cài đặt, âm thanh, bảng màu).
5. `verify.sh`, ảnh chụp, đo FPS.

**Token/chi phí (ước tính):** khoảng 250k token. Phần tốn nhất là viết `sim.py`/`play.py` (2 lần ghi cả file) và 3 vòng chỉnh bot. Cách đã tiết kiệm:
- Dùng các patch nhỏ thay vì đọc lại cả file.
- Không chạy agent phụ.
- Test headless chạy trong 2 giây, nên vòng sửa nhanh.

**Lỗi của AI và cách phát hiện:**
| Lỗi | Phát hiện | Sửa / chỉnh harness |
|---|---|---|
| 3 test do AI viết lệch 1 tick (choáng, hồi lướt, recoil); lần thứ hai gặp loại lỗi này | Test đỏ; đối chiếu với mô hình tick | Sửa test, không sửa code. Thêm quy tắc "timer N tick đặt ở p thì hoạt động ở p..p+N−1" vào AGENTS.md |
| Helper scenario quên xóa Bùa Gió mặc định, nên test cầu tre đo tốc độ 7.2 thay vì 6 | `test_bridge_walk` đỏ (52 ≠ 49) | `empty()` xóa cả `charms`. Thêm quy tắc "scenario phải xóa mọi thực thể mặc định" vào AGENTS.md |
| Bot né Bóng Mực tự lao xuống biển | Thống kê `falls` khi chạy bot | Thêm `_safe_dir` (nhìn trước 2.5 m) |
| `unlit_shader` + `AmbientLight` làm tối toàn bộ màu chuẩn (áo Mây ra màu xám) | Xem ảnh chụp | `setLightOff()` cho các phần cần đúng màu; chỉ địa hình chịu ánh sáng môi trường |
| Ảnh pause chụp trước khi menu kịp render | Xem ảnh: không có menu | Chụp sau 2 frame |
| Dùng thuộc tính `ISLAND_RADIUS` đã bị xóa khỏi sim (play.py cũ) | ImportError khi chạy | Viết lại play.py |

**Đánh giá Phase 2:**
- Đạt: mọi AC headless P2-1…P2-15 có test xanh; FPS khoảng 120 (yêu cầu ≥ 30); cả Đêm chạy headless dưới 1 s (giới hạn 30 s); tất định ở cả 3 Đêm.
- Ảnh hưởng tới Phase 1: số liệu và luật điểm đổi theo chuẩn, nên các test Phase 1 bị ảnh hưởng đã được viết lại. `--night 1` vẫn chạy được mọi scenario dạng v1.0.
- Rủi ro: các giả định B1 (xuất phát Đêm 3 ở (0,0,−30)), B4 (`spawning` 60 tick, `wander` 2 m/s) và B5 (cách đo chênh cao) có thể khác test ẩn.
- Chưa đạt trọn: bot chưa thắng được Đêm 2/3, nên chưa có ảnh màn Bình Minh. Phần lưu cài đặt, đồng hồ đỏ khi ≤ 30 s, âm thanh và màn Bình Minh **chưa được kiểm chứng** (không có test tự động, chưa ai chơi tay). Cần kiểm tra tay trước Phase 4.

## Phase 3 (Ticket-03 "Đèn cạn dầu", contract v1.2), khoảng 30 phút

**Cách làm:** viết ADR 0001, CHANGELOG và spec C1–C6 **trước** khi sửa code. Sau đó sửa sim trong một bản vá (fuel dùng số nguyên 1/60, `drain`, thắng lúc bình minh, sức chứa, điểm mới). Tiếp theo cập nhật 6 test bị luật mới thay thế (kèm lý do) và thêm 13 test mới. Cuối cùng là bot châm dầu, UI tối thiểu (thanh dầu, mù màu, HUD sức chứa) và verify.

**Token/chi phí (ước tính):** khoảng 120k token. Tiết kiệm nhờ vá bằng script có `assert` (fail ngay nếu đoạn gốc không khớp), không đọc lại file lớn, và chỉ xem 3 ảnh.

**Lỗi của AI và cách phát hiện:**
| Lỗi | Phát hiện | Sửa / chỉnh harness |
|---|---|---|
| Scenario thắng CLI bấm Tương tác nhiều lần tại chỗ: đèn vừa sáng (99.98 dầu) lại thành đèn nhận được gần nhất, nên các lần bấm sau chuyển thành châm dầu | Test CLI đỏ (1 ≠ 3 đèn) | Thiết kế lại scenario. Ghi quy tắc vào AGENTS.md |
| 3 test mới đặt sai khoảng cách/số tick (drain 2.5 m > 2 m, safe zone 3 tick, sức chứa 2 ≠ 3) | Test đỏ, đối chiếu luật | Sửa test (code đúng) |
| Bấm lần hai khi nút vẫn đang giữ: không có cạnh false→true | `IndexError` trong `test_refuel` | Thả nút trước khi bấm lại |
| Test CLI chỉ chạy 200 tick trong khi bình minh ở tick 240 | Test đỏ | Đổi `time_left_s` = 3 |

**Đánh giá Phase 3:**
- Đạt mọi AC headless P3-1…P3-10 (63 test). Có ADR, CHANGELOG; không test nào bị skip.
- Test Phase 1–2 không bị thay thế vẫn xanh.
- FPS khoảng 119. Cả Đêm headless chạy ≤ 1.6 s.
- Bot thắng Đêm 1 theo luật bình minh.
- Chưa kiểm chứng: thanh dầu/nhấp nháy/đèn xẹp chưa có ảnh; biểu tượng ⚠ và việc lưu cài đặt mù màu chưa được kiểm tra.
- Rủi ro: C1 (đi về đèn tắt gần nhất với tốc độ 2 m/s) và C2 (`fuel_drain` ghi theo từng con) có thể khác test ẩn.
