# Đánh giá kỹ thuật dự án Web Mining

Ngày đánh giá: 21/11/2026. Phạm vi: nội dung kế hoạch, mã nguồn có trên `main` trước đợt mở rộng, và kết quả snapshot `steam_100games_v1`. Đây là nhận định kỹ thuật, không phải điểm dự đoán của giảng viên; repo chưa có rubric chấm điểm chính thức. Công việc nằm trên nhánh riêng của các thành viên khác chưa được đánh giá.

## Nhận định

Đề tài có đủ chiều sâu để trở thành một đồ án môn học tốt cho nhóm bốn người. Câu hỏi so sánh link analysis với learned graph recommendation, rồi đo tác động của opinion mining, rõ ràng và có thể kiểm chứng. Điểm mạnh là thiết kế thí nghiệm và pipeline có nguồn gốc dữ liệu. Điểm yếu hiện tại là lấy mẫu chưa tạo đủ lịch sử người dùng cho câu hỏi recommendation. Việc tăng tổng số review chưa giải quyết được điều đó.

Không cần phát minh mô hình mới để có đồ án tốt. Dùng phương pháp đã công bố, xây hệ thống chạy được và đưa ra kết luận có kiểm chứng là mục tiêu phù hợp. Tuy nhiên, ghép các tên mô hình hoặc có giao diện gợi ý đẹp chưa đủ chứng minh phần nghiên cứu.

| Tiêu chí | Nhận định | Cơ sở và điều kiện |
| --- | --- | --- |
| Phù hợp môn Web Mining | Tốt | Thu thập dữ liệu web, phân tích liên kết user-game, opinion mining và recommendation; có thể ánh xạ rõ vào nội dung môn |
| Câu hỏi nghiên cứu | Tốt | Có baseline và ablation để kiểm tra phần opinion có thêm giá trị hay không |
| Độ mới về thuật toán | Vừa phải | PPR, LightGCN và weighted fusion là các hướng đã có; đóng góp là thực nghiệm, dữ liệu và phân tích |
| Độ khó tổng thể | Khoảng 7–8/10 | Thang chủ quan cho nhóm sinh viên: khó ở đánh giá công bằng, dữ liệu và validation NLP hơn là số request crawl |
| Chất lượng triển khai thu thập | Khá tốt cho pilot | Có giới hạn, versioning, hash ID, provenance, resume, log và test; còn hai app chưa xác minh được type qua store API |
| Phù hợp dữ liệu với personalized ranking | Yếu ở snapshot hiện tại | Phần lớn người dùng chỉ có một tương tác, số người đủ lịch sử rất nhỏ |
| Khả thi với bốn người | Có điều kiện | Giữ bốn cấu hình chính, chốt dữ liệu/split sớm, giới hạn demo và text mining |
| Bằng chứng về hiệu quả mô hình | Chưa có trên main | Chưa thấy shared evaluator, model, metric thực nghiệm hay opinion validation |

