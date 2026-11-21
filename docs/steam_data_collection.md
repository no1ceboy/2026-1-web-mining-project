# Steam Data Collection — Hướng dẫn vận hành và bàn giao

Phần triển khai này chỉ phụ trách thu thập, provenance, kiểm tra chất lượng và độ kết nối. Dùng Python **3.10 trở lên**, chỉ thư viện chuẩn, không cần pip, GPU, Steam login hay API key.

Đầu vào bàn giao cho các bước sau là `outputs/steam_expanded_pilot.jsonl`, đi kèm `outputs/steam_expanded_manifest.json`. Đây là snapshot review đã chuẩn hóa schema; chưa phải dữ liệu đã cleaning hoặc chia train/validation/test. Đọc `outputs/steam_overlap_report.md` trước khi dùng để đánh giá mô hình.

## Chạy từ thư mục repo

```powershell
cd "C:\HUST\Web Mining\2026-1-web-mining-project"
python scripts/steam_crawler.py --check-access
python scripts/steam_crawler.py
python scripts/steam_metadata_audit.py
python scripts/steam_overlap_report.py
```

`--check-access` chỉ kiểm tra API và schema trên hai review, không lưu nội dung hoặc SteamID. Crawler dùng API mới với `input_json` và enum số theo [tài liệu Steamworks](https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english). Không dùng endpoint appreviews cũ.

File `configs/steam_crawl_v0.json` cố định 20 app ID, tối đa 100 review/game, 50 review/trang, tối đa 5 trang/game. Khoảng nghỉ tối thiểu giữa request là 2 giây. Mẫu gồm 5 game pilot cũ và 15 game PC chọn thủ công; không phải mẫu ngẫu nhiên hay đại diện toàn Steam. Store audit xác minh ID, tên chính thức và loại app; không thu thập toàn bộ metadata.

## Dừng và chạy tiếp

Để thử dừng có kiểm soát sau một trang:

```powershell
python scripts/steam_crawler.py --max-pages-per-run 1
python scripts/steam_crawler.py
```

Có thể nhấn Ctrl+C khi đang chạy rồi chạy lại cùng lệnh. Chương trình đọc cursor và ID đã lưu từ output, tiếp tục phần chưa hoàn thành. Chạy lại một mẫu đã đủ mục tiêu sẽ không gửi thêm request crawl. Chỉ chạy **một crawler cho mỗi thư mục output** tại một thời điểm.

Sau mỗi trang, chương trình ghi JSONL bằng file tạm + thay thế nguyên tử, sau đó mới lưu manifest. Nếu tiến trình bị tắt giữa hai bước, lần chạy tiếp có thể tải lại trang cũ; ID đã lưu được dùng để bỏ trùng. Manifest lưu checksum dữ liệu và lịch sử các lần chạy từ lúc cơ chế run_history được thêm vào.

Mặc định tối đa 3 lần thử lại sau lỗi mạng/HTTP 429/5xx, dùng backoff 2/4/8 giây và tôn trọng Retry-After. Nếu máy chủ yêu cầu chờ hơn 60 giây, chương trình trả quyền điều khiển; chờ theo Retry-After rồi chạy lại. HTTP 401/403 hoặc lỗi truy cập kéo dài sẽ dừng lượt crawl để tránh tiếp tục gửi request tới các game khác. Không đổi mạng, proxy hay vượt kiểm soát truy cập tự động.

Nếu đạt giới hạn trang, hết dữ liệu hoặc cursor không tiến lên, chương trình ghi rõ trạng thái; không khẳng định đủ 100 review. Mã thoát 0 tương ứng hoàn tất hoặc dừng theo ngân sách trang; mã 1 tương ứng bị ngắt, bị chặn hoặc chưa đạt mục tiêu.

## Phiên bản dữ liệu khác

Không sửa config rồi tiếp tục một snapshot cũ: chương trình kiểm tra checksum config và từ chối trộn cấu hình. Khi cần một lần thu thập mới, dùng thư mục khác:

```powershell
python scripts/steam_crawler.py --output-dir outputs/steam_expanded_v1 --check-access
python scripts/steam_crawler.py --output-dir outputs/steam_expanded_v1
python scripts/steam_metadata_audit.py --output-dir outputs/steam_expanded_v1
python scripts/steam_overlap_report.py --output-dir outputs/steam_expanded_v1
```

