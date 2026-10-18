# Source notes — Giftronaut integration

Ngày kiểm tra lại tài liệu công khai: **18/10/2026**. Bản hiện hành: **Đặc tả tích hợp v2.6**.

## Bổ sung rule BA v2.6

- Bổ sung rule nghiệp vụ cho availability theo thị trường, quota tổng giá trị quà, cảnh báo số dư thấp, Issued Total/đối soát và usage/expiry.
- Các rule OMH được ghi là Đề xuất. Những dữ liệu hoặc hành vi chưa có bằng chứng từ Giftronaut được đưa vào danh sách cần chốt, không được ghi như contract đối tác đã xác nhận.

## Điều chỉnh bản đồ API và field contract v2.5

- Bản đồ API hiển thị như một khối nội dung bình thường, không dùng bố cục sơ đồ bên trái và phần giải thích bên phải.
- Chuẩn hóa tuyến mũi tên SVG của luồng đổi quà chính để không chạy qua ô API khác; các nhánh webhook, tra cứu và số dư vẫn có ô riêng, liên kết đến đặc tả và được giải thích trong ghi chú bên dưới.
- Hoàn thiện bảng request/response riêng cho G4, G5, G6, G7 và G8. Toàn bộ G1–G8 có field, kiểu dữ liệu, bắt buộc/không bắt buộc và ý nghĩa; field chưa có schema công khai được ghi rõ cần xác nhận trong sandbox.

## Điều chỉnh bản đồ API v2.4

- HTML không còn hiển thị sơ đồ PlantUML cho bản đồ API. Thay vào đó là SVG tương tác giống bản đồ flow; mỗi ô I/G dẫn thẳng đến đặc tả API.
- Bản đồ API dùng panel thông thường (`position: static`), nên không dính khi cuộn. PlantUML 25 vẫn giữ làm source nội bộ/ảnh dự phòng, không phải thành phần hiển thị trong HTML.

## API map và field contract v2.3

- Bổ sung sơ đồ 25 để thấy quan hệ giữa OP Points/ELLIS, API Ohmyhotel đề xuất, sổ điểm và Giftronaut.
- G1–G8 có bảng field request/response; I1–I9 có field contract riêng. Field chưa có schema công khai được đánh dấu cần xác nhận sandbox.
- Mã I/G trong HTML là link nội bộ tới đặc tả API tương ứng. Nguồn chính thức Giftronaut vẫn nằm dưới tiêu đề mỗi API G.

## Setup và trình bày v2.2