LightGCN học embeddings bằng lan truyền trên graph user-item; vì vậy cấu trúc lịch sử tương tác quan trọng đối với lựa chọn này. Đây là suy luận về tính phù hợp của dữ liệu dự án, không phải kết quả thử LightGCN trên snapshot. Tham khảo [bài báo LightGCN](https://arxiv.org/abs/2002.02126).

## Snapshot 10.000 review thực sự có gì?

Nguồn số liệu: [báo cáo](../outputs/steam_100games_v1/steam_overlap_report.md) và [JSON thống kê](../outputs/steam_100games_v1/steam_overlap_stats.json).

| Chỉ số | Kết quả |
| --- | ---: |
| Review / app được lấy mẫu | 10.000 / 100 |
| Review mỗi app | 100 |
| Người dùng duy nhất | 9.718 |
| Review tích cực / tiêu cực | 8.659 / 1.341 |
| Người review nhiều game, bất kỳ nhãn | 200 |
| Người có ít nhất 2 game tích cực | 169 |
| Người có ít nhất 3 game tích cực | 37 |
| Người có ít nhất 5 / 10 game tích cực | 5 / 1 |
| Review rỗng | 47 |
| Review tối đa 3 token tách bằng khoảng trắng, bao gồm review rỗng | 3.147 |
| Review có last-update sau thời gian tạo | 422 |
| ID review trùng trong file | 0 |
| Request crawl thành công / tổng attempt | 101 / 101 |
| App type được xác minh tự động là game | 98 / 100 |

Trong 8.423 người có tương tác tích cực, 8.254 người chỉ có một game tích cực, tức khoảng 98%. Chỉ 169 người có đủ hai tương tác tích cực để có khả năng giữ một tương tác làm lịch sử và một làm mục tiêu. Sau cutoff toàn cục, lọc warm item, loại game đã review và kiểm tra edit-time, số người đánh giá được sẽ còn phụ thuộc dữ liệu thực tế. Không được ghi 169 là số test users đã xác nhận.

37 người có ít nhất ba game có thể hỗ trợ lịch sử + validation + test cho cùng một người về mặt số lượng; đây không phải yêu cầu mỗi người phải xuất hiện trong cả hai cửa sổ của global protocol. Chỉ năm người có ít nhất năm game tích cực cho thấy các nhóm lịch sử 5–10, 11–30, trên 30 trong kế hoạch chưa phù hợp. Không đủ cỡ mẫu thì bỏ phân tích nhóm hoặc điều chỉnh ngưỡng trước khi xem test metrics.

Thành phần liên thông lớn nhất chứa 88 game và 7.501 người, nhưng nhiều người chỉ là lá bậc một. Component lớn không có nghĩa là có nhiều lịch sử hữu ích để cá nhân hóa.

Hai appdetails chưa khả dụng là Path of Exile 2 (`2694490`) và FINAL FANTASY XIV Online (`39210`). Request review của cả hai vẫn thành công. Audit giữ trạng thái unresolved sau lần kiểm tra lại; không tự suy diễn app type từ một response metadata bị thiếu.

## Những rủi ro quyết định chất lượng đồ án

1. **Lấy mẫu theo game làm đứt lịch sử người dùng.** 100 review gần nhất/game phù hợp để lấy một mẫu text có giới hạn. Nó không tối ưu để giữ các tương tác của cùng một người trên nhiều game. Nên quyết định khả năng ranking từ shared split; nếu thiếu coverage thì thiết kế lại sampling trên cùng nguồn trong phạm vi cho phép, hoặc dùng Amazon fallback thành một dataset riêng. Không tự động cho rằng Amazon đủ tốt trước khi audit metadata và histories.
2. **Quota cố định làm lệch ý nghĩa Popularity.** Mỗi game có đúng 100 review, nên positive count trên toàn snapshot bị ảnh hưởng mạnh bởi positive rate và quota. Đây có thể là baseline hợp lệ trên dataset đã chọn, nhưng không đại diện độ phổ biến của game trên Steam. Trong snapshot này, khoảng từ review cũ nhất tới mới nhất trong 100 review CS2 là khoảng 8 giờ; với My Time at Portia là 139,24 ngày. Global time split có thể làm thay đổi mạnh item coverage; phải công bố khoảng thời gian từng game và số item có trong train.
3. **Thiếu định nghĩa điểm opinion.** Công thức fusion hiện có alpha nhưng còn cần định nghĩa cách tạo vector user/item, mapping aspect, missing values, chuẩn hóa score và fallback. Một phàn nàn về story không có nghĩa người đó ghét mọi game có story; số lần nhắc một aspect cũng không tự chứng minh aspect đó quan trọng.
4. **ABSA chưa được chứng minh đúng trên ngôn ngữ game.** Có 31,47% review rất ngắn, cùng slang, sarcasm và meme. Không được dùng voted_up làm nhãn cho mọi aspect. Cần evidence span thật, annotation guide, development/evaluation tách biệt và đánh giá precision/recall/F1 trên nhãn người.
5. **Rò rỉ theo thời gian.** Không dùng review mục tiêu để tạo user/item opinion. Snapshot mới lưu timestamp_updated theo [API Steamworks](https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english). Text và voted_up có thể đã được sửa sau thời điểm tạo; cần chính sách bảo thủ theo edit-time. Một ngày tạo cũ không chứng minh text hiện tại đã tồn tại trước cutoff. [Nghiên cứu về temporal leakage](https://arxiv.org/abs/2010.11060) cho thấy vi phạm global timeline có thể làm thay đổi kết quả và thứ hạng mô hình.
6. **Nhầm chất lượng đề tài với tiến độ thực hiện.** Repo có kế hoạch chi tiết và phần thu thập chạy được. Trên main hiện chưa có kết quả chứng minh PPR, LightGCN hoặc opinion augmentation tốt đến đâu. Không nên trình bày kế hoạch như kết quả đã đạt.

## Phạm vi nên giữ và cách chia việc

Giữ bốn cấu hình: Popularity, PPR, LightGCN, LightGCN + opinion. Chưa thêm SASRec, chatbot, mô hình tự huấn luyện từ đầu, nhiều nguồn crawl hoặc giao diện lớn. Có thể làm đồ án tốt ngay cả khi phần opinion không cải thiện ranking, miễn kết quả được đo công bằng và có phân tích giới hạn.

| Vai trò | Đầu ra cần chịu trách nhiệm | Cân bằng khối lượng |
| --- | --- | --- |
| Data collection | Snapshot/versioning, metadata và quality diagnostics, hỗ trợ reproducibility | Sau khi crawl xong, hỗ trợ kiểm tra lịch sử, nguồn và artifact tích hợp; cùng tham gia annotation |
| Data pipeline & evaluation | Cleaning, loader, global cutoffs, coverage, evaluator, Popularity | Đây là phần khó về phương pháp, cần được cả nhóm review thay vì coi là việc phụ |
| Graph recommendation | PPR, LightGCN, config và runtime trên cùng split | Chạy pipeline nhỏ trước, sau đó mới tích hợp opinion feature |
| Opinion mining | Taxonomy, annotation, benchmark extractor, validation và định nghĩa O(u,i) | Cả nhóm hỗ trợ annotation độc lập; không để một người gánh toàn bộ nhãn và integration |

Ước lượng lập kế hoạch, chưa phải số giờ đã benchmark: 4 người × 8–10 giờ/tuần × 5–6 tuần tương ứng khoảng 160–240 giờ công. Điều kiện là đã biết Python/ML căn bản và chốt nguồn sớm. Nếu còn hai ngày tới checkpoint 23/11 thì mục tiêu nên là progress report có bằng chứng, coverage audit và một baseline nhỏ; hoàn tất toàn bộ hệ thống trong thời gian đó không thực tế.

Graph 10.000 cạnh/100 game là quy mô thử nghiệm nhỏ; khó khăn chính không nằm ở việc sở hữu GPU lớn. NLP inference có thể là phần tốn thời gian hơn. Benchmark một batch nhỏ trước, đo throughput và chất lượng rồi mới quyết định sample text, CPU/GPU hoặc chi phí. Không cần chạy ABSA toàn bộ dataset trước khi có annotation pilot.

## Thứ tự ưu tiên tiếp theo

1. **Chốt feasibility của ranking.** Data/evaluation owner công bố số user/item/target theo global train/validation/test, bao gồm các lý do bị loại. Kiểm tra lịch sử và item coverage trước khi dành thời gian tuning mô hình. Thống nhất mức coverage chấp nhận được theo rubric và độ chắc chắn mong muốn; repo hiện chưa có ngưỡng chính thức.
2. **Chạy baseline và PPR trên cùng protocol.** Dùng cùng ứng viên, cùng seen-item exclusion và cùng evaluator. Đừng thay split để cứu một model. Việc cần baseline đủ mạnh và tái lập được có cơ sở trong [nghiên cứu thực nghiệm về đánh giá neural recommendation](https://arxiv.org/abs/1907.06902); paper đó không chứng minh mô hình nào thắng trên dữ liệu này.
3. **Annotation trước khi khai thác text hàng loạt.** Bắt đầu 50 review, có overlap độc lập; sau đó mở rộng khoảng 200–300 review. Taxonomy phát triển từ dữ liệu được phép dùng ở giai đoạn train/development, tách extraction development khỏi held-out extraction evaluation. Không dùng LLM tự sinh nhãn rồi gọi đó là human gold labels.
4. **Viết rõ O(u,i) và normalize trước integration.** Chốt join keys, aspect schema, cách xử lý thiếu profile và alpha chọn trên validation. Giữ test đóng cho tới khi cấu hình đã cố định.
5. **Demo nhỏ và báo cáo kết quả thật.** Chọn user đủ lịch sử, hiển thị top game, model score và evidence span có nguồn. Báo cáo Recall/NDCG cùng coverage, runtime, uncertainty phù hợp cỡ mẫu và các trường hợp thất bại. Không biến lời giải thích tự sinh thành bằng chứng người dùng thực sự thích một aspect.

Với giới hạn dữ liệu hiện tại, hướng đáng bảo vệ là một hệ thống và thí nghiệm được kiểm chứng trên population được mô tả rõ, kèm phân tích opinion đáng tin cậy. Chưa có bằng chứng để kết luận mô hình hybrid cải thiện recommendation hay hoạt động tốt cho người dùng Steam nói chung.
