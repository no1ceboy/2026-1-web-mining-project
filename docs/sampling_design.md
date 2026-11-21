# Thiết kế lấy mẫu theo lịch sử người dùng

## Mục tiêu và phạm vi

Thay cách lấy 100 review rời rạc/game bằng **thu thập lịch sử công khai của một cohort người dùng được định nghĩa từ dữ liệu train**. Catalog có 100 game; số review/game không bị ép bằng nhau. Mục tiêu khoảng 10.000 review là mục tiêu lập kế hoạch, không phải lý do để cắt rời lịch sử hoặc chọn người vì họ có nhiều review tương lai.

Phải phân biệt ba điều:

- Thu thập thêm những review thật của cùng một người sẽ bổ sung cạnh graph thật.
- Chọn cohort có lịch sử train đủ dài giúp đặt một bài toán warm-start có thể đánh giá.
- Việc cohort không còn người một tương tác là hệ quả của định nghĩa cohort, không chứng minh toàn bộ Steam đã hết thưa hoặc người dùng bình thường có nhiều lịch sử hơn.

Đối tượng nghiên cứu mới là **những reviewer có ít nhất ba game tích cực trong train, có lịch sử công khai có thể thu thập đủ trong ngân sách, thuộc catalog được công bố**. Không áp dụng kết luận cho cold-start, toàn bộ Steam hoặc toàn bộ người chơi.

## Quy trình v3

1. **Đóng băng catalog và thời gian trước khi huấn luyện.** Dùng 98 app đã được audit là game từ v1; thay Path of Exile 2 và FINAL FANTASY XIV Online do appdetails chưa xác minh được bằng Divinity: Original Sin 2 (`435150`) và Fallout 76 (`1151340`). Hai app thay thế được kiểm tra metadata trực tiếp. Không thay game theo model/test metrics.
2. **Tìm ứng viên bằng API trong quá khứ.** Lấy tối đa 100 review tích cực tiếng Anh/game, chỉ trong phần train. Yêu cầu timestamp tạo và lần chỉnh sửa cuối đều trước cutoff. Không dùng `author.num_reviews` hiện tại, tương tác test, sentiment tương lai hoặc tổng số review tương lai để chọn người.
3. **Ưu tiên bằng bằng chứng train.** Người xuất hiện ở nhiều game trong các seed record train được xét trước; cùng mức được sắp theo SHA-256 và seed cố định. Đây là cách tăng hiệu suất tìm active reviewers, không phải chọn theo test outcome. Danh sách và các game seed được lưu bằng user hash.
4. **Lấy lịch sử public profile.** Đọc các trang review công khai, kiểm tra robots, phân trang, bỏ trùng theo review ID, lưu tiến độ. Giữ các review trong catalog. Trang riêng tư, lỗi parse hoặc lịch sử vượt giới hạn trang không được giả định là lịch sử đầy đủ. Không dùng login, cookie cá nhân hay vượt kiểm soát truy cập.
5. **Định nghĩa cohort từ train.** Cần ít nhất ba game tích cực khác nhau có thông tin khả dụng trước cutoff. Giữ lịch sử của người được chọn, bao gồm review tiêu cực, ngắn và rỗng. Không yêu cầu người đó phải có validation/test target; không chạy all-time k-core rồi mới chia tập.
6. **Tạo hai luồng dữ liệu.** Luồng tương tác giữ nhãn recommendation hợp lệ, bất kể độ dài hay ngôn ngữ text. Luồng opinion train chỉ nhận text đủ dài, nhận diện là tiếng Anh và đã khả dụng trước cutoff. Thiếu opinion thì model phải dùng fallback đã thống nhất.
7. **Audit coverage trước model.** Đếm user/item/target thật theo từng cửa sổ, ứng viên warm và game đã review bị loại. Không dùng số raw review hoặc độ lớn connected component để suy ra số test users.

