# OP Points × ELLIS × Giftronaut — BRD/PRD tích hợp

> **Kết luận điều hành:** Prototype hiện tại mới mô phỏng việc phát gift card; chưa có bằng chứng OP Points hoặc ELLIS đang gọi Giftronaut thật. Luồng mục tiêu bắt đầu từ việc kết nối Giftronaut và xác nhận Choice Card/mệnh giá được hỗ trợ, sau đó OP đổi điểm, Ohmyhotel đặt quà, Giftronaut xác nhận kết quả và hệ thống chốt giao dịch. OP Points là nơi người dùng đổi và tự resend khi email bounce; ELLIS cấu hình, hỗ trợ và kiểm tra vận hành; mọi kết nối Giftronaut được thực hiện ở backend Ohmyhotel.

| Thuộc tính | Nội dung |
|---|---|
| Sản phẩm | Ohmyhotel B2B — OP Points và ELLIS |
| Phạm vi | Tích hợp Giftronaut để đổi điểm thành Choice Card |
| Phiên bản | 1.4 — High-level system interaction draft |
| Ngày biên soạn | 14/10/2026 |
| Cập nhật gần nhất | 15/10/2026 |
| Vai trò biên soạn | Product Owner / Business Analyst |
| Độc giả | Business, Product, Engineering, QA, Operations, Finance, Security, Partnerships |
| Trạng thái | Target proposal; chưa phải xác nhận production đã tích hợp |

## 0. Cách đọc và mức độ tin cậy

Mọi nhận định quan trọng dùng một trong bốn nhãn sau:

- **[OBS] Observed:** quan sát được từ prototype hoặc artifact trong workspace; không chứng minh backend production.
- **[VER] Verified:** đối chiếu với tài liệu API chính thức của Giftronaut tại ngày biên soạn.
- **[TGT] Target:** thiết kế/yêu cầu được đề xuất cho Ohmyhotel.
- **[DEC] Decision:** quyết định còn mở, cần owner phê duyệt trước khi build hoặc go-live.

Các sơ đồ mô tả **target system**, trừ khi chú thích khác. Tên API nội bộ trong tài liệu là contract đề xuất, không phải khẳng định endpoint đã tồn tại.

### 0.1. Từ điển ngắn cho PO/BA

| Thuật ngữ trong tài liệu | Hiểu đơn giản |
|---|---|
| Catalog API | API dùng để xác nhận Choice Card `productId` và mệnh giá được phép; không phải catalog thương hiệu hiển thị cho OP |
| Published reward option | Món quà Ohmyhotel đã duyệt và cho phép OP nhìn thấy/đổi |
| Redemption | Một yêu cầu đổi điểm của OP |
| Order | Đơn phát quà được gửi sang Giftronaut |
| Hold điểm | Tạm giữ điểm để OP không thể dùng cùng số điểm cho giao dịch khác |
| Spend điểm | Chốt trừ điểm sau khi Giftronaut xác nhận đơn hoàn tất |
| Release điểm | Trả phần điểm đang giữ khi chắc chắn không có quà được phát |
| Callback / webhook | Giftronaut chủ động báo kết quả về Ohmyhotel |
| Poll | Ohmyhotel chủ động hỏi lại trạng thái đơn khi chưa nhận được callback |
| Idempotency key | Mã chống tạo hai đơn cho cùng một lần OP bấm đổi quà |
| Reconciliation | Đối soát theo lô để tìm sai lệch còn sót giữa điểm, đơn quà và tiền provider |

Các thuật ngữ kỹ thuật như HMAC, outbox hoặc optimistic locking chỉ xuất hiện trong phần API/kiểm soát dành cho Engineering. Quyết định sản phẩm cần hiểu là: **ai làm gì, khi nào giao dịch được coi là xong, điểm được xử lý ra sao và người dùng thấy trạng thái nào**.

---

# Phần A — BRD: bài toán kinh doanh

## 1. Hiện trạng và câu trả lời “đã tích hợp chưa?”

### 1.1. Kết luận hiện trạng

**[OBS] Chưa có bằng chứng về tích hợp Giftronaut thật trong phạm vi đã khảo sát.** Prototype công khai thể hiện trải nghiệm đổi điểm và mô phỏng xử lý bằng state/timer phía trình duyệt. Workspace không có backend source, credentials, provider logs hoặc production network trace để xác nhận hệ thống khác đang tích hợp.

Vì vậy kết luận đúng về mặt BA là:

1. Prototype đang có **UI/flow mô phỏng**.
2. Không nên mô tả là “đã tích hợp Giftronaut”.
3. Không thể phủ định một tích hợp production nằm ngoài source và quyền truy cập hiện có.
4. Muốn xác minh dứt điểm cần kiểm tra backend repository, secret manager, API gateway logs, webhook configuration và Giftronaut organization portal.

### 1.2. Vấn đề kinh doanh

OP Points đã định nghĩa giá trị điểm của OP, còn ELLIS quản trị policy và vận hành. Khoảng trống là một chuỗi phát quà có thể kiểm soát từ đầu đến cuối:

| Vấn đề | Rủi ro nếu không giải quyết | Năng lực cần có |
|---|---|---|
| UI báo thành công nhưng provider chưa phát quà | Khiếu nại, mất niềm tin | Trạng thái dựa trên backend/provider |
| Trừ điểm và đặt quà là hai hệ thống khác nhau | Mất điểm hoặc phát quà trùng | Tạm giữ điểm, mã chống trùng và cơ chế hỏi lại kết quả |
| Timeout không cho biết đơn có được tạo hay chưa | Retry mù tạo chi phí kép | Tra cứu theo `clientOrderId` trước khi quyết định |
| Email bounce bị hiểu nhầm là chưa phát quà | Hoàn điểm sai hoặc phát quà mới | Tách issuance và delivery; resend đơn cũ |
| Balance provider thấp | Đơn bị từ chối | Finance kiểm tra theo lịch; lỗi 402 làm Failed và trả điểm |
| Ops không thấy cùng dữ liệu với OP | Support chậm, action thiếu audit | Một source of truth và ELLIS exception cockpit |

## 2. Mục tiêu, outcome và guardrail

### 2.1. Business outcomes [TGT]

| ID | Outcome | Chỉ số đề xuất |
|---|---|---|
| BO-01 | OP đổi điểm và nhận quà đáng tin cậy | Tỷ lệ issuance thành công; thời gian từ request đến issued |
| BO-02 | Không tạo tác động tài chính trùng | Số duplicate gift, duplicate spend bằng 0 |
| BO-03 | Ops xử lý ngoại lệ có bằng chứng | Case quá SLA, mean time to resolve, reopen rate |
| BO-04 | Finance kiểm soát tiền ở provider | Available/pending balance, coverage days, unreconciled value |
| BO-05 | Support giải thích được từng giao dịch | 100% redemption truy vết được qua correlation ID |

### 2.2. Guardrail bắt buộc [TGT]

- Không gửi client secret/access token xuống OP Points hoặc ELLIS browser.
- Không trừ điểm vĩnh viễn chỉ dựa trên click ở UI.
- Không release hold khi kết quả provider còn bất định.
- Không tạo idempotency key mới để “retry” cùng một ý định đổi quà.
- Không hoàn điểm chỉ vì email bounce.
- Không resend bằng cách tạo gift order mới.
- Không cho một OP đổi vượt `available balance` dù có request đồng thời.
- Không cho Operations sửa trực tiếp balance; mọi adjustment phải là ledger transaction có approval và audit.

## 3. Phạm vi

### 3.1. Phạm vi theo thứ tự triển khai

| Nhóm | Nội dung | Có chặn core flow? |
|---|---|---|
| **P0 — Core integration** | Kết nối sandbox; xác nhận Choice Card `productId` và mệnh giá; OP tạo redemption; giữ điểm; tạo/query Giftronaut order; nhận callback; chốt spend/release; OP xem trạng thái | Có |
| **P1 — Vận hành pilot** | ELLIS tra cứu chi tiết; OP/Ops xử lý bounce-resend; xem balance theo lịch; danh sách lỗi; runbook hỗ trợ | Chặn production pilot, không chặn sandbox E2E |
| **P2 — Kiểm soát mở rộng** | Đối soát tự động theo lô, màn hình mismatch, báo cáo financial close và phân tích xu hướng | Không chặn core build; lên kế hoạch sau khi luồng chính ổn định |
| **P3 — Tối ưu** | Funding API, bulk/campaign, multi-provider, forecast nâng cao | Ngoài MVP |

P0 dùng Choice Card, gửi ngay (`IMMEDIATE`) và mỗi redemption chỉ có một người nhận để luồng kết quả rõ ràng. Trước production pilot vẫn cần một bước kiểm tra thủ công hằng ngày; hệ thống reconciliation tự động đầy đủ thuộc P2.

### 3.2. Out of scope cho MVP

- Bulk recipient trong một OP redemption.
- Campaign order, recipient groups và tự quản email template qua API.
- Branded Card riêng từng merchant hoặc reward-link delivery.
- Tự động ACH top-up bằng `balance.write`.
- Tự suy đoán gift đã được người nhận sử dụng khi provider chưa có event khả dụng.
- Multi-provider routing và tự động chọn provider theo giá.