- Đọc bổ sung [Sandbox vs Production](https://api.giftronaut.com/docs/guides/sandbox), [Authentication](https://api.giftronaut.com/docs/guides/authentication), [Webhook setup](https://api.giftronaut.com/docs/guides/webhooks).
- F0 bổ sung tạo App, scopes, lưu cấu hình OMH đề xuất, Client Credentials, production server-to-server approval/IP allowlist, challenge đăng ký webhook và Send Test. Sandbox không chứng minh giao email thật.
- Webhook guide nêu retry và challenge; bản mới phân biệt challenge đăng ký với event envelope, không áp dụng ACK 204 cho challenge.
- HTML v2.2 có flowchart link trực tiếp tới F0–F5 (F2a/F2b), sơ đồ bên trái, giải thích/ví dụ đóng mở bên phải; màn hình nhỏ xếp dọc. Script build dùng flow_layout.py; check_html.py kiểm tra tương tác bằng Chromium headless được cung cấp qua --browser.
- Toàn bộ API, trạng thái và mapping OMH là Đề xuất. Mỗi G1–G8 có link nguồn ngay dưới tiêu đề. Chưa gọi API sandbox thực.

## Bổ sung flow v2.1

Giữ nguyên API spec v2.0; dùng các contract đã đối chiếu để bổ sung sơ đồ 18–23: cấu hình, tạo yêu cầu, nhận kết quả, xác minh lỗi, resend và số dư. Mỗi flow nêu hệ thống tham gia, method/path, điều kiện và edge case. Sơ đồ 16–17 tiếp tục dùng cho tổng quan và trạng thái. Không bổ sung endpoint đối tác hoặc khẳng định đã chạy sandbox.

## Kết quả rà soát v2.0

- Đã đọc lại Orders, Catalog, Balance, Webhook, Quickstart và các guide Authentication, Errors, Idempotency, Rate limits qua web. Chưa có credentials để thực hiện sandbox contract test.
- [Errors guide](https://api.giftronaut.com/docs/guides/errors): mã lỗi chung; 429 dùng `error/error_description`, khác `code/message/details`.
- [Idempotency](https://api.giftronaut.com/docs/guides/idempotency): duplicate 409 cần lookup bằng `clientOrderId`; không mặc định response replay đơn gốc.
- [Authentication](https://api.giftronaut.com/docs/guides/authentication): Client Credentials và token response.
- [Balance guide](https://api.giftronaut.com/docs/guides/balance): xác nhận 402 `INSUFFICIENT_BALANCE` và balance response wrapper.
- [Rate limits](https://api.giftronaut.com/docs/guides/rate-limits) và Quickstart ghi ngược giới hạn sandbox/production, khác cả phạm vi org/client. Bản mới không khẳng định con số cũ là đúng; cần GF xác nhận và đọc response headers.
- Catalog Choice Card dùng range của organization, không phải danh sách price point cố định của branded card. Mệnh giá 10/20/50/100 USD do OMH chọn và phải nằm trong range.
- API reference chưa thể hiện đầy đủ response schema cho mọi endpoint. Ví dụ trích trường trong bản BA không phải response đã kiểm thử; danh sách cần xác nhận nằm ở D5/D7/D8.
- Đối chiếu công thức điểm với OP Points BRD/PRD mục 9: ví dụ demo 20 USD × 1.480 KRW/USD ÷ 1.000 KRW/P = 29,6P; không dùng ví dụ 2.500P thiếu cơ sở của bản cũ.
- `PREVIOUS-v1.4.md` và các sơ đồ 00–15 là lịch sử trước khi đơn giản hóa; không dùng như contract hiện hành. Sơ đồ 16–17 phục vụ bản v2.0.

## Nguồn chính thức

- [Giftronaut API overview](https://api.giftronaut.com/docs)
- [API reference và base URL](https://api.giftronaut.com/docs/reference)
- [Quickstart: OAuth2, rate limit, idempotency](https://api.giftronaut.com/docs/quickstart)
- [Orders API](https://api.giftronaut.com/docs/reference/orders)
- [Catalog API](https://api.giftronaut.com/docs/reference/catalog)
- [Balance API](https://api.giftronaut.com/docs/reference/balance)
- [Webhook events](https://api.giftronaut.com/docs/reference/webhooks)

Giftronaut gắn nhãn API là **Beta**. Endpoint, scope và business rule phải được đối chiếu lại với contract/tenant thật trước khi production.

## Nguồn nội bộ và quan sát

- OP Points Functional Spec VI v1.1 *(external source; file is not stored in this repository)* — source ưu tiên cho harness fit check; xác nhận prototype mô phỏng, Choice Card cố định, OP self-service resend, balance check thủ công và production gaps.
- [OP Points BRD/PRD](../../../02-domain-specifications/op-points/OP-Points-BRD-PRD.md)
- [ELLIS BRD/PRD](../../../02-domain-specifications/ellis-config/ELLIS-BRD-PRD.md)
- [Đề xuất tích hợp OP Points — ELLIS](../../../03-product-proposals/op-points-ellis-integrated/OP-POINTS-ELLIS-INTEGRATED-PROPOSAL.md)
- [Prototype Ohmy Partners](https://bstars00-rgb.github.io/B2B-System/)

Prototype chỉ chứng minh hành vi UI mô phỏng. Không có backend source, production credentials, provider logs hay network evidence trong workspace để kết luận một tích hợp production khác có tồn tại hay không.

## Khác biệt so với trao đổi cũ

Tài liệu chính thức hiện tại có `POST /api/v1/balance/charge` và thao tác hủy ACH top-up. Vì API đang Beta và funding là tác vụ tài chính nhạy cảm, đề xuất Phase 1 chỉ dùng `balance.read` để theo dõi; Finance tiếp tục nạp qua quy trình được duyệt. Chỉ bật `balance.write` sau khi contract, quyền, maker-checker và runbook đã được phê duyệt.