Quota ở bước tìm seed chỉ dùng để khám phá ứng viên. Nó không phải số đếm đưa thẳng vào Popularity hoặc phép ước lượng positive rate toàn Steam. Kể cả sau khi bỏ quota trong dataset, Popularity vẫn là positive count trong cohort có điều kiện; không phải độ phổ biến toàn nền tảng. Không tuyên bố có trọng số inverse-probability khi xác suất được chọn không được biết.

Bộ lọc off-topic của API chỉ được áp dụng ở discovery. Lịch sử public không tự kế thừa bộ lọc đó; phiên bản này chưa xác minh được mọi off-topic/received-for-free flag cho các record lịch sử. Không được mô tả toàn bộ cohort là đã được Steam lọc spam hoặc review bomb.

## Thời gian và độ chính xác

Config được lưu tại [steam_history_sampling_v3.json](../configs/steam_history_sampling_v3.json).

| Giai đoạn | Khoảng thời gian UTC |
| --- | --- |
| Khung quan sát | 01/01/2020 đến trước 21/11/2026 |
| Train và xác định cohort | Trước 01/01/2024 |
| Validation | Năm 2024 |
| Refit trước test | Lịch sử hợp lệ trước 01/01/2025 |
| Test | 01/01/2025 đến trước 21/11/2026 |

Đây là bài toán lịch sử có horizon dài, không phải dự đoán phiên chơi tiếp theo trong thời gian thực. Khoảng test dài tăng cơ hội quan sát tương tác nhưng có preference drift, thay đổi thị trường và censoring; phải ghi trong báo cáo. Chủ sở hữu shared evaluator cần review hợp đồng này trước khi chốt thí nghiệm cuối. Các file split được đánh dấu là proposed contract, không âm thầm thay evaluator chung.

API cung cấp timestamp chính xác cho seed. Public profile thường chỉ hiển thị ngày và có thể bỏ năm nếu là năm hiện tại. Dataset ghi `timestamp_precision`; không gọi timestamp proxy theo ngày là thời gian chính xác đến giây.

- Với ngày public không rõ múi giờ, lấy khoảng có thể xảy ra từ UTC-day-start trừ 14 giờ tới cộng 38 giờ. Chỉ nhận một record vào lịch sử nếu bound trên của lần chỉnh sửa đã trước cutoff; loại vùng biên không chắc chắn.
- Seed khớp review ID, app, nhãn và khoảng ngày có thể dùng epoch chính xác từ API cho **tương tác**. Điều này không làm text public được coi là khả dụng sớm hơn bound riêng của nó.
- Collector hiện giữ timestamp của mọi seed review khi discovery mới chạy từ đầu. Pilot v2/v3 đã thu trước phần mở rộng evidence này giữ timestamp chi tiết của seed đầu tiên mỗi user và danh sách game seed; builder xử lý tương thích, không tự tạo timestamp chính xác cho các seed còn thiếu evidence.
- `available_after_utc` áp dụng cho nhãn/tương tác. `text_available_after_utc`, nếu có, áp dụng cho text; nếu không có thì dùng bound chung.
- Target có lần chỉnh sửa hiển thị ở ngày sau ngày tạo bị loại, vì không thể chắc nhãn hiện tại là nhãn khi tạo review.
- Nếu UI không hiển thị edit date, phiên bản này giả định chưa sửa. Đây là giả định cần kiểm tra, không phải cam kết từ API. Ảnh chụp năm 2026 cũng không khôi phục được profile đã xóa, nội dung cũ hoặc trạng thái public trong năm 2024.

Vì vậy cohort là retrospective sample dưới điều kiện khả dụng hiện tại. Việc không chọn theo future positives không loại được hoàn toàn survivorship/nonresponse bias của nguồn. Nếu môn học yêu cầu ground truth lịch sử chính xác hơn, cần nguồn có version history hoặc một dataset lịch sử đã audit; không được bỏ qua cờ độ chính xác.

## Xử lý các vấn đề dữ liệu

