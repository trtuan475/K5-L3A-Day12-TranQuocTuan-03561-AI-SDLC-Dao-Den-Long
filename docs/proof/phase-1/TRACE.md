# Phase 1: Truy vết yêu cầu → bằng chứng

Chạy lại: `bash scripts/verify.sh phase-1` (sinh [REPORT.md](REPORT.md)) và `python3 play.py --demo --shots docs/proof/phase-1/shots` (sinh ảnh).

| Yêu cầu PRD-0 / Contract | AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| Màn Đêm 1, đảo tròn, 5 đèn, xuất phát (0,0,0) | AC1 | `test_initial_state` | [unittest.log](unittest.log) | Đạt |
| Đi lại, nhảy, camera 3D | AC2 | `test_move_speed`, `test_cam_yaw`, `test_normalize`, `test_jump`, `test_fence`; ảnh | [unittest.log](unittest.log), [shots/](shots/) | Đạt |
| Đom đóm rải rác, nhặt được | AC3 | `test_pickup_radius`, `test_pickup_capacity` | [unittest.log](unittest.log) | Đạt |
| Nạp ánh sáng để thắp đèn | AC4 | `test_deposit_and_lit`, `test_partial_deposit_and_edge`; scenario win | [runs/win_scenario.jsonl](runs/win_scenario.jsonl) | Đạt |
| Bóng Mực xuất hiện, đuổi; sợ đèn | AC5 | `test_shade_chase`, `test_safe_radius`; event `shade_spawned` | [runs/bot_seed1.jsonl](runs/bot_seed1.jsonl) | Đạt |
| Bị chạm mất máu | AC6 | `test_hit`, `test_invuln` | [unittest.log](unittest.log) | Đạt |
| Tỏa sáng xua Bóng Mực, tốn ánh sáng | AC7 | `test_pulse_stun_push`, `test_pulse_needs_light`, `test_pulse_cooldown` | [unittest.log](unittest.log) | Đạt |
| Thắng / thua / điểm | AC8 | `test_win`, `test_lose_no_flames`, `test_lose_dawn`; bot 3 seed thắng; người đứng yên thua | [REPORT.md](REPORT.md) | Đạt |
| Chơi Đêm 1 từ đầu tới thắng/thua | AC8 | Bot chơi màn mặc định qua `inputs.json`, replay bằng `headless.py` | [runs/](runs/) | Đạt |
| HUD, chơi lại sau thắng/thua | AC11 | Ảnh HUD + màn hình thắng có "Nhấn R để chơi lại"; phím R tạo `Game` mới | [shots/04_won.png](shots/04_won.png) | Đạt (R kiểm tra bằng tay) |
| Tất định | AC9 | `test_determinism`, `test_cli_determinism`, `cmp` hai lần chạy | [REPORT.md](REPORT.md) | Đạt |
| Mã thoát 0/2, dòng end | AC10 | `test_cli_*` | [runs/bad_inputs.stderr](runs/bad_inputs.stderr) | Đạt |
| Bản 3D dùng đúng logic headless | | Bot trong bản 3D: thắng ở tick 2944 với 1260 điểm, trùng với headless seed 1 | [shots/04_won.png](shots/04_won.png) | Đạt |
| Phong cách: đêm ấm, đảo sáng dần, tím đen = nguy hiểm, nón lá + đèn nhỏ | | Ảnh 01→04 | [shots/](shots/) | Đạt (đồ họa đơn giản) |

**Chưa làm / giới hạn:** không có âm thanh. Đồ họa dùng hình khối cơ bản. Việc chơi bằng tay (WASD, chuột, R) chỉ được kiểm tra bằng tay, không có test tự động cho phần input của Ursina.