Giữ nguyên giới hạn đã thống nhất; việc mở rộng ngoài pilot cần nhóm chốt mục tiêu trước. Snapshot online mới có thể khác do review mới, review chỉnh sửa và cache của API, ngay cả khi config giống nhau. Các file `steam_pilot.jsonl` và `steam_pilot_manifest.json` gốc không bị ghi đè.

## Các file đầu ra

| File trong outputs/ | Ý nghĩa |
| --- | --- |
| `steam_access_check.json` | Kết quả truy cập API và kiểm tra schema trên máy/mạng chạy lệnh |
| `steam_expanded_pilot.jsonl` | Review đã chuẩn hóa, mỗi dòng một JSON |
| `steam_expanded_manifest.json` | Config, cursor, tiến độ từng game, số lỗi/bỏ trùng, checksum và lịch sử chạy |
| `steam_crawl_requests.jsonl` | Mỗi request attempt: tham số, thời điểm, HTTP status, kết quả và retry; không lưu response gốc |
| `steam_metadata_audit.json` | Đối chiếu ID/tên/loại app với public Steam store |
| `steam_overlap_stats.json` | Thống kê chất lượng và graph ở dạng máy đọc được |
| `steam_overlap_report.md` | Báo cáo để gửi nhóm, so sánh pilot cũ và đề xuất nguồn |

Review giữ đúng schema pilot: ID review, SHA-256 user ID, ID/tên game, thời gian tạo và crawl, feedback gốc, positive_interaction, title/text, language, helpful_votes và source_url. SteamID gốc chỉ được dùng trong bộ nhớ để hash, không được ghi ra log hay response file.

Giữ cả hai nhãn feedback và cả review rỗng; report đếm rõ số rỗng để Member 2 quyết định cách xử lý. Bản ghi thiếu định danh, timestamp, nhãn Boolean hoặc sai ngôn ngữ bị loại với lý do trong manifest. Không tự suy diễn feedback bị thiếu thành false. Source language được kiểm tra theo API, chưa chạy mô hình xác định ngôn ngữ độc lập.

## Kiểm tra

```powershell
python -m unittest discover -s tests -v
```

Các test offline kiểm tra hash/nhãn tiêu cực, phân trang và giới hạn mẫu, pause/resume, replay sau crash, thay đổi config, cursor không tiến, dừng khi bị từ chối truy cập, HTTP 429/Retry-After và graph có đáp án biết trước. Test dùng dữ liệu tổng hợp, không gọi mạng. Live crawl được ghi riêng trong log/manifest; không mô tả lỗi giả lập là lỗi đã xảy ra thật.

## Những việc cần bạn phối hợp với nhóm

1. Đọc `outputs/steam_overlap_report.md`, gửi JSONL + manifest cho Member 2 và báo cáo graph cho Member 3. Không gửi lời hứa rằng mẫu này đủ để đánh giá mô hình.
2. Trao đổi với trưởng nhóm về đề xuất Steam/Amazon. Chưa có ngưỡng chấp nhận overlap được nhóm chốt; các số đếm hiện tại là bằng chứng để quyết định, không phải kết quả từ evaluator.
3. Nếu crawl sẽ chuyển sang máy/mạng khác, người chạy ở đó cần kiểm tra `--check-access` lại. Kết quả máy này không xác nhận mạng khác.
4. Mã nguồn và snapshot được quản lý trên nhánh `main`. Với các cập nhật tiếp theo, thống nhất phiên bản dữ liệu và quy trình review với nhóm.

Member 2 sở hữu cleaning/split/evaluator, Member 3 sở hữu model, Member 4 sở hữu opinion mining. Không tự tạo một split khác hay gắn nhãn aspect dựa trên voted_up. Mỗi người cần làm phần annotation độc lập theo phân công thực tế của nhóm; crawler không tạo nhãn người dùng giả.

Lưu ý dữ liệu theo thời gian: timestamp của review là thời gian tạo; nội dung tải hôm nay có thể đã được sửa sau đó. Nhóm cần chính sách xử lý edit-time hoặc snapshot lịch sử trước khi dùng text để tuyên bố thí nghiệm không có rò rỉ tương lai. Với chỉ 20 game, Recall@20 dễ trở thành chỉ số tầm thường vì K bao phủ toàn bộ tập ứng viên.
