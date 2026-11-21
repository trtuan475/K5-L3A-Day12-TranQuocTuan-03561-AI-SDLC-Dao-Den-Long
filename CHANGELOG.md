# Changelog

## Phase 4: v1.0.0, Contract v1.3 (Ticket-04 "Bình minh")
### Added
- `bench_cmd` = `python3 play.py --bench-mode` (cảnh chuẩn 200 Bóng Mực / 100 đom đóm, camera bay vòng, ghi bench.json).
- `soak_cmd` = `python3 soak.py` (10 Đêm trong một tiến trình, ghi soak.json).
- Bảng xếp hạng cục bộ (top 10, `~/.dao_den_long_leaderboard.json`), màn hình xem từ menu, lưu điểm sau Bình Minh hoặc khi thua; `python3 play.py --export-leaderboard out.json`.
- Tiếp cận: đổi phím (phát hiện trùng, khôi phục mặc định, được lưu), phụ đề và chỉ báo (Bóng Mực xuất hiện kèm mũi tên ở mép, gió, 10 s cuối, đèn sắp hết dầu), giảm chuyển động (tắt rung camera và chớp màn hình), chữ ≥ 18 px và tùy chọn chữ lớn ×1.25.
- `Game(bench=True)`: tắt spawn, sát thương, nhặt, hao dầu và kết thúc Đêm.
### Changed
- Tối ưu render: cache trạng thái Bóng Mực, dùng setter Panda3D trực tiếp (bench từ 60 lên 115 FPS).
### Breaking
- Không có thay đổi luật gameplay. `contract_version` thành `1.3`.

## Phase 3: Contract v1.2 (Ticket-03 "Đèn cạn dầu")
### Breaking changes
- `contract_version` thành `1.2`. `night*_duration_s` đổi thành 240 / 270 / 300 (trước là 300 / 330 / 360).
- **Không còn thắng sớm.** `game_over.reason` có giá trị `dawn_survived` khi thắng; `all_lit` bị bỏ. Thắng khi còn sống ở tick bình minh và số đèn sáng ≥ ceil(0.6 × n).
- **Điểm:** +5 mỗi đom đóm nạp (trước là +10), +100 khi thắp lần đầu, +40 khi thắp lại, +5 mỗi Bóng Mực trúng Tỏa Sáng (+15 nếu nó đang `drain`). Khi thắng: mỗi đèn sáng được 50 + floor(fuel), mỗi Ngọn Lửa còn lại được +50. **Bỏ** thưởng theo thời gian còn lại.
- Đèn đang sáng nhận thêm đom đóm (châm dầu) và có thể tắt (`lantern_out`). Thắp lại cần 5 đom đóm.
- Vùng an toàn chỉ có khi fuel ≥ 30. Bóng Mực có trạng thái mới là `drain`.
- Sức chứa = 10 + 2 × successful_lights (tối đa 20), không còn cố định 10.
- Snapshot: đèn có thêm `fuel`, `ever_lit`, `relit_count`; `player.capacity`. Sự kiện mới: `refuel`, `lantern_out`, `fuel_drain`. `lantern_lit` có thêm `relight`.
### Test đã thay đổi (có lý do)
- `test_win_score`, `test_win_on_last_tick`: viết lại thành `test_dawn_win_*`, vì luật thắng sớm bị thay thế.
- `test_deposit_multi_and_score`: điểm mỗi đom đóm đổi từ 10 sang 5.
- `test_initial_state`: thời lượng các Đêm đổi.
- `test_safe_block`: giờ phải đặt fuel ≥ 30, vì vùng an toàn phụ thuộc vào dầu.
- `tests/scenarios/win.json`: không thể thắng ở tick 9 nữa, nên đổi thành kịch bản sống tới bình minh với 3/5 đèn sáng.

## Phase 2: Contract v1.1 (Ticket-02)
- Số liệu và bản đồ chuẩn, 3 Đêm, lướt, rơi khỏi đảo, Gió Lạc, Bùa Gió, gió, pause; thắng/thua xét cuối tick. Xem docs/notes/phase-2-spec.md.

## Phase 1: Contract v1.0
- Phiên bản đầu tiên.
