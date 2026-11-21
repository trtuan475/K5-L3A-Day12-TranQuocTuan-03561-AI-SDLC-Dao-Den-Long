# Retro: Đảo Đèn Lồng (Day 12 AI SDLC)

## 1. Số liệu tổng hợp
| Phase | Nội dung chính | Test cuối phase | Token ước tính | Kết quả |
|---|---|---|---|---|
| 1 | PRD-0, contract v1.0, lõi tất định, headless, Ursina | 32 | ~150k | Đạt mọi AC, bot thắng |
| 2 | Số chuẩn, 3 Đêm, lướt/rơi/Gió Lạc/Bùa/gió/pause, UI đầy đủ | 50 | ~250k | Đạt AC headless; UI có vài mục chưa kiểm chứng |
| 3 | Change request: dầu đèn, `drain`, thắng lúc bình minh | 63 | ~120k | Đạt; có ADR + CHANGELOG |
| 4 | Bench/soak, bảng xếp hạng, tiếp cận, đóng gói | 70 | ~150k | bench 115 FPS / p1 60; soak 0 crash |
| **Tổng** | | | **~670k token** (một phiên Claude Code, không dùng agent phụ) | |

Bench (Apple M2 Pro): avg 115 FPS, p1-low 60, p95 9.9 ms, load 0.84 s. Headless chạy trọn một Đêm trong ≤ 1.6 s. Soak 10 Đêm mất 0.7 s, RSS không tăng.

## 2. Điều hiệu quả
- **Tách lõi sim tất định (stdlib) khỏi Ursina ngay từ Phase 1.** Nhờ vậy, Phase 2–3 viết lại luật mà không đụng tới render. Test headless chạy trong 3 s. Bản 3D cho kết quả trùng khớp con số với headless (tick 2944, 1260 điểm ở Phase 1).
- **Viết spec, giả định và AC trước khi code.** Mỗi lần test đỏ đều có tiêu chí để đối chiếu, nên phân biệt được "code sai" với "test sai".
- **Lưu thời gian và dầu bằng số nguyên tick.** Không có lỗi số thực. So sánh "đúng 30" là chính xác.
- **Vá file bằng script có `assert`** (thay vì sửa tay nhiều chỗ). Nếu đoạn gốc không khớp thì script fail ngay, nên tránh được sửa sai chỗ.
- **`verify.sh` sinh toàn bộ bằng chứng** và ghi commit hash vào báo cáo. Bằng chứng luôn khớp với tag.

## 3. Điều không hiệu quả
- **Bot làm bằng chứng tốn nhiều vòng chỉnh** (né Bóng Mực, điều hướng tầng/cầu, châm dầu) mà vẫn chỉ thắng được Đêm 1. Một scenario thắng ngắn cho mỗi Đêm sẽ rẻ hơn.
- **Gỡ lỗi chụp ảnh với Ursina** (cửa sổ bị đóng, offscreen thiếu UI, `size=` làm mất lớp UI, `look_at` làm lăn camera, ánh sáng làm tối màu). Mỗi lỗi chỉ lộ ra khi **xem ảnh**, không lộ ra trong log.
- Hai lần ghi lại cả `play.py` tốn token. Nên tách module UI sớm hơn.

## 4. Những lần AI sai và cách phát hiện
| Loại | Ví dụ | Phát hiện bằng | Thay đổi harness |
|---|---|---|---|
| Lệch 1 tick (lặp lại 3 lần) | bất tử 121 tick, choáng/hồi lướt kiểm tra sai tick | test đỏ + đọc output headless | Quy tắc mô hình tick trong AGENTS.md |
| Scenario thiếu dọn dẹp | Bùa Gió mặc định làm test cầu đo 7.2 m/s | test đỏ (52 ≠ 49) | Quy tắc "xóa mọi thực thể mặc định" |
| Hiểu sai hệ quả của luật mới | Đèn vừa thắp lại thành mục tiêu châm dầu | test CLI đỏ | Ghi vào AGENTS.md |
| API bịa hoặc sai | `color.lerp`, `ISLAND_RADIUS` đã bị xóa | crash khi chạy | Chạy thật sau mỗi thay đổi UI |
| Bằng chứng nói quá | Ghi "đã kiểm tra tay" khi chưa ai kiểm tra (Phase 2) | tự rà lại trước khi gắn tag | Quy tắc trong skill `verify`: "đánh dấu chưa kiểm chứng" |
| Hiệu năng | bench ban đầu 60 FPS, sát ngưỡng | số đo trong bench.json | Cache trạng thái, dùng setter Panda3D trực tiếp (lên 115 FPS) |

## 5. Harness nào giúp nhiều nhất
1. **`scripts/verify.sh` + skill `verify`.** Một lệnh chạy hết test, scenario, tất định, timing, rồi ghi báo cáo kèm commit. Đây là nguồn bằng chứng cho cả 4 phase.
2. **AGENTS.md có các quy tắc rút ra từ lỗi thật** (mô hình tick, dọn scenario, dầu dùng số nguyên). Mỗi quy tắc đều sinh ra từ một lỗi lặp lại.
3. **Stop hook chặn kết thúc khi test đỏ.** Ít khi kích hoạt, vì test được chạy trước mỗi commit, nhưng nó là chốt chặn cuối.
4. CI GitHub Actions chạy `verify.sh` khi push (chỉ cần stdlib).

## 6. Token và cách tiết kiệm
- Tổng khoảng 670k token (ước tính theo độ dài phiên). Không dùng subagent. Chỉ đọc tài liệu lab một lần.
- Test headless chạy nhanh (2–3 s), nên vòng sửa không cần nhiều lượt.
- Chỉ xem 2–3 ảnh mỗi lần thay vì toàn bộ.
- Lãng phí lớn nhất: chỉnh bot và gỡ lỗi chụp ảnh (ước tính khoảng 25% tổng).

## 7. Nếu làm lại
- Tách `play.py` thành các module (world / hud / menus) ngay từ Phase 2.
- Viết scenario thắng ngắn cho mỗi Đêm thay vì cố làm bot giỏi.
- Thêm test tự động cho phần UI logic (Flow, rebinding) bằng cách tách khỏi Ursina.
- Hỏi trợ giảng sớm về các giả định rủi ro (B1 điểm xuất phát Đêm 3, B4 `spawning`, C1 `wander`).
