# HTKK 5.8.5 reference files for 01/GTGT

These files were copied from the static templates in the locally installed HTKK 5.8.5 package, under `InterfaceTemplates`. They are retained as versioned test/reference inputs; they do not establish legal applicability by themselves.

## File roles

- `InterfaceTemplates/xml/01_GTGT_TT89_xml_309.xml` is an XML return-template/sample (`HSoThueDTu`). It is a **tax-return XML**, not an e-invoice XML.
- `InterfaceTemplates/xml/01_GTGT_TT89_309.xml` is HTKK's `Sections/Cells` spreadsheet-import layout metadata. It is neither a return XML nor an invoice XML.
- `InterfaceTemplates/Validate/01_GTGT_TT89_309.xsd` is the corresponding validation schema. Its relative dependency on `InterfaceTemplates/TKhaiThue_DBHC.xsd` is preserved.
- SHA-256 values below identify the exact source copies.

## Verification

The sample `01_GTGT_TT89_xml_309.xml` was read with the HTKK 5.8.5 XSD dependency and validated locally against `01_GTGT_TT89_309.xsd`: **PASS**. This validates that supplied sample against the supplied schema; it does not prove HTKK/eTax acceptance of generated output or authorize filing.

## Scope and provenance limits

The local `HTKK_SAMPLES_5.8.5` collection contains 4,096 files (about 289 MB). This source snapshot includes only the directly relevant 01/GTGT XML/XSD reference files rather than the full multi-tax corpus. Other spreadsheets in the working folder were not copied because they may contain real employee or business data. The source corpus remains at the user's local folder.

The five PDFs in `legal/source-files` were copied verbatim from the working folder supplied for this task. Their SHA-256 values provide integrity checks only; this change does not independently certify their origin, effective dates, or current legal applicability. No tax rules or form mappings were automatically changed based on those files.

## SHA-256

| Relative path | SHA-256 |
|---|---|
| `InterfaceTemplates/xml/01_GTGT_TT89_xml_309.xml` | `6617D38E8391AD72EDA2874B62E518E812AFC6FD7A2F3B8779D2E41B1AB1E4DD` |
| `InterfaceTemplates/xml/01_GTGT_TT89_309.xml` | `BA96834481A4B5B8A1C803572D10FAFB669538402ED06F80A504C3212488638A` |
| `InterfaceTemplates/Validate/01_GTGT_TT89_309.xsd` | `8481F7C98CA9E008742552BDA4F7ECC814CB91D453584B179FDF2D7767D9DA19` |
| `InterfaceTemplates/TKhaiThue_DBHC.xsd` | `ABA7F2ACBC9332CAAF3EB2DA9A081A3D876DDC7813D6230921DA48C775460011` |



## XML nháp 01/GTGT

Bộ xuất tái sử dụng pipeline GTGT và các mẫu trắng HTKK riêng cho TT80/TT89. Nó ánh xạ chỉ tiêu được phân loại tường minh, MST đã cung cấp và kỳ kê khai; giữ nguyên cây phần tử mẫu. XSD ghi kỳ tháng `MM/YYYY`, kỳ quý `Q/YYYY`, ngày đầu/cuối quý `DD/MM/YYYY`. Mẫu TT80 trong gói 5.8.5 còn có các trường địa chỉ cũ. Bộ xuất từ chối mapping thiếu và chỉ tiêu không thuộc phiên bản mẫu. XML sinh ra vẫn là bản nháp; tên/địa chỉ doanh nghiệp, cơ quan thuế, loại tờ khai, chữ ký và phụ lục chưa có đầu vào sẽ để trống. Test so sánh cấu trúc và đọc lại dữ liệu giả lập; chưa thử nhập HTKK/eTax.