## 4. Stakeholder và ownership

| Năng lực | Accountable | Responsible | Consulted |
|---|---|---|---|
| Point policy và Choice Card/mệnh giá | Product | Product Ops | Finance, Engineering |
| Giftronaut commercial contract/SLA | Partnerships | Partnerships | Legal, Finance, Product |
| Funding và lịch kiểm tra balance | Finance | Finance Ops | Product, Operations |
| Integration và reliability | Engineering | Backend/SRE | Security, QA |
| Daily exceptions và resend | Operations | Support/Ops | Engineering |
| P2 reconciliation sign-off | Finance | Operations + Data/Engineering | Product |
| Security review/secrets/webhook | Security | Engineering | Giftronaut |

![Stakeholder và ownership map](assets/00-stakeholder-ownership.png)

[PlantUML](diagrams/00-stakeholder-ownership.puml) · [SVG](assets/00-stakeholder-ownership.svg)

## 5. Nguyên tắc phân chia trách nhiệm hệ thống

| Hệ thống | Làm gì | Không nên làm gì |
|---|---|---|
| OP Points UI | Chọn quà, xác nhận email, gửi ý định, xem trạng thái | Gọi provider, giữ secret, tự tính/trừ balance authoritative |
| ELLIS UI | Cấu hình quà, tra cứu giao dịch, resend có quyền, hỗ trợ case lỗi | Sửa điểm hoặc tạo gift trực tiếp bên ngoài flow đã duyệt |
| Internal API | Kiểm tra người dùng/quyền và cung cấp dữ liệu cho hai giao diện | Đưa khóa kết nối Giftronaut xuống trình duyệt |
| Dịch vụ xử lý redemption | Điều phối toàn bộ quá trình giữ điểm, đặt quà, nhận kết quả và chốt điểm | Coi một lần timeout là thất bại cuối cùng |
| Lớp kết nối Giftronaut | Chuyển dữ liệu Ohmyhotel sang đúng API Giftronaut và xử lý lỗi kết nối | Tự quyết định chính sách điểm |
| Point Ledger | Sổ giao dịch điểm: điểm khả dụng, đang giữ, đã tiêu và được trả lại | Cho phép sửa thẳng số dư mà không có giao dịch tham chiếu |
| Giftronaut | Choice Card config, order, delivery, provider balance/ledger | Source of truth cho trạng thái provider, không phải cho điểm OP |

![Bối cảnh tích hợp hệ thống](assets/01-system-context.png)

[PlantUML](diagrams/01-system-context.puml) · [SVG](assets/01-system-context.svg)

### 5.1. Kết quả harness check với hệ thống hiện tại

#### 5.1.1. Kết luận

**Solution fit với functional spec hiện tại sau các điều chỉnh trong mục này.** Nó giữ đúng hành trình OP chọn mệnh giá → nhận Choice Card qua email → xử lý bounce/resend. Tuy nhiên đây là **fit về product flow và integration contract**, chưa phải bằng chứng backend hiện tại đã sẵn sàng.

Workspace hiện chỉ có functional spec, tài liệu phân tích và prototype bundle; không có source backend, database schema, API gateway config hoặc deployment manifest. Vì vậy không thể xác minh framework, cách deploy hoặc khả năng tái sử dụng service production. Phần tích hợp phải được triển khai như backend capability mới, không gọi Giftronaut trực tiếp từ prototype frontend.

#### 5.1.2. Fit matrix

| Miền kiểm tra | Hệ thống/spec hiện tại | Solution sau điều chỉnh | Đánh giá |
|---|---|---|---|
| Trải nghiệm OP | Chọn US$10/20/50/100; nhận Choice Card qua email | Giữ nguyên flow và trạng thái Processing/Sent/Bounced/Failed | **Fit** |
| Sản phẩm quà | Chỉ một Choice Card; không build catalog thương hiệu theo quốc gia | Sync `GET /catalog/choice-cards` để xác nhận `productId` và mệnh giá, sau đó cấu hình các option cố định | **Fit sau khi thu gọn catalog** |
| Điểm | Prototype tính trên browser; production cần ledger earn/hold/deduct/restore/expire | Bổ sung Point Ledger và giữ → chốt/trả điểm | **Fit về target; backend còn thiếu** |
| Tạo order | Spec dùng `POST /orders/choice-cards`, một recipient, IMMEDIATE, cùng idempotency key | Giữ đúng contract; có recovery theo `clientOrderId` | **Fit** |
| Kết quả | COMPLETE/delivery callback; timeout phải query order | Callback + poll cùng cập nhật một redemption | **Fit** |
| Bounce/resend | OP tự kiểm tra/sửa email và resend; ELLIS có audit | OP self-service là luồng chính; Ops dùng ELLIS khi cần hỗ trợ | **Fit sau khi sửa ownership** |
| Balance | ELLIS hiển thị balance; business đã quyết định không có alert | P1 kiểm tra theo lịch; 402 làm Failed và trả điểm; alert chỉ là change request | **Fit sau khi bỏ alert bắt buộc** |
| Funding | Chuyển khoản thủ công qua portal; không dùng ACH | Manual funding là baseline; funding API để P3 ngoài scope | **Fit** |
| Audit/đối soát | Audit append-only và đối chiếu 1:1 được ghi là bắt buộc | P1 có audit + kiểm tra thủ công; P2 tự động hóa reconciliation/cockpit | **Fit nếu không bỏ kiểm soát tối thiểu** |
| Persistence | Redemption nằm ở `localStorage`; policy reset khi refresh | Lưu server-side redemption, point transaction, provider event và audit | **Gap phải build** |
| Booking/account data | Prototype gán OP và ngày thanh toán bằng dữ liệu suy ra | Cần account ID thực trên booking và paid-at event thật | **Dependency ngoài Giftronaut** |

#### 5.1.3. Những gì có thể tái sử dụng và những gì phải build

| Có thể giữ từ hiện trạng | Phải build cho production |
|---|---|
| UX Redeem, bốn mệnh giá ban đầu, trạng thái hiển thị và nội dung bounce/resend | Backend redemption API và quyền theo OP/company |
| Công thức đổi point/mệnh giá và policy ELLIS đã mô tả | Point ledger bền vững với HOLD/SPEND/RELEASE |
| Data shape `GiftRedemption`, `idempotencyKey`, `orderNo`, events làm reference | Database schema, transaction boundary và worker xử lý order |
| ELLIS prototype panel làm reference UI | OAuth/secret storage, Giftronaut adapter và webhook endpoint |
| Mock cases OK, validation, insufficient balance, bounced | Timeout recovery, duplicate protection, audit store và monitoring |
| Báo cáo hiện có làm reference requirement | Dữ liệu production từ booking/payment/company master và export |

#### 5.1.4. Điều kiện để Engineering xác nhận fit cuối cùng

1. Cung cấp backend repository hoặc architecture diagram production của OP Points/ELLIS.
2. Xác định service/database nào sẽ sở hữu Point Ledger và Redemption.
3. Xác nhận event/field thật cho OP tạo booking và thời điểm Fully Paid.
4. Xác nhận cơ chế đăng nhập/quyền hiện tại giữa Marketplace và ELLIS.
5. Chạy contract test bằng Giftronaut sandbox tenant thật để chốt `productId`, mệnh giá, resend payload, webhook challenge và IP allowlist.
6. Chạy một vertical slice: US$10 từ OP UI → HOLD → order → callback → SPEND → hiển thị Sent.

---

# Phần B — PRD: hành vi sản phẩm và tích hợp

## 6. Master flow và mức độ ưu tiên

### 6.1. High-level lifecycle: từ zero setup đến transaction complete

![Master transaction lifecycle](assets/10-master-transaction-lifecycle.png)

[PlantUML](diagrams/10-master-transaction-lifecycle.puml) · [SVG](assets/10-master-transaction-lifecycle.svg)

Đây là flow chính để đọc toàn bộ giải pháp. BA/PO có thể review từ trái sang phải mà chưa cần đọc API:

| Stage | Kết quả cần đạt | Flow chi tiết | Priority |
|---|---|---|---|
| A. Setup integration | Có sandbox app, scopes, credentials và webhook hoạt động | [7.2](#72-flow-a--setup-integration-và-choice-card-p0) | P0 |
| B. Setup Choice Card | Xác nhận productId/mệnh giá, map point cost và publish bốn option | [7.2](#72-flow-a--setup-integration-và-choice-card-p0) | P0 |
| C. Create redemption/order | Điểm được hold, provider nhận order duy nhất | [7.3](#73-flow-b--create-redemption-và-provider-order-p0) | P0 |
| D. Complete transaction | Callback/poll xác nhận COMPLETE, điểm chuyển SPENT | [7.4](#74-flow-c--callbackpoll-và-complete-transaction-p0) | P0 |
| E. Support delivery | Bounce được xử lý bằng resend cùng gift | [7.9](#79-flow-e--email-bounce-và-resend-p1) | P1 |
| F. Batch control | Đối soát/report phát hiện drift còn sót | [14](#14-reconciliation-p2) | P2 |

Diễn giải nghiệp vụ theo một câu: **Ohmyhotel kết nối Giftronaut → chọn quà được phép đổi → OP tạo yêu cầu → Ohmyhotel tạm giữ điểm và đặt quà → Giftronaut báo hoàn tất → Ohmyhotel chốt trừ điểm → OP nhìn thấy kết quả.**

Một giao dịch chỉ được coi là **complete về nghiệp vụ đổi điểm** khi:

1. có một redemption nội bộ duy nhất;
2. có một Giftronaut order được liên kết bằng idempotency key/order ID;
3. provider order đã đạt `COMPLETE`;
4. point hold đã chuyển thành `SPEND` đúng một lần;
5. OP Points đọc được trạng thái cuối từ backend.

Email delivery có thể hoàn tất hoặc bounce sau đó. Delivery là trục vận hành riêng và không đảo ngược issuance/point spend.

#### 6.1.1. High-level system sequence: các hệ thống tương tác ra sao

![High-level system sequence](assets/15-high-level-system-sequence.png)

[PlantUML](diagrams/15-high-level-system-sequence.puml) · [SVG](assets/15-high-level-system-sequence.svg)

Sơ đồ trên là bản đồ tương tác tổng ở mức nghiệp vụ. Nó gom các business interaction chính thành bốn chặng:

1. **Chuẩn bị:** OMH Admin cấu hình món quà và chính sách quy đổi; Finance nạp trước tiền thật vào Giftronaut. Đây là công việc theo kỳ, không diễn ra trong từng giao dịch.
2. **Tạo giao dịch:** OP bấm đổi điểm; OP Points gửi yêu cầu về backend Ohmyhotel; backend kiểm tra điều kiện, tạm giữ điểm và tạo order tại Giftronaut.
3. **Hoàn tất:** Giftronaut gửi quà và báo kết quả; backend chốt điểm thành `SPENT`, sau đó cập nhật OP Points và ELLIS.
4. **Hỗ trợ:** nếu email bị bounce hoặc OP chưa nhận được, hệ thống gửi lại cùng gift/order cũ và không trừ thêm điểm.

> **Quy tắc approval:** OMH Admin/Finance duyệt **chính sách, ngân sách và việc nạp balance trước**. Một lượt đổi điểm hợp lệ của OP được xử lý tự động và **không chờ Admin approve từng order**. Chỉ các trường hợp lỗi hoặc bất thường mới chuyển sang ELLIS để Operations kiểm tra.

> **Quy tắc tiền và điểm:** OP Points là điểm nội bộ do Ohmyhotel quản lý; Giftronaut không giữ “điểm Giftronaut”. Khi giao dịch thành công, Ohmyhotel chốt trừ điểm của OP và Giftronaut đồng thời sử dụng balance USD đã được OMH nạp trước để phát Choice Card.

### 6.2. Priority map

| Priority | Phạm vi | Lý do |
|---|---|---|
| **P0 — Core integration** | Kết nối Giftronaut; xác nhận Choice Card và mệnh giá; OP tạo yêu cầu; tạm giữ điểm; tạo hoặc hỏi lại order; nhận kết quả; chốt trừ/trả điểm; hiển thị trạng thái | Bắt buộc để một transaction chạy an toàn từ đầu đến cuối |
| **P1 — Vận hành pilot** | ELLIS tra cứu; OP/Ops xử lý bounce-resend; kiểm tra balance theo lịch; danh sách giao dịch bị kẹt; runbook | Cần trước production pilot để Support/Operations xử lý được |
| **P2 — Kiểm soát mở rộng** | Đối soát tự động theo lô, màn hình sai lệch, financial close report và trend | Làm sau khi core flow ổn định; không chặn sandbox E2E |
| **P3 — Tối ưu** | Tự động nạp tiền, nhiều provider, bulk/campaign và forecast nâng cao | Không nằm trong MVP integration |

> **Ranh giới quan trọng:** batch reconciliation là P2; request-level recovery sau timeout và query theo `clientOrderId` vẫn là P0. Đây là cơ chế chống tạo order hoặc trừ điểm trùng ngay trong core transaction.

### 6.3. Cách các hệ thống phối hợp

**[TGT] OP Points và ELLIS không kết nối thẳng tới Giftronaut.** Cả hai gửi yêu cầu về backend Ohmyhotel; backend là bên duy nhất giữ khóa và gọi API Giftronaut. Cách này giúp:

- bảo vệ credentials;
- áp dụng idempotency và rate limiting nhất quán;
- đổi provider mà không làm lộ contract ra UI;
- audit mọi action theo user và correlation ID;
- giữ state nội bộ khi provider/webhook gián đoạn;
- reconcile ledger điểm với order và tiền provider.

### 6.4. Vì sao giao dịch phải có bước “đang xử lý”

Ohmyhotel và Giftronaut là hai hệ thống độc lập nên không thể chốt điểm và phát quà trong đúng cùng một thao tác. Target dùng ba lớp kiểm soát:

1. **Ghi nhận nội bộ cùng lúc:** tạo redemption, giữ điểm và ghi yêu cầu cần gửi đi trong một lần lưu dữ liệu.
2. **Một yêu cầu chỉ tạo một đơn:** dùng cùng `redemptionId` làm mã chống trùng phía Giftronaut.
3. **Hoàn tất sau:** callback hoặc việc hỏi lại trạng thái sẽ chốt từng request; batch reconciliation P2 chỉ tìm các sai lệch còn sót theo kỳ.

## 7. Luồng end-to-end chi tiết

### 7.1. Bản đồ các subflow

| Flow | Trigger | API/callback chính | Done condition | Priority |
|---|---|---|---|---|
| A. Integration + Choice Card config | Onboarding hoặc daily refresh | OAuth token; `GET /catalog/choice-cards`; internal config publish | Bốn option chỉ dùng mệnh giá provider hỗ trợ | P0 |
| B. Create redemption/order | OP confirm đổi điểm | Internal quote/create; `POST /orders/choice-cards`; query by clientOrderId | Có redemption + point HOLD + provider order hoặc VERIFYING | P0 |
| C. Complete | Webhook hoặc poll scheduler | Signed callback; `GET /orders/{orderId}` | Provider COMPLETE + point SPEND đúng một lần | P0 |
| D. Failure recovery | Timeout/409/429/5xx | Query, retry cùng key, backoff | Link đơn gốc hoặc definitive failure + RELEASE | P0 |
| E. Bounce/resend | `order.bounced`, Ops action | Internal resend; provider `/resend`; callback mới | Cùng gift được gửi lại, không trừ điểm thêm | P1 |
| F. Batch reconciliation | Schedule/manual close | Orders + balance ledger reads | Mismatch được phát hiện/case hóa | P2 |

### 7.2. Flow A — Setup integration và Choice Card [P0]

![Setup and catalog API flow](assets/11-setup-catalog-api.png)

[PlantUML](diagrams/11-setup-catalog-api.puml) · [SVG](assets/11-setup-catalog-api.svg)

**Câu hỏi nghiệp vụ flow này trả lời:** Ohmyhotel lấy đúng Choice Card `productId` và mệnh giá được phép từ đâu, ai xác nhận cấu hình và khi nào bốn option được hiển thị cho OP?

**Kết quả hoàn tất:** OP Points hiển thị các option US$10/20/50/100 đã được xác nhận nằm trong khoảng provider cho phép, có point cost, ngày hiệu lực và mapping chính xác tới `productId` Choice Card.

#### 7.2.1. Setup một lần theo environment

| Bước | Owner | Action | Output |
|---:|---|---|---|
| 1 | Partnerships/Admin | Tạo Giftronaut Sandbox app | `client_id`, `client_secret`, app/environment ID |
| 2 | Engineering/Security | Chọn scopes tối thiểu | P0: `catalog.read`, `orders.read`, `orders.write`; thêm `balance.read` ở P1 |
| 3 | Engineering/Security | Lưu secret refs, cấu hình rotation | Không có plain secret trong source/CI/log |
| 4 | Engineering | Cấu hình public webhook URL và secret | Endpoint theo environment, HMAC test pass |
| 5 | Engineering/QA | Token/connectivity smoke test | Token TTL/scopes/rate headers được ghi nhận |
| 6 | Product/QA | Gửi sandbox order thử | End-to-end technical readiness |

#### 7.2.2. Choice Card configuration lifecycle

1. Backend lấy token `catalog.read` và gọi `GET /api/v1/catalog/choice-cards` hằng ngày.
2. Hệ thống lấy `productId`, currency và khoảng/mệnh giá được phép của **một sản phẩm Choice Card**.
3. Product/Finance xác nhận các option US$10/20/50/100 nào được bật và số point tương ứng.
4. ELLIS lưu phiên bản policy cùng ngày hiệu lực; OP Points chỉ nhận các option đang active.
5. Nếu provider thay đổi `productId` hoặc giới hạn mệnh giá, hệ thống giữ cấu hình đang chạy và yêu cầu review; không tự thay đổi giao dịch lịch sử.

**Không build:** danh sách thương hiệu theo quốc gia hoặc catalog quà cho OP chọn. Người nhận chọn thương hiệu bên trong link Choice Card của Giftronaut sau khi nhận email.

### 7.3. Flow B — Create redemption và provider order [P0]

![Create order API flow](assets/12-create-order-api.png)

[PlantUML](diagrams/12-create-order-api.puml) · [SVG](assets/12-create-order-api.svg)

**Câu hỏi nghiệp vụ flow này trả lời:** Khi OP bấm xác nhận, làm sao hệ thống vừa giữ đúng điểm vừa chỉ tạo đúng một đơn quà?

**Kết quả hoàn tất:** hệ thống có một `redemptionId`, điểm ở trạng thái đang giữ và Giftronaut đã nhận đơn hoặc giao dịch đang được xác minh; OP không phải bấm tạo lại.

Các mốc chính:

- API quote chỉ xác nhận “món quà này cần bao nhiêu điểm” trong một khoảng thời gian; chưa giữ điểm hoặc đặt quà.
- API create kiểm tra lại quote rồi cùng lúc giữ điểm, tạo redemption và ghi yêu cầu cần gửi sang Giftronaut.
- OP Points nhận trạng thái `PROCESSING`; chưa hiển thị “đã gửi quà”.
- Backend dùng `redemptionId` làm mã chống trùng và lưu `orderId` do Giftronaut trả về.
- 409 hoặc timeout không tạo key/order mới; chuyển sang Flow D.

### 7.4. Flow C — Callback/poll và complete transaction [P0]

![Completion callback API flow](assets/13-completion-callback-api.png)

[PlantUML](diagrams/13-completion-callback-api.puml) · [SVG](assets/13-completion-callback-api.svg)

**Câu hỏi nghiệp vụ flow này trả lời:** Ai xác nhận giao dịch đã xong và tại thời điểm nào điểm được chốt trừ?

**Kết quả hoàn tất:** khi Giftronaut order đạt `COMPLETE`, redemption thành `ISSUED`, điểm đang giữ chuyển thành đã tiêu đúng một lần và OP Points đọc được kết quả cuối.

Giftronaut có thể chủ động báo kết quả qua callback; nếu callback chưa đến, Ohmyhotel chủ động hỏi lại. Hai đường này cùng cập nhật một giao dịch, và mã giao dịch duy nhất bảo đảm điểm chỉ được chốt một lần.

Trình tự hoàn tất:

1. Xác minh callback thật sự từ Giftronaut và chưa được xử lý trước đó.
2. Lưu callback rồi phản hồi đã nhận để Giftronaut không phải chờ.
3. Tìm redemption/order tương ứng.
4. Nếu callback đến muộn hoặc chưa đủ rõ, hỏi lại trạng thái order từ Giftronaut.
5. Nếu trạng thái chính thức là `COMPLETE`, chốt giao dịch điểm `SPEND` có tham chiếu redemption/order.
6. Cập nhật trạng thái phát quà và giao email riêng; OP Points đọc kết quả qua API nội bộ.
7. Nếu chưa COMPLETE, giữ HOLD và lên lịch poll tiếp trong SLA.

### 7.5. Preconditions

- OP đã đăng nhập và thuộc company hợp lệ.
- Account không bị khóa redemption/risk review.
- Option mệnh giá còn active, nằm trong giới hạn Choice Card và có policy snapshot.
- Email đã được OP xác nhận theo UX/policy.
- Point available đủ sau khi loại phần đang hold.
- Chương trình redemption đang mở; các lỗi provider được xử lý theo error matrix.

### 7.6. Happy path tổng hợp

![Happy path](assets/02-happy-path-redemption.png)

[PlantUML](diagrams/02-happy-path-redemption.puml) · [SVG](assets/02-happy-path-redemption.svg)

| Bước | Actor/System | Xử lý | Dữ liệu/evidence bắt buộc |
|---:|---|---|---|
| 1 | OP | Chọn mệnh giá và xác nhận email | redemptionOptionId, point cost, masked email |
| 2 | OP Points | Gửi request duy nhất | `clientRequestId`, `Idempotency-Key` |
| 3 | Internal API | Xác thực, authorize, validate schema | actor, tenant/company, correlation ID |
| 4 | Orchestrator | Resolve policy snapshot | productId, points, amount, currency, refund policy |
| 5 | Ledger | Atomic hold theo FEFO | HOLD transactions gắn redemptionId |
| 6 | Orchestrator | Ghi redemption và outbox | status `HELD`, immutable provider key |
| 7 | API | Trả `202 PROCESSING` | redemptionId; không nói “đã gửi quà” |
| 8 | Worker/Adapter | Lấy token và POST Choice Card | request/response metadata đã mask |
| 9 | Giftronaut | Tạo order | orderId, PENDING/IN_PROGRESS |
| 10 | Webhook/Poller | Xác nhận trạng thái canonical | signed event hoặc GET order evidence |
| 11 | Orchestrator | Khi order `COMPLETE`, chuyển hold → spend | SPEND reference providerOrderId |
| 12 | UI/ELLIS | Hiển thị issuance và delivery riêng | status, timestamps, reason code |

### 7.7. Quy tắc xác nhận điểm

- Khi request hợp lệ, điểm đi từ `AVAILABLE` sang `ON_HOLD` trước khi gọi provider.
- Khi provider order đạt `COMPLETE`, điểm đi từ `ON_HOLD` sang `SPENT`.
- Nếu provider từ chối chắc chắn trước khi tạo order hoặc xác nhận không tồn tại order theo recovery policy, hold được `RELEASE`.
- Nếu timeout/mất response, giữ `ON_HOLD` và chuyển `VERIFYING`; không release và không tạo key mới.
- Nếu delivery bounce sau khi issue, điểm vẫn `SPENT`.
- Mọi transition phải idempotent và kiểm tra version/current state.

### 7.8. Flow D — Timeout và kết quả chưa rõ [P0]

![Timeout recovery](assets/03-timeout-recovery.png)

[PlantUML](diagrams/03-timeout-recovery.puml) · [SVG](assets/03-timeout-recovery.svg)

**[VER]** Giftronaut yêu cầu `idempotencyKey`; gửi trùng trả `409 DUPLICATE_IDEMPOTENCY_KEY` và không tạo đơn thứ hai. Đơn gốc có thể tra bằng `GET /api/v1/orders?clientOrderId=...`.

Recovery policy [TGT]:

1. Gắn request provider với cùng `redemptionId` tối đa 64 ký tự.
2. Timeout đưa về `VERIFYING`, không kết luận fail.
3. Query theo `clientOrderId`; nếu có order, liên kết và theo dõi đơn đó.
4. Nếu query rỗng, retry có exponential backoff + jitter trong cửa sổ đã định nghĩa.
5. Chỉ release khi có bằng chứng chắc chắn request không tạo order, hoặc manual resolution theo runbook/provider support.
6. Nếu nhận 409, query đơn gốc; không sinh idempotency key khác.

### 7.9. Flow E — Email bounce và resend [P1]

![Bounce and resend API flow](assets/14-resend-api.png)

[PlantUML](diagrams/14-resend-api.puml) · [SVG](assets/14-resend-api.svg)

**Câu hỏi nghiệp vụ flow này trả lời:** Nếu quà đã phát nhưng email không tới, OP tự gửi lại thế nào; khi nào Operations cần hỗ trợ mà không phát thêm quà hoặc trừ thêm điểm?

**Kết quả hoàn tất:** OP dùng “Check email and resend” trên OP Points. Nếu cần hỗ trợ, Ops dùng ELLIS. Cả hai đều yêu cầu Giftronaut gửi lại **cùng gift/order**, lưu lịch sử action và chờ callback giao email tiếp theo.

Quy tắc:

1. Bounce chỉ thay đổi trạng thái giao email; redemption vẫn `ISSUED` và điểm vẫn `SPENT`.
2. OP chỉ resend redemption của chính mình; Ops chỉ resend trong phạm vi quyền hỗ trợ.
3. Nếu đổi email, màn hình phải yêu cầu xác nhận địa chỉ mới trước khi gửi.
4. Resend không tạo redemption, Giftronaut order hoặc point transaction mới.
5. Số lần resend cần giới hạn và được lưu audit để tránh abuse.

## 8. API interaction với Giftronaut

### 8.1. Thông số nền tảng [VER]

| Hạng mục | Contract hiện hành |
|---|---|
| API base URL | `https://api.giftronaut.com/api/v1` |
| Token endpoint | `POST https://api.giftronaut.com/oauth2/token` |
| Auth | OAuth 2.0 Client Credentials, Bearer token |
| Environment | Cùng URL; sandbox/production phụ thuộc credentials |
| Token TTL | Sandbox 24 giờ; production 1 giờ |
| Rate limit | Production 60 request/phút; sandbox 300 request/phút |
| Rate headers | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` |
| Order idempotency | Body `idempotencyKey`; duplicate trả 409 |

Nguồn: [API reference](https://api.giftronaut.com/docs/reference), [Quickstart](https://api.giftronaut.com/docs/quickstart).

### 8.2. API capability matrix

| Priority | Nghiệp vụ | Giftronaut endpoint | Ohmyhotel dùng để làm gì | Khi có lỗi |
|---|---|---|---|---|
| P0 | Đăng nhập hệ thống | `POST /oauth2/token` | Lấy quyền gọi API từ backend | Xin token mới một lần khi hết hạn |
| P0 | Xác nhận Choice Card config | `GET /api/v1/catalog/choice-cards` | Lấy `productId` và mệnh giá được phép; cache hằng ngày | Giữ cấu hình đang chạy và yêu cầu review nếu provider thay đổi |
| P0 | Tạo đơn quà | `POST /api/v1/orders/choice-cards` | Phát quà cho một redemption | Không tạo mã mới; chuyển qua flow xác minh |
| P0 | Tìm đơn bằng mã nội bộ | `GET /api/v1/orders?clientOrderId=...` | Xác định request timeout có tạo đơn hay chưa | Giữ điểm và thử lại theo lịch |
| P0 | Xem trạng thái một đơn | `GET /api/v1/orders/{orderId}` | Bổ sung callback hoặc xác nhận trạng thái cuối | Tiếp tục giữ điểm trong thời gian xác minh |
| P0 | Nhận callback | HTTPS webhook | Nhận kết quả order/delivery sớm | Poll order nếu callback trễ hoặc mất |
| P1 | Gửi lại email | `POST /api/v1/orders/{orderId}/resend` | Gửi lại cùng gift | Tạo case hỗ trợ; không tạo order mới |
| P1 | Xem số dư provider | `GET /api/v1/balance` | Finance kiểm tra available/pending theo lịch | Nếu đơn trả 402: Failed, trả điểm và nạp thủ công |
| P2 | Đọc sổ tiền provider | `GET /api/v1/balance/ledger` | Đối soát tiền theo kỳ | Tạo mismatch case |
| P3 | Yêu cầu ACH top-up | `POST /api/v1/balance/charge` | Chỉ xem xét qua change request | Baseline hiện tại vẫn là chuyển khoản qua portal |
| P3 | Hủy ACH top-up | `DELETE /api/v1/balance/charge/{fundingNo}` | Chỉ dùng nếu ACH được phê duyệt sau này | Maker-checker và Finance xử lý |

Scope kỹ thuật tương ứng: catalog dùng `catalog.read`; order/query/resend dùng `orders.read` và `orders.write`; balance dùng `balance.read`; funding tự động dùng `balance.write`.

### 8.3. OAuth interaction [TGT]

```http
POST https://api.giftronaut.com/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id={secret-ref}&
client_secret={secret-ref}&
scope=orders.read%20orders.write%20catalog.read%20balance.read
```

Ghi chú triển khai dành cho Engineering:

- sandbox và production dùng app/secret tách biệt;
- secret nằm trong secret manager, không nằm trong source, CI output hoặc request log;
- backend tái sử dụng token cho tới gần hết hạn thay vì xin token cho từng order;
- chỉ một tiến trình làm mới token tại một thời điểm;
- khi 401, refresh token tối đa một lần rồi phân loại lỗi; không loop vô hạn;
- `balance.write` tách sang credential/app có quyền hẹp nếu Phase sau bật funding API.

### 8.4. Provider create order mapping

Request target cho một redemption:

```json
{
  "idempotencyKey": "rdm_01J...",
  "productId": "<approved-choice-card-product-id>",
  "sendTiming": { "type": "IMMEDIATE" },
  "emailSetting": {
    "senderName": "Ohmyhotel Rewards",
    "subject": "Your OP Points reward",
    "message": "Your reward is ready."
  },
  "recipients": [
    {
      "email": "op@example.com",
      "firstName": "An",
      "lastName": "Nguyen",
      "amount": 25
    }
  ],
  "refundOption": false
}
```

| Internal field | Provider field | Rule |
|---|---|---|
| `redemption.id` | `idempotencyKey` | Stable, unique toàn organization; không đổi khi retry |
| policy `provider_product_id` | `productId` | Lấy từ Choice Card config snapshot đã xác nhận |
| fixed MVP | `sendTiming.type` | `IMMEDIATE` |
| approved template config | `emailSetting.*` | Versioned; subject/message không nhận HTML tùy ý từ client |
| verified profile/input | `recipients[0].email` | Normalize, validate, encrypt at rest/mask in logs |
| policy amount | `recipients[0].amount` | Whole number và đúng price point/currency |
| decision D-03 | `refundOption` | Baseline đề xuất false; stakeholder phải chốt |

**[VER]** Tài liệu Orders quy định account balance phải đủ tổng amount quy đổi USD; recipient amount phải đúng price point; `refundOption=false` mặc định có thời hạn 180 ngày. Nếu bật refund option, tài liệu hiện tại nêu cửa sổ 30/60/90 ngày với tỷ lệ refund 50%/40%/30%. Nguồn: [Orders API](https://api.giftronaut.com/docs/reference/orders).

## 9. API nội bộ đề xuất

### 9.1. Contract surface

| Priority | Người dùng | Method và path đề xuất | Ý nghĩa nghiệp vụ | Quyền |
|---|---|---|---|---|
| P0 | OP Points | `GET /v1/op-points/redemption-options` | Xem các quà đã được duyệt và số điểm cần dùng | OP thuộc company |
| P0 | OP Points | `POST /v1/op-points/redemptions/quote` | Khóa tạm giá trị điểm/mệnh giá để OP xác nhận | Chính OP |
| P0 | OP Points | `POST /v1/op-points/redemptions` | Tạo yêu cầu đổi quà và giữ điểm | Chính OP + chương trình đang mở |
| P0 | OP Points | `GET /v1/op-points/redemptions/{id}` | Xem trạng thái yêu cầu của mình | Chỉ chủ giao dịch |
| P1 | OP Points | `POST /v1/op-points/redemptions/{id}/resend` | OP gửi lại gift của chính mình sau bounce | Chủ giao dịch + trạng thái BOUNCED |
| P1 | ELLIS | `GET /v1/ellis/redemptions` | Tìm danh sách redemption cần hỗ trợ | Vai trò Ops theo phạm vi |
| P1 | ELLIS | `GET /v1/ellis/redemptions/{id}` | Xem timeline điểm, order và callback | Vai trò Ops theo phạm vi |
| P1 | ELLIS | `POST /v1/ellis/redemptions/{id}/resend` | Gửi lại cùng gift | Support role + reason |
| P1 | ELLIS | `GET /v1/ellis/provider-balance` | Xem số dư provider và mức cảnh báo | Finance/Ops read |
| P2 | ELLIS | `GET /v1/ellis/reconciliation-cases` | Xem sai lệch được phát hiện theo kỳ | Finance/Ops |
| P2 | ELLIS | `POST /v1/ellis/reconciliation-cases/{id}/actions` | Xử lý sai lệch có kiểm soát | Role + maker-checker |

### 9.2. Tạo redemption

```http
POST /v1/op-points/redemptions
Authorization: Bearer <Ohmyhotel user token>
Idempotency-Key: 7fc4a5a9-...
Content-Type: application/json
```

```json
{
  "quoteId": "qte_01J...",
  "redemptionOptionId": "choice-usd-20",
  "delivery": {
    "email": "op@example.com"
  }
}
```

```json
{
  "redemptionId": "rdm_01J...",
  "status": "PROCESSING",
  "issuanceStatus": "HELD",
  "deliveryStatus": "NOT_SENT",
  "usageStatus": "UNKNOWN",
  "pointsHeld": 2500,
  "submittedAt": "2026-10-14T08:15:30Z"
}
```

HTTP semantics [TGT]:

- `202` khi đã hold và đang submit/verify.
- `200` khi replay cùng idempotency key và payload giống nhau; trả resource gốc.
- `409 IDEMPOTENCY_PAYLOAD_MISMATCH` khi cùng key nhưng payload khác.
- `409 INSUFFICIENT_POINTS` hoặc `422` theo API standard nội bộ đã chọn; phải nhất quán.
- `503 REDEMPTION_TEMPORARILY_UNAVAILABLE` khi chương trình đang bảo trì hoặc provider integration bị tạm dừng trước bước hold.

### 9.3. OP tự resend và ELLIS hỗ trợ

```json
{
  "email": "corrected@example.com",
  "reasonCode": "RECIPIENT_EMAIL_CORRECTION",
  "caseId": "case_01J..."
}
```

Request body trên áp dụng cho action hỗ trợ từ ELLIS. OP Points dùng contract tương tự nhưng không cần `caseId` và server bắt buộc kiểm tra redemption thuộc đúng OP đang đăng nhập. Resend chỉ hợp lệ khi `issuanceStatus=ISSUED`, delivery là `BOUNCED`, actor có quyền và email mới được xác nhận. Action ghi lần gửi, old/new email đã mask, actor, reason, timestamp và provider response. Không tạo point transaction mới.

## 10. State model và mapping

![Redemption state machine](assets/05-redemption-state-machine.png)

[PlantUML](diagrams/05-redemption-state-machine.puml) · [SVG](assets/05-redemption-state-machine.svg)

### 10.1. Ba trục trạng thái

| Trục | Internal status | Ý nghĩa |
|---|---|---|
| Issuance | `REQUESTED`, `HELD`, `SUBMITTING`, `VERIFYING`, `PROVIDER_ACCEPTED`, `ISSUED`, `FAILED`, `RELEASED` | Gift có được provider tạo/xác nhận chưa |
| Delivery | `NOT_SENT`, `SENT`, `BOUNCED`, `RESEND_REQUESTED` | Email delivery; không quyết định quyền sở hữu điểm |
| Usage | `UNKNOWN` | Provider usage event chưa sẵn sàng theo tài liệu hiện tại |

### 10.2. Mapping trạng thái provider

| Provider status/event [VER] | Internal effect [TGT] | Point effect |
|---|---|---|
| POST trả `PENDING`/`IN_PROGRESS` | `PROVIDER_ACCEPTED`; tiếp tục poll/webhook | Giữ HOLD |
| Order `COMPLETE` | `ISSUED` | HOLD → SPEND một lần |
| Order `CANCELED` | Review reason; nếu chưa issue thì `FAILED` | RELEASE khi đủ bằng chứng |
| `order.delivery_complete` | delivery `SENT`/`DELIVERED` theo taxonomy chọn | Không đổi điểm nếu đã SPENT |
| `order.delivery_partial` | Exception; MVP 1 recipient nên phải điều tra | Không tự release |
| `order.bounced` | delivery `BOUNCED` | Không đổi điểm |
| resend accepted | `RESEND_REQUESTED` rồi theo event mới | Không đổi điểm |
| `recipient.redeemed` | Chưa dùng | Giữ `UNKNOWN` |

**[VER]** Webhook có thể không theo thứ tự; bounce được batch và có thể đến sau delivery complete. `recipient.redeemed` được tài liệu ghi “coming soon”. Nguồn: [Webhook events](https://api.giftronaut.com/docs/reference/webhooks).

## 11. Webhook contract và bảo mật

![Webhook processing](assets/04-webhook-processing.png)

[PlantUML](diagrams/04-webhook-processing.puml) · [SVG](assets/04-webhook-processing.svg)

Ở góc nhìn nghiệp vụ, callback chỉ được dùng để thay đổi giao dịch khi hệ thống xác minh nó đến từ Giftronaut, tìm được redemption tương ứng và sự thay đổi phù hợp với trạng thái hiện tại. Callback đến hai lần không được chốt điểm hai lần; callback đến muộn không được làm giao dịch quay về trạng thái cũ.

### 11.1. Ingress requirements [TGT]

- Endpoint public HTTPS riêng theo environment, ví dụ `/webhooks/giftronaut/v1`.
- Đọc **raw request body** trước khi parse JSON.
- Kiểm tra `X-Giftronaut-Signature` theo HMAC-SHA256, format `sha256={hex}`.
- Dùng constant-time comparison và secret lấy từ secret manager.
- Reject request thiếu/sai signature; không ghi full payload chứa PII vào standard log.
- Dedupe bằng `eventId` có unique constraint.
- Lưu event bất biến trước, trả 2xx nhanh, xử lý side effect bằng worker.
- Lưu `event_time` và `received_at` riêng; không giả định arrival order.
- Event không map được đi vào DLQ/exception queue, không bị drop im lặng.

### 11.2. Replay và secret rotation

- Nếu contract có timestamp header/tolerance, enforce theo tài liệu/tenant configuration trước go-live.
- Trong thời gian rotate, handler có thể verify bằng current và previous secret trong cửa sổ ngắn.
- Replay cùng `eventId` trả 2xx nhưng không tạo side effect thứ hai.
- Resend có thể sinh delivery event mới; chỉ dedupe theo `eventId`, không dedupe mù theo orderId/event type.

## 12. Error handling matrix

| Tình huống | Có retry? | Điểm | OP Points | ELLIS/Ops action |
|---|---|---|---|---|
| Input/email không hợp lệ | Không | Không hold hoặc release trong local tx | Sửa dữ liệu | Không tạo case trừ abuse pattern |
| Không đủ điểm | Không | Không hold | Báo balance thiếu | Audit business rejection |
| Provider trả `402 INSUFFICIENT_BALANCE` | Sau khi Finance nạp tiền | RELEASE hold vì đơn không được tạo | Thất bại tạm thời; điểm đã trả | ELLIS hiện code; Finance nạp thủ công qua portal |
| 400 validation từ provider | Không tự retry | Release khi chắc chắn no order | Thất bại có lý do an toàn | Mapping/config case |
| 401/403 | Refresh một lần; rồi dừng | Giữ hold | Processing | Incident credential/scope |
| 409 duplicate idempotency | Query đơn gốc | Giữ hold | Processing | Không tạo key mới |
| 429 | Có, theo reset + jitter | Giữ hold | Processing | Rate-limit metric/backpressure |
| 5xx | Có giới hạn | Giữ hold | Processing | Circuit breaker nếu ngưỡng vượt |
| Network timeout | Query trước retry | Giữ hold | Processing/verification | Case nếu quá SLA |
| Webhook signature sai | Không | Không đổi | Không ảnh hưởng | Security log/alert |
| Webhook duplicate | ACK, không side effect | Không đổi lần hai | Không ảnh hưởng | Dedupe metric |
| Webhook out of order | Query/canonicalize | Theo issuance canonical | Trạng thái cuối đúng | Case nếu transition không giải được |
| Email bounced | Resend theo action | Giữ SPENT | Hướng dẫn support | Xác nhận email, resend cùng order |
| Reconciliation mismatch | Không tự phát quà | Freeze action rủi ro | Processing/support state | Owner + SLA + evidence |

## 13. Dữ liệu và audit

![Data model](assets/06-data-model.png)

[PlantUML](diagrams/06-data-model.puml) · [SVG](assets/06-data-model.svg)

### 13.1. Invariant dữ liệu

- `client_request_id` unique theo OP/client scope.
- `provider idempotency_key` unique và immutable.
- Một redemption có tối đa một logical provider order trong MVP.
- `provider_event_id` unique.
- Tổng point transactions tạo balance; không update số dư bằng tay.
- `SPEND` không vượt hold của redemption; `RELEASE + SPEND` không vượt hold.
- Provider order ID có thể null khi đang submit/verify, nhưng khi có phải immutable trừ controlled repair có audit.
- Policy snapshot giữ product, points, amount, currency, refund/email template version tại thời điểm request.

### 13.2. Correlation và log

Mọi record/log có tối thiểu: `correlationId`, `redemptionId`, `clientRequestId`, `providerOrderId` nếu có, environment, action, result, timestamp và actor/service. Email chỉ hiển thị masked; payload nhạy cảm được mã hóa và retention theo policy.

## 14. Reconciliation [P2]

![Reconciliation](assets/07-reconciliation-flow.png)

[PlantUML](diagrams/07-reconciliation-flow.puml) · [SVG](assets/07-reconciliation-flow.svg)

Reconciliation trong phần này là cơ chế **kiểm tra theo lô sau giao dịch**, không phải flow dùng để hoàn tất từng redemption. Vì vậy nó thuộc P2. Các thao tác hỏi lại order ngay sau timeout hoặc callback bị mất vẫn thuộc P0 vì chúng nằm trong core transaction.

Trước khi P2 được triển khai, production pilot cần một báo cáo đơn giản và checklist kiểm tra thủ công hằng ngày cho các giao dịch còn `PROCESSING` quá thời gian cho phép.

### 14.1. Đối soát theo kỳ

| Loại | Tần suất đề xuất | Mục tiêu |
|---|---|---|
| Order reconciliation | Hằng giờ + daily close | Internal redemption ↔ Giftronaut order |
| Financial reconciliation | Daily | SPEND amount ↔ provider balance ledger debit |
| Full historical replay | Theo incident/month-end | Chứng minh không mất event hoặc side effect |

### 14.2. Mismatch taxonomy

| Code | Mismatch | Mức độ sự cố | Hướng xử lý |
|---|---|---|---|
| `PROVIDER_ORDER_INTERNAL_MISSING` | Provider có đơn, local thiếu link | Critical/High theo giá trị | Gắn lại khi match chắc chắn; không tạo đơn |
| `SPENT_PROVIDER_NOT_FOUND` | Đã spend nhưng provider không có đơn | Critical | Dừng auto action, điều tra thủ công |
| `ISSUED_POINTS_HELD` | Provider complete, điểm còn hold | High | Chốt spend nếu bằng chứng đầy đủ |
| `FAILED_POINTS_HELD` | Fail chắc chắn nhưng hold chưa release | High | Trả điểm nếu bằng chứng đầy đủ |
| `AMOUNT_MISMATCH` | Amount/currency lệch | Critical | Finance review; không tự sửa tiền/điểm |
| `BALANCE_LEDGER_MISMATCH` | Provider ledger không khớp order | Critical | Finance/provider case |
| `DELIVERY_STATE_DRIFT` | Trạng thái giao email hai bên lệch | Medium | Hỏi lại provider và cập nhật trạng thái chuẩn |

Mỗi case có amount, currency, age, evidence, owner, SLA, resolution code và approver. Không xóa case để “làm sạch” dashboard.

## 15. Balance và funding theo functional spec hiện tại

![Funding flow](assets/08-funding-low-balance.png)

[PlantUML](diagrams/08-funding-low-balance.puml) · [SVG](assets/08-funding-low-balance.svg)

### 15.1. Baseline đã được quyết định [P1]

- ELLIS gọi `GET /balance` và hiển thị available/pending cho Finance/Ops.
- Functional spec hiện tại quyết định **không có cảnh báo số dư tự động**.
- Finance kiểm tra balance theo lịch vận hành và trước giai đoạn promotion lớn.
- Finance nạp USD bằng chuyển khoản qua Giftronaut portal; thời gian xử lý và owner phải nằm trong runbook.
- Nếu create order trả `402 INSUFFICIENT_BALANCE`, order không được tạo, redemption thành `FAILED` và điểm được trả tự động. OP chỉ thấy thông báo chung; ELLIS thấy code nội bộ.
- `GET /balance/ledger` được dùng cho kiểm tra 1:1 và reconciliation, không quyết định trạng thái một redemption đang chạy.

### 15.2. Phần chỉ được làm qua change request [P3]

Tài liệu API hiện tại có endpoint ACH top-up, nhưng functional spec OMH chọn chuyển khoản thủ công và không dùng ACH. Chỉ đưa `balance.write`, funding API, auto-alert hoặc tự động dừng redemption vào scope khi Business/Finance phê duyệt change request, control và runbook mới.

## 16. Yêu cầu chức năng cho ELLIS

| ID | Requirement | Priority |
|---|---|---|
| EL-GF-01 | Cấu hình Choice Card `productId`, bốn mệnh giá và point cost đã được duyệt | P0 |
| EL-GF-02 | Xem tối thiểu một redemption/order trong sandbox để kiểm tra core flow | P0 |
| EL-GF-03 | Phân quyền và lưu dấu vết cho action quản trị | P0 |
| EL-GF-04 | Tìm theo redemption ID, order ID, email đã che, OP, company, trạng thái, ngày | P1 |
| EL-GF-05 | Timeline dễ đọc: giữ/chốt điểm, đặt quà, callback và support action | P1 |
| EL-GF-06 | Hiển thị trạng thái phát quà, giao email và sử dụng riêng | P1 |
| EL-GF-07 | Hỗ trợ gửi lại cùng gift khi OP không tự xử lý được | P1 |
| EL-GF-08 | Danh sách giao dịch bị kẹt/lỗi theo thời gian xử lý | P1 |
| EL-GF-09 | Hiển thị balance available/pending để Finance kiểm tra theo lịch | P1 |
| EL-GF-10 | Reconciliation cases và evidence export | P2 |
| EL-GF-11 | Funding request/cancel với maker-checker | P3 |

## 17. Yêu cầu trải nghiệm OP Points

- Trước confirm: hiện point cost, gift amount/currency, email masked, expiry/refund text đã duyệt.
- Sau submit: trả “Đang xử lý” cùng redemption ID; không dùng “Gift sent” trước provider confirmation.
- Khi issued/delivered: hiển thị đúng từng trạng thái và timestamp.
- Khi bounced: hiện “Check email and resend”, cho OP xác nhận/sửa email và gửi lại cùng gift; không hứa hoàn điểm.
- Khi verifying: không cho OP tạo lại cùng reward; cho xem trạng thái và SLA support.
- History phải dùng cùng source/state với ELLIS, nhưng ẩn provider/internal debug detail.
- Retry do double-click/reload phải trả resource cũ qua idempotency.

## 18. Security, privacy và compliance

| Control | Requirement |
|---|---|
| Secrets | Secret manager, rotation, environment isolation, không log |
| Transport | TLS; webhook public ingress giới hạn method/content type/size |
| AuthZ | Server-side RBAC và object-level scope cho OP/company/admin |
| PII | Encrypt email at rest, mask UI/log/export, retention và access audit |
| Webhook | HMAC verify trên raw body, constant-time compare, event dedupe |
| Data integrity | Append-only ledger/audit, unique constraints, optimistic locking |
| Abuse | Velocity/value limit, suspicious email/account pattern, kill switch |
| Admin action | Reason bắt buộc; maker-checker cho financial adjustment/funding |
| Vendor | DPA, subprocessor, data region/retention, incident notification cần review |

## 19. NFR, SLO và observability

Các con số dưới đây là **target đề xuất**, cần baseline/load test trước khi duyệt.

| ID | Target |
|---|---|
| NFR-01 | Internal create p95 ≤ 800 ms để hoàn tất validate + hold + enqueue, không chờ provider |
| NFR-02 | 99.9% API availability trong pilot window, loại planned maintenance đã thông báo |
| NFR-03 | 99% order được resolve khỏi SUBMITTING/VERIFYING trong 15 phút khi provider healthy |
| NFR-04 | Webhook ingress ACK p95 ≤ 500 ms sau verify + durable persist |
| NFR-05 | Duplicate financial effect bằng 0 trong replay/concurrency tests |
| NFR-06 | P0/P1: giao dịch bị kẹt phải có danh sách vận hành; balance được kiểm tra theo lịch; P2: daily reconciliation hoàn tất trước giờ business chốt |
| NFR-07 | RPO cho redemption/ledger bằng 0 ở committed DB transaction; RTO theo service tier được duyệt |
| NFR-08 | PII không xuất hiện trong standard log/metric/trace |

Metric/alert tối thiểu:

- create latency/success theo internal và provider;
- count/value theo issuance/delivery state;
- age của hold, submitting, verifying;
- 401/403/409/429/5xx/timeout rate;
- webhook invalid signature, duplicate, lag, DLQ;
- available/pending balance để phục vụ lịch kiểm tra Finance;
- reconciliation mismatch count/value/age khi P2 được triển khai;
- resend volume và repeat bounce;
- circuit breaker/gate state.

## 20. Test strategy

### 20.1. Các lớp kiểm thử

| Lớp | Nội dung |
|---|---|
| Contract | Schema/field/status/error của OAuth, catalog, orders, balance, webhook |
| Unit/state | Allowed transitions, ledger invariants, mapping/error classification |
| Integration sandbox | Create/query/resend/webhook/balance theo credential sandbox |
| Concurrency | Double click, parallel redeem vượt balance, duplicate worker/event |
| Resilience | Timeout trước/sau provider commit, 409, 429, 5xx, token expiry, webhook mất/trễ/ngược thứ tự |
| Security | Secret scan, RBAC/object scope, signature/replay, PII log/export |
| Reconciliation [P2] | Tạo thử từng loại sai lệch và xác minh evidence/resolution |
| UAT | OP status copy, Ops search/resend/case, Finance balance/close |

### 20.2. Golden scenarios bắt buộc

1. Happy path COMPLETE + delivery complete chỉ spend một lần.
2. Hai create cùng internal idempotency key trả cùng redemption.
3. Hai redeem đồng thời không làm available âm.
4. Provider tạo order nhưng response timeout; query tìm thấy và không tạo order thứ hai.
5. Duplicate provider key 409; hệ thống link đơn gốc.
6. 429 tuân `X-RateLimit-Reset`, không retry storm.
7. Webhook duplicate/out-of-order/replay không làm lùi state hoặc side effect trùng.
8. Bounce sau delivery complete chuyển delivery state nhưng giữ SPENT.
9. Resend email mới dùng cùng order, không phát gift/point transaction mới.
10. Provider trả 402: order không được tạo, điểm được trả và ELLIS hiển thị lý do nội bộ.
11. Admin ngoài scope không xem/action redemption của company khác.

Scenario P2: reconciliation phát hiện provider order thiếu local và tạo case/backfill có audit.

## 21. Kế hoạch tích hợp cho BA/PO

![Integration rollout](assets/09-integration-rollout.png)

[PlantUML](diagrams/09-integration-rollout.puml) · [SVG](assets/09-integration-rollout.svg)

### Phase 0 — Contract và policy

BA/PO tạo decision log và chốt: Choice Card `productId`/mệnh giá, point conversion, refund option, delivery copy, point commit timing, SLA, lịch kiểm tra balance, funding owner, quyền resend và data retention. Partnerships/Security xác nhận API Beta có thể dùng production theo contract.

**Exit criteria:** D-01 đến D-12 có owner; API scope matrix, state model, reason taxonomy và test data được sign-off.

### Phase 1 — Sandbox foundation

Engineering triển khai kết nối đăng nhập, Choice Card config sync, create/query order, callback, point hold/spend/release và các API nội bộ P0. QA dùng sandbox credentials và bộ dữ liệu đã được Product duyệt.

**Exit criteria:** happy path, concurrency, idempotency, timeout recovery, invalid signature và provider errors qua automated/integration test.

### Phase 2 — UAT và operational readiness

Xây OP self-service resend, ELLIS search/detail, danh sách giao dịch bị kẹt, balance panel, lịch kiểm tra, runbook và audit thuộc P1. Product/Ops/Finance chạy UAT từ lúc chọn quà đến khi transaction complete, bao gồm bounce, 402 và provider outage.

**Exit criteria:** không có quà hoặc point spend trùng; giao dịch bị kẹt có owner/action; support copy và daily manual control được duyệt.

### Phase 3 — Controlled production pilot

Mở theo cohort nhỏ, denomination/budget cap và kill switch. Theo dõi balance, error, point hold quá hạn và support ticket hằng ngày. Dùng báo cáo đơn giản để Finance/Ops kiểm tra thủ công trong pilot.

**Exit criteria:** KPI/guardrail trong cửa sổ pilot đạt target; Finance/Ops/Security ký mở rộng.

### Phase 4 — Automated reconciliation và scale [P2]

Sau khi core flow ổn định, xây đối soát order/point/provider ledger, màn hình mismatch và financial close report. Phase này giảm công việc kiểm tra thủ công và hỗ trợ mở rộng volume; không chặn việc hoàn thiện P0 trong sandbox.

**Exit criteria:** sai lệch được phát hiện theo kỳ, có severity/owner/evidence và không có action tài chính tự động khi chưa được duyệt.

## 22. Acceptance criteria

Phân nhóm để PO/BA ưu tiên nghiệm thu:

- **P0:** AC-01–AC-13, AC-17–AC-18, AC-25, AC-28–AC-29, AC-31–AC-32 và AC-35.
- **P1:** AC-14–AC-16, AC-19–AC-21, AC-26–AC-27, AC-30 và AC-33.
- **P2:** AC-22–AC-24 và AC-34.

| ID | Given / When | Then |
|---|---|---|
| AC-01 | OP Points gọi create | Browser chỉ gọi Ohmyhotel API; không thấy Giftronaut secret/token |
| AC-02 | Request hợp lệ | Point được hold atomic cùng redemption/outbox |
| AC-03 | Hai request đồng thời vượt available | Tối đa một hold thành công; balance không âm |
| AC-04 | Replay cùng key và payload | Trả redemption gốc; không hold/submit thêm |
| AC-05 | Cùng key nhưng payload khác | Trả conflict; không đổi state |
| AC-06 | Provider trả PENDING/IN_PROGRESS | Giữ hold và theo dõi orderId |
| AC-07 | Provider đạt COMPLETE | Hold chuyển SPEND đúng một lần |
| AC-08 | POST timeout sau khi provider tạo đơn | Hệ thống query theo clientOrderId và link đơn gốc |
| AC-09 | Provider trả duplicate key 409 | Không tạo key mới; query đơn gốc |
| AC-10 | Lỗi chắc chắn không tạo order | Hold release đúng một lần |
| AC-11 | Kết quả còn bất định | State VERIFYING và hold giữ nguyên |
| AC-12 | Webhook signature sai | Không đổi state; ghi security event |
| AC-13 | Webhook eventId lặp | ACK nhưng không side effect lần hai |
| AC-14 | Bounce đến sau delivery complete | Delivery thành BOUNCED; issuance/points không bị rollback |
| AC-15 | OP resend redemption bị bounce của chính mình | Dùng provider order cũ, không phát/trừ điểm mới |
| AC-16 | OP hoặc Ops sửa email khi resend | Lưu actor/old-new masked value/provider result; Ops có thêm reason/case |
| AC-17 | Rate limit 429 | Retry theo reset/backoff, không vượt concurrency cap |
| AC-18 | Token production hết hạn | Refresh an toàn; không log secret/token |
| AC-19 | Provider outage | Circuit breaker/gate hoạt động; request dở không mất |
| AC-20 | Create order trả 402 | Redemption Failed, điểm được trả; OP không thấy số dư provider |
| AC-21 | Finance nạp tiền và refresh ELLIS | Available/pending phản ánh response mới; không tự retry redemption Failed cũ |
| AC-22 | Provider có order, local thiếu link | Reconciliation tạo case/backfill có evidence |
| AC-23 | Local SPENT, provider không có order | Tạo sự cố Critical; không tự tạo order/adjust balance |
| AC-24 | Amount/currency mismatch | Dừng auto resolution và yêu cầu Finance review |
| AC-25 | OP xem redemption người khác | Server từ chối |
| AC-26 | Admin ngoài company scope | Server từ chối và security audit |
| AC-27 | Export có email | Mask/permission/retention áp dụng |
| AC-28 | Mệnh giá bị tắt hoặc provider config đổi sau quote | Create từ quote hết hiệu lực bị từ chối/requote |
| AC-29 | Policy thay đổi sau submit | Redemption giữ policy snapshot cũ |
| AC-30 | `recipient.redeemed` chưa hỗ trợ | Usage hiển thị UNKNOWN, không suy đoán |
| AC-31 | Webhook bị mất | P0 polling cuối cùng đưa state đúng |
| AC-32 | Event đến ngược thứ tự | State canonical không bị lùi |
| AC-33 | ELLIS mở detail | Timeline nối được point, request, order, events và actions |
| AC-34 | Daily close | Ledger/redemption/order/provider ledger đối soát có bằng chứng |
| AC-35 | Tạm dừng chương trình | Chặn submit mới đúng scope; vẫn xử lý đơn đang dở và webhook |

## 23. Quyết định còn mở

| ID | Quyết định | Khuyến nghị | Owner |
|---|---|---|---|
| D-01 | Choice Card `productId` và mệnh giá được tenant hỗ trợ | Xác nhận US$10/20/50/100 trong sandbox; chỉ bật option hợp lệ | Product + Partnerships |
| D-02 | Tỷ lệ point ↔ gift value và FX | Versioned policy; không dùng FX hôm nay sửa lịch sử | Product + Finance |
| D-03 | `refundOption` | MVP `false` nếu contract/business chấp nhận | Finance + Product |
| D-04 | Thời điểm point chuyển SPENT | Provider order `COMPLETE` | Product + Finance |
| D-05 | Timeout verification window/SLA | Chốt theo provider SLA và ops coverage | Engineering + Ops |
| D-06 | Lịch kiểm tra balance và cách xử lý 402 | Kiểm tra thủ công theo lịch; 402 = Failed + trả điểm | Product + Finance |
| D-07 | Email source/verification | Xác nhận masked email trước redeem; change có audit | Product + Security |
| D-08 | Sender/template/content/localization | Versioned approved config | Marketing + Product |
| D-09 | Quyền resend của OP và Ops | OP chỉ thao tác giao dịch của mình; Ops theo scoped support role | Ops + Security |
| D-10 | Funding route | Chuyển khoản portal; ACH/API chỉ qua change request | Finance |
| D-11 | Data retention/DPA/region | Chốt theo Legal/Security/vendor contract | Legal + Security |
| D-12 | Pilot cap, success và stop condition | Cohort + daily value cap + kill switch | Business + Finance |

## 24. Go-live checklist

- Contract/API Beta usage, pricing, fee, country, expiry/refund, support escalation đã ký.
- Production app/scopes/secrets/webhook endpoint tách sandbox và đã rotate thử.
- D-01–D-12 được phê duyệt, không còn assumption ngầm trong code.
- Ledger invariant, idempotency, concurrency và timeout recovery qua test.
- Webhook HMAC, dedupe, out-of-order và polling fallback qua test.
- Báo cáo giao dịch và daily manual control được Finance/Ops sign-off; automated reconciliation được theo dõi như P2.
- ELLIS exception queue, resend, RBAC, audit và runbooks sẵn sàng.
- Lịch kiểm tra balance, funding owner và incident contacts được cấu hình.
- OP copy thể hiện đúng `PROCESSING`, `ISSUED`, `BOUNCED`, `FAILED`.
- Dashboard giao dịch, provider error handling, circuit breaker và kill switch được diễn tập.
- Pilot cohort, budget cap, SLA và rollback/stop plan được phê duyệt.

## 25. Nguồn và giới hạn

Nguồn chính thức được kiểm tra ngày 14/10/2026:

1. [Giftronaut API overview](https://api.giftronaut.com/docs).
2. [API reference và base URL](https://api.giftronaut.com/docs/reference).
3. [Quickstart — OAuth, rate limit và idempotency](https://api.giftronaut.com/docs/quickstart).
4. [Orders API](https://api.giftronaut.com/docs/reference/orders).
5. [Catalog API](https://api.giftronaut.com/docs/reference/catalog).
6. [Balance API](https://api.giftronaut.com/docs/reference/balance).
7. [Webhook events](https://api.giftronaut.com/docs/reference/webhooks).
8. [Ghi chú nguồn và khác biệt](sources/SOURCE-NOTES.md).

Nguồn nội bộ:

- OP Points Functional Spec VI v1.1 *(external source; file is not stored in this repository)* — harness chính dùng để kiểm tra product fit.
- [OP Points BRD/PRD](../../02-domain-specifications/op-points/OP-Points-BRD-PRD.md).
- [ELLIS BRD/PRD](../../02-domain-specifications/ellis-config/ELLIS-BRD-PRD.md).
- [OP Points — ELLIS integrated proposal](../../03-product-proposals/op-points-ellis-integrated/OP-POINTS-ELLIS-INTEGRATED-PROPOSAL.md).
- [Ohmy Partners prototype](https://bstars00-rgb.github.io/B2B-System/).

Giftronaut ghi API là **Beta**, vì vậy endpoint/schema/business rule có thể thay đổi. Tài liệu này là BRD/PRD và target integration contract để review; không thay thế commercial contract, tenant-specific API spec, production log audit, DPA hoặc security assessment.

## 26. Cấu trúc artifact và cách render

```text
04-external-integrations/giftronaut/
  OP-POINTS-ELLIS-GIFTRONAUT-INTEGRATION-BRD-PRD.md
  OP-POINTS-ELLIS-GIFTRONAUT-INTEGRATION-BRD-PRD.html
  diagrams/   15 PlantUML source files
  assets/     PNG và SVG đã render
  sources/    Source notes
  build_docs.py
```

Render lại từ workspace root:

```powershell
python docs/04-external-integrations/giftronaut/build_docs.py
```
