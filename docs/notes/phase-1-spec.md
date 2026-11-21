# Phase 1: Spec, giả định, tiêu chí nghiệm thu

Nguồn: PRD-0 và Test Contract v1.0 (lab board, tab Phase 1).

## Quyết định kiến trúc
- **Python 3 + Ursina.** Máy có sẵn Python 3.11 và không có Node.js.
- Lõi logic `lantern_island/sim.py` chỉ dùng thư viện chuẩn và chạy tất định. Lõi này không import Ursina.
  Cả `headless.py` lẫn `play.py` (bản 3D) đều gọi chung lõi này, nên test headless kiểm tra đúng logic mà người chơi đang chơi.
- Toàn bộ thời gian trong lõi được đếm bằng **tick nguyên** (1/60 giây) để tránh sai số số thực. Kết quả chỉ được làm tròn 3 chữ số thập phân khi xuất ra.

## Tuning (khớp `game.contract.json`)
| Khóa | Giá trị | Ghi chú |
|---|---|---|
| player_speed | 6.0 m/s | |
| carry_capacity | 10 | |
| lantern_cost | 5 | Số đom đóm cần để thắp 1 đèn |
| lantern_count_night1 | 5 | L1..L5 nằm trên vòng tròn bán kính 25 m, L1 ở (0,0,25), các đèn cách nhau 72° |
| pickup_radius | 1.0 m | |
| interact_radius | 2.5 m | |
| pulse_cost | 1 | Trừ vào **số đom đóm đang mang** |
| pulse_radius | 6.0 m | |
| night1_duration_s | 300 | |
| flames | 3 | "Máu" của Mây |
| invuln_s | 2.0 | |
| hit_drop_ratio | 0.5 | |
| pulse_stun_s | 2.0 | |
| pulse_push_m | 3.0 | |
| pulse_cooldown_s | 1.0 | |
| safe_radius | 5.0 m | Áp dụng quanh **đèn đã thắp** |
| shade_speed | 3.0 m/s | |
| shade_hit_radius | 1.0 m | |
| fall_enabled | false | Đảo có rào vô hình ở bán kính 40 m |
| score | mote 10, lantern 100, stun 20, second_left 1, flame_left 50 | |

## Giả định (chỗ PRD-0 mơ hồ)
- A1. **Ánh sáng = đom đóm đang mang.** Mỗi lần tỏa sáng tốn `pulse_cost` đom đóm. Nếu mang ít hơn mức này, hoặc đang trong cooldown, thì không có gì xảy ra và không phát sự kiện.
- A2. **Nạp đèn:** khi `interact` chuyển false→true, game chọn đèn **chưa thắp** gần nhất nằm trong `interact_radius`, rồi nạp `min(carried, lantern_cost - deposited)`. Phần còn lại người chơi vẫn giữ. Nếu nạp đủ thì phát `lantern_lit`.
- A3. **Bị chạm:** áp dụng khi không đang bất tử và có Bóng Mực *không bị choáng* nằm trong `shade_hit_radius`. Mây mất 1 flame, đánh rơi `floor(carried × hit_drop_ratio)`, rồi được bất tử `invuln_s`. Số đom đóm rơi **biến mất** và không nằm lại trên đất.
- A4. **Bóng Mực** luôn đuổi người chơi (trạng thái `chase`), trừ lúc bị choáng (`stunned`). Chúng không vào được hình tròn `safe_radius` quanh đèn đã thắp: nếu bước tới bị lấn vào thì bị đẩy ra tới mép. Bóng Mực bay với tâm ở y = 1.0.
- A5. **Tỏa sáng:** Bóng Mực trong `pulse_radius` bị choáng `pulse_stun_s` và bị đẩy ra xa người chơi `pulse_push_m` theo mặt phẳng XZ. Danh sách `stunned_ids` có thể rỗng. Mỗi Bóng Mực bị choáng được cộng `per_stun`.
- A6. **Điểm:** `per_mote` cho mỗi lần nhặt, `per_lantern` cho mỗi lần thắp đèn. Khi **thắng** được cộng thêm `per_second_left × floor(time_left_s)` và `per_flame_left × flames`. Thua thì không có thưởng.
- A7. **Hết giờ:** khi `time_left_s` về 0 mà chưa thắp hết đèn thì thua với lý do `dawn`.
- A8. **Mặc định của màn** (khi không có scenario): 30 đom đóm sinh ngẫu nhiên theo seed. Mỗi con bị nhặt sẽ hồi sinh sau 5 giây ở vị trí ngẫu nhiên. Đầu màn có 2 Bóng Mực, sau đó cứ 30 giây thêm 1 con, tối đa 6 con, sinh ở mép đảo. Nếu `random_motes`/`random_shades` là false thì tắt việc sinh và hồi sinh tương ứng.
- A9. **Thứ tự xử lý trong một bước:** input → trừ đồng hồ 1 tick → di chuyển/nhảy → nhặt → nạp đèn (thắng thì dừng) → tỏa sáng → Bóng Mực di chuyển và sinh thêm → va chạm (hết flame thì dừng) → kiểm tra hết giờ.
- A10. Khi game kết thúc giữa chừng, headless ghi thêm một snapshot cuối (nếu tick đó chưa có snapshot), sau đó mới ghi dòng `end`.
- A11. Lỗi tham số hoặc file JSON sai định dạng (tick không tăng nghiêm ngặt, sai kiểu dữ liệu, `--night` khác 1) thì thoát với mã 2. Lỗi khác thì thoát với mã 1.

## Tiêu chí nghiệm thu → cách kiểm chứng
| ID | Tiêu chí | Kiểm chứng |
|---|---|---|
| AC1 | Snapshot tick 0: người chơi ở (0,0,0), có 5 đèn, state `playing` | test `test_initial_state` |
| AC2 | Di chuyển đúng tốc độ, xoay theo cam_yaw, chuẩn hóa vector | `test_move_speed`, `test_cam_yaw`, `test_normalize` |
| AC3 | Nhặt trong bán kính, không vượt sức chứa | `test_pickup*` |
| AC4 | Nạp/thắp đèn, sự kiện deposit/lantern_lit | `test_deposit_and_lit` |
| AC5 | Bóng Mực đuổi, không vào safe_radius | `test_shade_chase`, `test_safe_radius` |
| AC6 | Bị chạm: mất flame, rơi đom đóm, bất tử | `test_hit*` |
| AC7 | Pulse: tốn ánh sáng, choáng, đẩy lùi, cooldown | `test_pulse*` |
| AC8 | Thắng `all_lit`, thua `no_flames`, thua `dawn`, điểm thưởng | `test_win`, `test_lose_*` |
| AC9 | Tính tất định: cùng đầu vào thì output giống hệt nhau | `test_determinism` + `scripts/verify.sh` |
| AC10 | Mã thoát 0/2, dòng end luôn là dòng cuối | `test_cli_*` |
| AC11 | Chơi được có giao diện 3D: HUD, chơi lại | Ảnh chụp/clip trong `docs/proof/phase-1/` |