| Vấn đề cũ | Chính sách mới | Điều còn phải kiểm chứng |
| --- | --- | --- |
| Hầu hết user chỉ có một game trong mẫu | Thu thập thêm lịch sử thật, cohort cần >=3 positive training games | Công bố cả phân bố trước lọc; không gọi cohort là toàn Steam |
| 100 review/game làm méo số đếm | Dataset cuối lấy theo người, không ép số dòng/game | Popularity vẫn có giới hạn do cohort/frame có điều kiện |
| Mỗi game bao phủ khoảng thời gian khác nhau | Áp dụng cùng cutoff và bound khả dụng cho tất cả game | Báo cáo warm items và cold-item exclusions |
| Rỗng/ít chữ | Giữ cạnh tương tác, flag riêng cho text | Không tự động gọi review ngắn là spam |
| Đa ngôn ngữ | Graph giữ tương tác; opinion train dùng English detection | Detector có lỗi; cần human spot check |
| Slang, meme, sarcasm | Không tự gán aspect/sentiment; chuẩn bị human validation | Chưa được giải quyết bằng một ngưỡng độ dài |
| Review sửa sau cutoff | Dùng creation/edit provenance và text bound riêng | Không thể tái tạo bản cũ từ bản mới |
| Dữ liệu test lọt vào cohort | Chọn dựa trên train; không bắt buộc có future target | Profile availability/size hiện tại vẫn gây nonresponse bias |
| Previously reviewed negative item bị gợi ý lại | Xuất seen-item masks gồm cả negative và review trước khung nghiên cứu | Tất cả model phải dùng cùng masks |
| Candidate set quá nhỏ làm Recall@20 tầm thường | Đếm số ứng viên thật và số target có >20 ứng viên | Chưa chạy ranking metrics khi coverage chưa đạt |
| Metadata thiếu | Hai app được thay trước discovery bằng app đã xác minh | Catalog là tập chọn thủ công, không đại diện ngẫu nhiên |

English detection dùng `langdetect==1.0.9`, seed cố định 42, chỉ chạy khi có ít nhất 20 token tách bằng khoảng trắng; ngưỡng score 0,9. Score không phải xác suất đúng đã được hiệu chuẩn. Các điều kiện này là heuristics kỹ thuật đăng ký trước pilot, chưa phải benchmark ngôn ngữ hay ABSA accuracy.

## Pilot và điều kiện bàn giao

Pilot hiệu chỉnh [v2](../outputs/steam_history_v2/sampling_report.md) dùng cutoff gần năm 2026 và kiểm tra 50 profile: phát hiện 122 review trong catalog, chọn 10 user với 60 review, nhưng không có target warm-start hợp lệ trong hai holdout. Không có model nào được huấn luyện hoặc ranking metric nào được xem để điều chỉnh protocol. Kết quả được giữ lại để giải thích vì sao v3 có horizon dài hơn và ưu tiên seed evidence trong train.

Kết quả v3 nằm ở [sampling_report.md](../outputs/steam_history_v3/sampling_report.md) và [sampling_audit.json](../outputs/steam_history_v3/sampling_audit.json). Không viết “đã có 10.000 review mới” hoặc “100 game đã có trong cohort” nếu bảng số liệu chưa đạt. 100 game là **catalog**, số game quan sát được phải báo cáo riêng.

Pilot v3 thực tế đã chạy trên 100 profile theo thứ tự bằng chứng train: 92 lịch sử được quan sát đủ, sáu vượt trần trang, hai không khả dụng. Thu được 875 review trong catalog trước lọc; cohort có 54 người, 554 review và 95 game quan sát được. Train có 334 cạnh tích cực; validation có 22 target users, test có 23; tập ứng viên của các target nằm trong khoảng 69–86 game. Có 85 text candidates tiếng Anh khả dụng trong train. Đây là bằng chứng pipeline hoạt động và có target thật, chưa đạt planning gate 500/100/100 và chưa phải thí nghiệm ranking có đủ độ chắc chắn.

