# Đảo Đèn Lồng

> **Video demo:** _(sẽ thêm ở Phase 4, Release `v1.0.0`)_
> Lab Day 12, AI SDLC · Trần Quốc Tuấn · 03561 · Tài liệu gốc của lab: [docs/lab/](docs/lab/README.md)

Game 3D góc nhìn thứ ba. Mây, người giữ đèn nhỏ tuổi đội nón lá, chạy khắp Đảo Bến để gom đom đóm và thắp lại 5 Đèn Lồng Lớn trước bình minh, đồng thời né những Bóng Mực tím đen trong sương.

## Cài đặt và chạy (macOS / Linux, Python ≥ 3.9)

```bash
python3 -m pip install -r requirements.txt   # cài Ursina (chỉ cần cho bản 3D)
python3 play.py                              # chơi
bash scripts/verify.sh phase-1               # chạy toàn bộ test + sinh bằng chứng
```

Chế độ headless (Test Contract v1.0, chỉ dùng thư viện chuẩn, không cần GPU):

```bash
python3 headless.py --seed 1 --night 1 --ticks 600 --out out.jsonl [--scenario s.json] [--inputs i.json] [--snapshot-every 10]
python3 -m unittest discover -s tests        # chỉ chạy test
```

## Điều khiển

| Phím | Hành động |
|---|---|
| W A S D | Di chuyển (theo hướng camera) |
| Chuột / ← → | Xoay camera |
| Space | Nhảy |
| E | Nạp đom đóm vào Đèn Lồng Lớn ở gần |
| F hoặc click trái | Tỏa sáng: tốn 1 đom đóm, làm choáng và đẩy lùi Bóng Mực ở gần |
| R | Chơi lại |
| Esc | Khóa/mở chuột |

## Luật và cách tính điểm

- Đi qua đom đóm để nhặt (mang tối đa 10 con). Đứng gần một đèn chưa thắp rồi bấm E để nạp. Mỗi đèn cần 5 đom đóm.
- Bóng Mực đuổi theo Mây. Bị chạm thì mất 1 ngọn lửa (có 3 ngọn), rơi mất một nửa số đom đóm đang mang, và được bất tử 2 giây.
- Bóng Mực không vào được vùng sáng bán kính 5 m quanh đèn **đã thắp** (vòng tròn vàng trên mặt đất).
- **Thắng** khi thắp đủ 5 đèn. **Thua** khi hết ngọn lửa hoặc hết 5 phút (bình minh tới).

| Sự kiện | Điểm |
|---|---|
| Nhặt 1 đom đóm | +10 |
| Thắp 1 đèn | +100 |
| Làm choáng 1 Bóng Mực | +20 |
| Khi thắng: mỗi giây còn lại | +1 |
| Khi thắng: mỗi ngọn lửa còn lại | +50 |

Mọi con số đều nằm trong [game.contract.json](game.contract.json). Game đọc trực tiếp từ file này, nên số khai báo luôn trùng với số game đang dùng. `fall_enabled = false`: đảo có rào vô hình ở bán kính 40 m nên không thể rơi xuống. Các giả định khác xem [docs/notes/phase-1-spec.md](docs/notes/phase-1-spec.md).

## Kiến trúc

```
lantern_island/sim.py   lõi logic tất định (stdlib), dùng chung cho cả headless và bản 3D
headless.py             CLI theo Test Contract (chỉ I/O)
play.py                 bản 3D Ursina: render + map phím → input frame → Game.step()
lantern_island/autoplay.py  bot dùng để sinh bằng chứng (chơi qua đúng định dạng inputs)
```

Bản 3D chạy logic ở 60 tick/giây cố định, giống hệt headless. Bằng chứng: bot chơi seed 1 trong bản 3D thắng ở tick 2944 với 1260 điểm, trùng khớp với lần replay qua `headless.py` ([REPORT](docs/proof/phase-1/REPORT.md)).

## Bằng chứng và ghi chép

- Phase 1: [docs/proof/phase-1/TRACE.md](docs/proof/phase-1/TRACE.md) (yêu cầu → bằng chứng) · [REPORT.md](docs/proof/phase-1/REPORT.md) (sinh tự động) · [ảnh](docs/proof/phase-1/shots/)
- Spec và giả định: [docs/notes/phase-1-spec.md](docs/notes/phase-1-spec.md) · Nhật ký AI và đánh giá: [docs/notes/ai-log.md](docs/notes/ai-log.md)
- Harness AI: [AGENTS.md](AGENTS.md) (CLAUDE.md trỏ tới file này), Stop hook [.claude/settings.json](.claude/settings.json) chặn kết thúc khi test đỏ, skill [.claude/skills/verify](.claude/skills/verify/SKILL.md), CI [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Sáng tạo của tôi

Phase 1 tập trung làm lõi đúng. Phần thêm hiện chỉ là hình ảnh, nằm hoàn toàn trong `play.py` nên không ảnh hưởng tới output headless:
- Vùng an toàn quanh đèn đã thắp được vẽ thành vòng sáng vàng trên mặt đất, để người chơi thấy rõ chỗ trú.
- Mặt đảo chuyển dần từ tím đêm sang xanh ấm khi thắp thêm đèn, và sương mù cũng mỏng dần.
- Bóng Mực chuyển sang màu tím nhạt khi bị choáng. Mây nhấp nháy khi đang bất tử, và quầng sáng quanh đèn nhỏ của Mây lớn dần theo số đom đóm đang mang.

Bằng chứng phần cũ vẫn đúng: `scripts/verify.sh` chạy hoàn toàn không có Ursina và tất cả mục đều PASS.
