# ADR 0001: Đèn có nhiên liệu, thắng bằng cách "giữ đảo sáng tới bình minh"

- Trạng thái: Chấp nhận (Phase 3, Ticket-03, Contract v1.2)
- Thay thế: luật "đèn đã sáng không nhận thêm", "Bóng Mực không bao giờ vào vùng an toàn", "thắng ngay khi tất cả đèn sáng", công thức điểm của Ticket-02

## Bối cảnh
Người chơi giỏi thắp hết đèn trong 2 phút rồi game kết thúc. Nhà thiết kế muốn có căng thẳng tới cuối Đêm: đèn có thể tắt, và mục tiêu là số đèn còn sáng ở tick bình minh.

## Quyết định
1. **Mô hình trạng thái đèn.** Mỗi đèn giữ `lit`, `fuel` (số nguyên đơn vị 1/60 dầu, tối đa 6000 = 100), `deposited`, `ever_lit`, `relit_count`. Có ba trạng thái logic:
   - `tắt-chưa-từng-sáng`: chi phí thắp 10.
   - `sáng`: fuel giảm 1 đơn vị mỗi tick, cộng thêm 5 đơn vị mỗi tick cho mỗi Bóng Mực đang `drain`.
   - `tắt-đã-từng-sáng`: chi phí thắp lại 5.
   Chuyển trạng thái: thắp thì fuel = 6000. Sau bước 2, đèn có fuel ≤ 0 thì tắt, `deposited = 0`, phát `lantern_out`.
   Vùng an toàn là thuộc tính suy ra `lit and fuel ≥ 30·60`, không lưu riêng, nên không thể lệch với fuel.
2. **Dầu dùng số nguyên** (1/60 đơn vị). Như vậy không có sai số số thực và việc so sánh "đúng 30" là chính xác. Chỉ làm tròn khi xuất ra (1 chữ số thập phân).
3. **Một lần Tương tác** chọn trong các đèn "nhận được" (chưa sáng, hoặc sáng nhưng chưa đầy dầu), gần nhất rồi id nhỏ hơn. Đèn chưa sáng thì nạp để thắp, đèn đang sáng thì châm dầu. Trong cả hai trường hợp, mỗi đom đóm được +5 điểm.
4. **Bóng Mực** thêm trạng thái `drain`. `wander` có mục tiêu theo thứ tự ưu tiên: đèn yếu (sáng, fuel < 30), rồi đèn tắt gần nhất, rồi điểm ngẫu nhiên. Trong 2 m quanh đèn yếu thì chuyển sang `drain`. Việc hút dầu tính ở bước 2 (cùng chỗ với hao tự nhiên). Các chuyển trạng thái ra khỏi `drain` xét ở bước 8.
5. **Thắng/thua chỉ xét ở bước 11.** Thứ tự là: hết lửa thì `no_flames`; nếu chưa, khi hết giờ thì so số đèn sáng với `ceil(0.6·n)` để ra `dawn_survived` hoặc `dawn`. Không còn kết thúc sớm vì thắp đủ đèn.
6. **Sức chứa** là giá trị suy ra từ `successful_lights` (đếm mỗi lần thắp thành công trong Đêm), không lưu riêng.

## Hệ quả
- Nhiều test của Phase 1–2 về điểm và thắng sớm không còn đúng: đã cập nhật hoặc xóa, có ghi lý do (xem CHANGELOG).
- Scenario v1.1 vẫn chạy được. Đèn `lit: true` không có `fuel` thì mặc định fuel = 100 và `ever_lit = true`.
- Bot làm bằng chứng phải biết châm dầu, nếu không đèn sẽ tắt trước bình minh.