Không có positive user trùng giữa các complete profile của pilot và quota snapshot v1; vì vậy không đưa ra so sánh “98% giảm còn X% trên cùng nhóm người”. Tỷ lệ degree của cohort/seed-prioritized sample và quota sample đo các population khác nhau. Các review mới là quan sát thật được bổ sung qua lịch sử, nhưng kết luận phải giới hạn ở cohort đã công bố.

Các mục tiêu vận hành của đợt lấy mẫu này:

- 500 người có ít nhất ba positive training games.
- Mỗi holdout có ít nhất 100 người đủ điều kiện và hơn 20 ứng viên để Recall@20 không bao phủ hết catalog của họ.
- Khoảng 10.000 review, giữ block lịch sử thay vì cắt về đúng số dòng.
- Tối đa 2.500 HTTP attempts, 2.000 profile ứng viên và 10 trang/profile. Dừng có báo cáo khi chạm giới hạn.

Đây là mục tiêu lập kế hoạch của nhóm, không phải ngưỡng thống kê phổ quát hay yêu cầu được xác nhận từ giảng viên. Chưa đạt thì ghi rõ, tiếp tục trong ngân sách đăng ký hoặc cân nhắc nguồn khác; không thay cutoff theo Recall/NDCG hay chỉ giữ người có target để làm đẹp kết quả.

Giữ 10.000 dòng chính xác đồng thời giữ đầy đủ lịch sử và chọn cohort độc lập tương lai không phải một ràng buộc nên ép bằng cách bỏ lẻ dòng. Phiên bản này ưu tiên cohort xác định từ train và block lịch sử; số dòng là mục tiêu mềm. Nếu cần trần lưu trữ cứng, phải thiết kế quy tắc từ train trước một đợt mới và công bố phần bị censoring.

Đã chuẩn bị thêm [config full-scale](../configs/steam_history_sampling_full_v1.json), chưa chạy trong pilot thiết kế: cùng protocol v3 nhưng nhắm 1.000 người train-eligible, trần 4.000 profile/6.000 request và vẫn xem 10.000 review là mục tiêu mềm. Đây là ngân sách có thể kéo dài nhiều giờ, không phải cam kết đủ 10.000 dòng hay đủ target. Planning gate của template vẫn yêu cầu tối thiểu 500 cohort users và 100 người mỗi holdout; mục tiêu thu thập 1.000 user được báo cáo riêng. Không tăng trần tự động khi hết ngân sách.

