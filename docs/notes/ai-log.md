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

**Đánh giá Phase 1:**
- Đạt toàn bộ AC1–AC11 (xem [TRACE](../proof/phase-1/TRACE.md)).
- Rủi ro lớn nhất là bộ test ẩn hiểu khác các giả định A1–A11, ví dụ pulse trừ vào đom đóm đang mang, hoặc đom đóm rơi thì biến mất. Tất cả đã được ghi lại và khai báo nhất quán.
- Cần chỉnh: bot thắng quá dễ (khoảng 50 giây), có thể cần cân bằng lại nếu ticket sau yêu cầu. Bước chụp ảnh nên chạy sớm hơn để tránh mất nhiều vòng gỡ lỗi.
