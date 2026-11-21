# Đảo Đèn Lồng

> **Video demo:** _(sẽ thêm ở Phase 4, Release `v1.0.0`)_
> Lab Day 12, AI SDLC · Trần Quốc Tuấn · 03561 · Tài liệu gốc của lab: [docs/lab/](docs/lab/README.md)

Game 3D góc nhìn thứ ba qua 3 Đêm. Mây, người giữ đèn nhỏ tuổi đội nón lá, gom đom đóm để thắp lại các Đèn Lồng Lớn trên Đảo Bến, Đảo Cau và Đảo Chuông trước bình minh, đồng thời né Bóng Mực và Gió Lạc trong sương đen.

## Cài đặt và chạy (macOS / Linux, Python ≥ 3.9)

```bash
python3 -m pip install -r requirements.txt   # cài Ursina (chỉ cần cho bản 3D)
python3 play.py                              # menu → Đêm 1 → 2 → 3 (có thể vào thẳng: --night 2)
bash scripts/verify.sh phase-2               # chạy toàn bộ test + sinh bằng chứng
```

Chế độ headless (Test Contract **v1.1**, chỉ dùng thư viện chuẩn, không cần GPU):

```bash
python3 headless.py --seed 1 --night 1|2|3 --ticks 600 --out out.jsonl [--scenario s.json] [--inputs i.json] [--snapshot-every 10]
python3 -m unittest discover -s tests        # chỉ chạy test
python3 play.py --bench 30 --night 3         # đo FPS ở 1280×720
```

## Điều khiển

| Phím | Hành động |
|---|---|
| W A S D | Di chuyển (theo hướng camera) |
| Chuột / ← → | Xoay camera (độ nhạy chỉnh trong Cài đặt) |
| Space | Nhảy |
| Shift | Lướt |
| E | Nạp đom đóm vào đèn ở gần |
| F hoặc click trái | Tỏa Sáng (tốn 3 đom đóm) |
| Esc / P | Tạm dừng: Tiếp tục / Chơi lại Đêm / Cài đặt / Về menu |

## Luật và cách tính điểm (số chuẩn Ticket-02)

- Nhặt đom đóm bằng cách đi qua chúng (mang tối đa 10). Mỗi đèn cần 10 đom đóm, nạp nhiều lần được.
- Bóng Mực đuổi theo khi Mây ở trong 12 m. Bị chạm thì mất 1 Ngọn Lửa và rơi một nửa số đom đóm ra xung quanh (nhặt lại được trong 8 s).
- Đèn đã sáng tạo vùng an toàn bán kính 6 m mà Bóng Mực không vào được.
- Rơi xuống biển mây thì mất 1 Ngọn Lửa và toàn bộ đom đóm, sau đó hồi sinh ở điểm xuất phát.
- Gió Lạc (Đêm 2 và 3) cướp tối đa 3 đom đóm. Tỏa Sáng trúng nó thì nó bỏ chạy hoặc thả lại đồ.
- Bùa Gió giúp chạy nhanh hơn và lướt không cần hồi chiêu trong 10 s.
- Đêm 3 có gió mạnh mỗi 30 s; lá bay báo trước 2 s.
- **Thắng** khi mọi đèn đều sáng. **Thua** khi hết Ngọn Lửa hoặc tới bình minh (300 / 330 / 360 s).

| Sự kiện | Điểm |
|---|---|
| Mỗi đom đóm **nạp** vào đèn | +10 |
| Mỗi đèn thắp | +100 |
| Mỗi Bóng Mực trúng Tỏa Sáng | +5 |
| Khi thắng: mỗi giây còn lại | +2 |
| Khi thắng: mỗi Ngọn Lửa còn lại | +50 |

Tổng điểm là tổng điểm các Đêm đã thắng. Mọi con số nằm trong [game.contract.json](game.contract.json) và game đọc trực tiếp từ file đó. Các giả định: [Phase 1](docs/notes/phase-1-spec.md), [Phase 2](docs/notes/phase-2-spec.md).

## Kiến trúc

```
lantern_island/sim.py    lõi logic tất định (stdlib), theo đúng thứ tự xử lý của Ticket-02; dùng chung cho headless và 3D
lantern_island/maps.py   bản đồ chuẩn của 3 Đêm (mặt đất, đèn, điểm sinh, bục phóng, bùa)
headless.py              CLI Test Contract v1.1 (chỉ I/O)
play.py                  Ursina: menu, giới thiệu Đêm, HUD, pause/cài đặt, âm thanh, render
lantern_island/autoplay.py  bot dùng để sinh bằng chứng (chơi qua đúng định dạng inputs)
scripts/gen_sfx.py       tự tổng hợp nhạc và hiệu ứng âm thanh (assets/sfx)
```

## Bằng chứng và ghi chép

- Phase 2: [TRACE](docs/proof/phase-2/TRACE.md) · [REPORT](docs/proof/phase-2/REPORT.md) · [FPS](docs/proof/phase-2/fps.txt) · [ảnh](docs/proof/phase-2/shots/)
- Phase 1: [TRACE](docs/proof/phase-1/TRACE.md) · [REPORT](docs/proof/phase-1/REPORT.md) (ở tag `phase-1`)
- Nhật ký AI và đánh giá: [docs/notes/ai-log.md](docs/notes/ai-log.md)
- Harness AI:
  - [AGENTS.md](AGENTS.md) (CLAUDE.md trỏ tới file này)
  - Stop hook [.claude/settings.json](.claude/settings.json) chặn kết thúc khi test đỏ
  - Skill [verify](.claude/skills/verify/SKILL.md)
  - CI [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Sáng tạo của tôi

Mọi phần thêm đều nằm trong `play.py`, nên output headless không bị ảnh hưởng:
- **Lời Ông Đăng** riêng cho từng Đêm ở màn giới thiệu.
- **Vùng an toàn hiển thị:** vòng sáng 6 m quanh đèn đã thắp, để người chơi thấy rõ chỗ trú.
- **Phản hồi trạng thái:** Mây nhấp nháy khi bất tử, quầng đèn nhỏ của Mây lớn dần theo số đom đóm đang mang, Bóng Mực phồng dần khi đang `spawning`, và đom đóm rơi sẽ nhấp nháy trong 2 s cuối trước khi tan.
- **Âm thanh tự tổng hợp:** nhạc nền ngũ cung, cùng tiếng gió báo trước cơn gió ở Đêm 3.

Bằng chứng phần cũ vẫn đúng: `scripts/verify.sh` chạy hoàn toàn không cần Ursina và tất cả mục đều PASS ([REPORT](docs/proof/phase-2/REPORT.md)).