## Chạy và chạy tiếp

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-sampling.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/steam_history_sampler.py --max-profiles-per-run 100
.\.venv\Scripts\python.exe scripts/build_history_dataset.py
.\.venv\Scripts\python.exe scripts/export_history_spotcheck.py
```

Lệnh sampler mặc định dùng config v3 và thư mục `outputs/steam_history_v3`. Chạy lại lệnh để tiếp tục; mỗi lượt tối đa 100 profile mới nếu có cờ trên. Bỏ cờ để chạy tới cohort target, user cap hoặc HTTP budget. Khoảng nghỉ 2 giây/request; 2.500 request tương ứng khoảng 83 phút chỉ tính khoảng nghỉ, chưa tính network/retry/parse. Không xem đó là thời gian đã benchmark hoặc tự động tăng ngân sách nếu chưa đủ dữ liệu.

Đợt full-scale có output riêng, không sửa config rồi tiếp tục trộn vào pilot:

```powershell
.\.venv\Scripts\python.exe scripts/steam_history_sampler.py --config configs/steam_history_sampling_full_v1.json --output-dir outputs/steam_history_full_v1 --max-profiles-per-run 100
.\.venv\Scripts\python.exe scripts/build_history_dataset.py --output-dir outputs/steam_history_full_v1
```

Seed discovery cũng checkpoint theo game; lịch sử checkpoint theo trang. HTTP 429/5xx/lỗi mạng có retry và backoff giới hạn. Retry-After quá dài hoặc không parse được ở public endpoint sẽ dừng thay vì thử sớm. Trạng thái dừng trong manifest phải được đọc trước khi gọi kết quả là hoàn tất. Chỉ chạy một sampler cho mỗi output directory.

## File bàn giao

Các file dưới `outputs/steam_history_v3/`:

| File | Công dụng |
| --- | --- |
| `sampling_manifest.json`, `sampling_requests.jsonl` | Config, trạng thái, metadata, request audit; user hash thay cho lookup ID |
| `seed_manifest.json` | Seed review IDs, thời gian API và bằng chứng game train dùng để sắp ưu tiên |
| `discovered_reviews.jsonl` | Dữ liệu thu được trước lọc cohort, gồm cả lịch sử chưa đủ điều kiện |
| `cohort_reviews.jsonl` | Các review trong khung nghiên cứu của cohort; không phải tập market ngẫu nhiên |
| `train_reviews.jsonl` | Lịch sử hợp lệ trước validation cutoff; graph chỉ dùng positive_interaction=true |
| `refit_reviews.jsonl` | Lịch sử hợp lệ trước test cutoff |
| `validation_targets.jsonl`, `test_targets.jsonl` | Target đủ điều kiện theo proposed coverage protocol |
| `seen_items_before_validation.jsonl`, `seen_items_before_test.jsonl` | Loại game từng review, kể cả negative và lịch sử trước năm 2020 |
| `opinion_train_candidates.jsonl` | Text tiếng Anh đủ điều kiện và khả dụng trước cutoff, chưa có gold aspect labels |
| `review_quality.jsonl` | Flag rỗng, độ dài, language detector và text availability |
| `split_manifest.json` | Hợp đồng đề xuất, hashes, cohort IDs và temporal policy |
| `sampling_audit.json`, `sampling_report.md` | Bằng chứng acquisition/coverage và trạng thái planning gate |
| `source_spotcheck_template.csv` | 20 mẫu chưa có nhãn người, để kiểm tra nguồn/ngày/ngôn ngữ/nội dung |

Các trường cốt lõi giữ review_id, user_id SHA-256, item_id, title/text, feedback và provenance. Khác API snapshot: helpful_votes có thể null vì không suy diễn con số không được parse; language có thể unknown; timestamp cần đọc cùng timestamp_precision và bound khả dụng. Source URL chỉ công bố platform root; đường dẫn profile/lookup ID không được đưa vào repo. Shared loader phải hỗ trợ hợp đồng này; không dùng checker dành riêng cho API snapshot để giả định tất cả record có epoch chính xác và nhãn English từ Steam.

## Phần bạn cần tự kiểm tra

Lệnh export tạo CSV với các cột nhãn người để trống và một HTML riêng trong `%LOCALAPPDATA%/WebMining/private_sampling/`. Mở HTML đó để đối chiếu nguồn của 20 mẫu, rồi điền date check, ngôn ngữ, nội dung có ý nghĩa và độ trung thực của text vào CSV. Không upload HTML riêng lên GitHub. Đây là data spot check, chưa thay cho 200–300 nhãn aspect/sentiment có overlap độc lập.

Lookup ID chỉ được giữ trong bộ nhớ và file được Windows DPAPI mã hóa ở ngoài repo. Resume dùng cùng máy/tài khoản Windows; người khác vẫn có thể dùng dataset đã công bố nhưng không giải mã được state này. Không copy state hoặc private HTML vào project để làm cho resume “tiện” hơn. Khi cần chạy từ đầu trên máy khác, dùng output version mới và lấy lại candidate IDs qua nguồn public.

Phần kỹ thuật tự động hóa không được tự điền nhãn human hoặc khẳng định UI edit policy chính xác tuyệt đối. Sau spot check và sau khi coverage đạt mục tiêu, cần thống nhất split/evaluator dùng chung trước khi so sánh bốn model của dự án.

Nguồn kỹ thuật: [Steamworks GetAppReviews](https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english), [Steam Community robots](https://steamcommunity.com/robots.txt), [Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata). Các nguồn mô tả giao diện/điều kiện kỹ thuật; chúng không chứng minh dataset của nhóm có đủ chất lượng hoặc mọi timestamp public đều chính xác.
