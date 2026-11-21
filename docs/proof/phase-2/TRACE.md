# Phase 2: Truy vết Ticket-02 → bằng chứng

Chạy lại:
- `bash scripts/verify.sh phase-2` sinh [REPORT.md](REPORT.md).
- `python3 play.py --demo --shots docs/proof/phase-2/shots` sinh [shots/](shots/).
- `python3 play.py --bench 30 --night 3 --out docs/proof/phase-2/fps.txt` sinh [fps.txt](fps.txt).

Test được nêu theo tên trong [tests/test_sim.py](../../../tests/test_sim.py) và [tests/test_cli.py](../../../tests/test_cli.py). Kết quả nằm trong [unittest.log](unittest.log).

| Yêu cầu Ticket-02 | AC | Kiểm chứng (scenario headless / test) | Kết quả |
|---|---|---|---|
| Số chuẩn: chạy 6 m/s, nhảy 7/−20, chỉ nhảy khi chạm đất | P2-1 | `test_std_speed_and_yaw`, `test_std_jump` | Đạt |
| Lướt 14 m/s / 12 tick / hồi 90 tick tính từ lúc bắt đầu; theo hướng quay mặt; trên không giữ độ cao | P2-1 | `test_dash`, `test_air_dash_keeps_height` | Đạt |
| Đom đóm: 20 điểm ban đầu, +1 mỗi 240 tick, trần 30, nhặt theo XZ ≤ 1 và chênh cao ≤ 1.5 | P2-2 | `test_mote_pick_height`, `test_mote_schedule`, `test_initial_state` | Đạt |
| Đèn: chi phí 10, nạp nhiều lần, chọn gần nhất rồi id nhỏ hơn, bán kính 2.0 | P2-3 | `test_deposit_multi_and_score`, `test_interact_radius` | Đạt |
| Vùng an toàn 6 m: chặn ở mép; đẩy ra trong ≤ 30 tick, không gây sát thương | P2-4 | `test_safe_block`, `test_safe_evict` | Đạt |
| Tỏa Sáng: tốn 3, cầu 3D 5 m từ chân + 0.8, choáng 120, đẩy 4 m/15 tick, trùng vị trí thì đẩy +X, hồi 180 | P2-5 | `test_pulse_3d_radius_push_stun`, `test_pulse_cost_and_cooldown`, `test_pulse_coincident_pushes_plus_x` | Đạt |
| Bóng Mực: 5 trạng thái, phát hiện 12/bỏ đuổi 18, tốc độ 4/4.5, lịch sinh 300 + k·khoảng, tối đa 6/8/10 | P2-6 | `test_detect_and_lose`, `test_chase_speed`, `test_spawn_schedule`, `test_spawn_max` | Đạt |
| Bị đánh: −1 lửa, rơi floor(n/2) ra vành 1.5–2.5 m (TTL 480), bất tử 90, recoil 2 m/60 tick, tối đa 1 hit/tick theo id | P2-7 | `test_hit`, `test_invuln_90` | Đạt |
| Rơi khỏi đảo: −1 lửa, mất hết đom đóm, chờ 60 tick, hồi sinh với bất tử; hết lửa thì thua ngay | P2-8 | `test_fall_and_respawn`, `test_fall_last_flame_loses` | Đạt |
| Thắng/thua cuối tick, thắng được cả ở tick hết giờ, điểm chuẩn | P2-9 | `test_win_score`, `test_win_on_last_tick`, `test_dawn`, scenario `tests/scenarios/win.json` | Đạt |
| Đêm 2: hai đảo, cầu không lan can, bục phóng (~1.4 s, đáp đảo kia) | P2-10 | `test_bridge_walk`, `test_off_bridge_falls`, `test_bounce_pad`; ảnh `n2_*` | Đạt |
| Đêm 3: tầng/vách/dốc/bục lên tầng 2/tháp không leo được/gió 2 m/s × 5 s mỗi 30 s | P2-11 | `test_cliff_blocks`, `test_ramp_up`, `test_pad_to_tier2_and_tower`, `test_wind`; ảnh `n3_*` | Đạt |
| Gió Lạc: idle→chase→flee→removed, cướp min(3, n), pulse trúng chase thì chạy, trúng flee thì thả đồ, lịch 1200 | P2-12 | `test_chase_steal_flee_removed`, `test_idle_when_poor`, `test_pulse_chase_flees_without_steal`, `test_pulse_flee_drops`, `test_drifter_schedule` | Đạt |
| Bùa Gió: 7.2 m/s, lướt không hồi chiêu, 600 tick, xuất hiện lại sau 2700 tick, vị trí chuẩn | P2-13 | `test_charm`, `test_default_charm_positions` | Đạt |
| Pause: tick tăng, sim_tick và đồng hồ đứng yên, state `paused`, sự kiện paused/resumed | P2-14 | `test_pause`; ảnh `n1_pause.png` | Đạt |
| Contract v1.1: các trường snapshot mới, `--night 1..3`, `night_start`, tất định, cả Đêm ≤ 30 s | P2-15 | `test_v11_snapshot_fields`, `test_determinism`, REPORT (khoảng 0.4–0.7 s mỗi Đêm) | Đạt |
| Chuỗi 3 Đêm: menu → giới thiệu (Ông Đăng) → chơi → kết quả → Đêm kế; Bình Minh; thua thì chơi lại | P2-16 | Ảnh `n*_0_intro`, `n*_4_result`; code `Flow` trong play.py | Một phần: menu/intro/kết quả có ảnh; màn Bình Minh **chưa kiểm chứng** (bot không thắng được Đêm 3) |
| Pause menu: Tiếp tục / Chơi lại Đêm / Cài đặt / Về menu; cài đặt âm lượng và độ nhạy được lưu | P2-16 | Ảnh `n1_pause.png`; lưu ở `~/.dao_den_long_settings.json` | Pause menu có ảnh; phần lưu cài đặt **chưa kiểm chứng** |
| Âm thanh: nhạc nền + 10 hiệu ứng + đếm ngược 10 s | P2-16 | `scripts/gen_sfx.py` → `assets/sfx/*.wav`; hook sự kiện trong `Flow.update` | File âm thanh sinh được; việc phát âm thanh **chưa kiểm chứng** |
| HUD đầy đủ theo bố cục; đồng hồ đỏ nhấp nháy khi ≤ 30 s; nhắc "E - Nạp ánh sáng"; mũi tên chỉ đèn | P2-16 | Ảnh `n*_1_play`, `n*_2_mid` | Đạt, riêng đồng hồ đỏ khi ≤ 30 s **chưa kiểm chứng** |
| Bảng màu chuẩn; ánh sáng môi trường 0.15 + 0.55 × tiến độ | P2-16 | `PAL` trong play.py (hex đúng từng giá trị); `AmbientLight`; các phần cần đúng màu bỏ qua ánh sáng | Đạt |
| ≥ 30 FPS trung bình ở 1280×720 | P2-17 | [fps.txt](fps.txt): Đêm 3 đạt 119.8 FPS, Đêm 1 đạt 119.1 FPS (Apple Silicon, vsync tắt) | Đạt |

**Giới hạn ghi nhận trung thực:**
- Bot làm bằng chứng chỉ thắng được Đêm 1 (seed 2). Ở Đêm 2 và Đêm 3, bot thua với số chuẩn: thắp 3/6 và 2/7 đèn.
- Việc thắng Đêm 2/3 được kiểm chứng bằng scenario (`test_win_*` dùng logic chung), chưa có lượt chơi thắng trọn vẹn của bot.
- Tính năng của Phase 1 vẫn giữ nguyên: rerun các test Phase 1 đã viết lại theo số chuẩn.
