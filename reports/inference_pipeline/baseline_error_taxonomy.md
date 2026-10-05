# Baseline error taxonomy

Status: saved full-dev snapshot; current service R0 rerun and EOS cause probe pending.

Records: 2783; BLEU: 33.728281; chrF++: 60.295810.
Dev SHA256: `a701f808ae84ab202bf89bd5d336bcddd02a43655a7c3637254d525258aa781b`
Adapter SHA256: `bca5c144efc084137379c0fb8774c9aea3c741781c687b0d972cfd9f756e3986`

| Label | Heuristic count | Rate |
|---|---:|---:|
| E1 | 0 | 0.000% |
| E2 | 2167 | 77.866% |
| E3 | 124 | 4.456% |
| E4 | 0 | 0.000% |
| E5 | 2191 | 78.728% |
| E6 | 121 | 4.348% |
| E7 | 0 | 0.000% |

E7 is unmeasured (no approved glossary), not zero confirmed errors.
E2 counts missing structural markers, not confirmed missing meaning. E6 checks identifiers only at M0.
EOS/cap cannot be inferred from saved text. No conclusion that ngram3 causes truncation.

## Metric signatures
- BLEU: `nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.6.0`
- chrF++: `nrefs:1|case:mixed|eff:yes|nc:6|nw:2|space:no|version:2.6.0`

## E1: 0 available examples (up to 20)

## E2: 20 available examples (up to 20)

### Bat_dong_san/113::segment-0003::vi2en

Source:
```text
1. Sửa đổi, bổ sung khoản 5 Điều 3 như sau:

“5. Kinh phí phục vụ cho việc xây dựng, điều chỉnh kế hoạch phát triển nhà ở của địa phương được xác định như sau:
a) Kinh phí lập kế hoạch phát triển nhà ở kỳ 05 năm và năm đầu kỳ chương trình không vượt quá 50% tổng mức kinh phí xây dựng chương trình phát triển nhà ở mới được xác định tại thời điểm lập dự toán; kinh phí phục vụ cho việc nghiên cứu để điều chỉnh kế hoạch phát triển nhà ở kỳ 05 năm không vượt quá 60% tổng mức kinh phí xây dựng kế hoạch phát triển nhà ở quy định tại điểm này;

b) Kinh phí lập kế hoạch phát triển nhà ở hàng năm (trừ năm đầu kỳ chương trình) không vượt quá 20% tổng mức kinh phí xây dựng chương trình phát triển nhà ở mới được xác định tại thời điểm lập dự toán; kinh phí phục vụ cho lập điều chỉnh kế hoạch phát triển nhà ở hàng năm không vượt quá 60% tổng mức kinh phí xây dựng kế hoạch phát triển nhà ở hàng năm quy định tại điểm này.

2. Bổ sung Điều 3a vào sau Điều 3 như sau:
```
Prediction:
```text
1. Clause 5 Article 3 is amended as follows: “5. Funding for formulation and adjustment of local housing development plans shall be determined as follow: a) Funding used for formulating housing development plan for the 5th and first year of the program period shall not exceed 50% of total funding for formulate new housing development program determined at the time of estimation; funding used for research for adjustment to housing development planning for the 05th period shall be not exceed 60% of total fund for formulated housing development Plan specified at this point; b) Fundings used for making annual housing development (except for the first year) shall not be exceed 20% of total expenditure for formulates new housing Development Program defined at time of calculation; funds used for preparing adjustments to annual housing Development Plan shall not excess 60% of the total expended for formulations of annual housing growth Plan as specified in this point. 2. Article 3a shall be added after Article 3 as follow
```

### Bat_dong_san/113::segment-0004::vi2en

Source:
```text
“Điều 3a. Tiêu chí xác định nhu cầu nhà ở để xây dựng chương trình, kế hoạch phát triển nhà ở
Việc xác định nhu cầu về nhà ở khi xây dựng chương trình, kế hoạch phát triển nhà ở của địa phương được căn cứ vào các tiêu chí sau đây:

1. Các chỉ tiêu, yêu cầu về phát triển nhà ở nêu trong Chiến lược phát triển nhà ở quốc gia được Thủ tướng Chính phủ phê duyệt.

2. Các chỉ tiêu liên quan đến phát triển nhà ở nêu trong quy hoạch tỉnh, quy hoạch xây dựng của địa phương của giai đoạn thực hiện chương trình, kế hoạch phát triển nhà ở đã được cơ quan có thẩm quyền phê duyệt.
3. Quỹ đất dành cho phát triển nhà ở được xác định trong quy hoạch xây dựng, quy hoạch, kế hoạch sử dụng đất của địa phương đã được cơ quan có thẩm quyền phê duyệt.

4. Nhu cầu về diện tích nhà ở của từng đối tượng trên địa bàn theo quy định tại Điều 49 của Luật Nhà ở.

5. Các cơ chế, chính sách hỗ trợ nhà ở do Nhà nước ban hành tại thời điểm nghiên cứu, xây dựng chương trình, kế hoạch phát triển nhà ở.
```
Prediction:
```text
“Article 3a. Criteria for determination of housing demand for development of housing development programs and plans The determination on housing demand when developing local housing development program and plan shall be based on the following criteria: 1. Criteria and requirements for housing development stated in the national housing development strategy approved by the Prime Minister. 2. Criteria related to housing development specified in provincial planning, local construction planning of the stage of implementation of the housing development plan and program approved by competent agencies. 3. Land funds for housing growth shall be determined in construction planning, land use planning and plan of the locality approved by a competent agency. 4. Demand for housing area of each subject in the area under the provisions of Article 49 of the Housing Law. 5. Housing support mechanisms and policies issued by the State at the time of research and development of the program and plans for housing.
```

### Bat_dong_san/113::segment-0005::vi2en

Source:
```text
6. Thực trạng về diện tích nhà ở trên địa bàn do cơ quan có thẩm quyền cung cấp tại thời điểm xây dựng chương trình, kế hoạch phát triển nhà ở; thực trạng về nhà ở thương mại, nhà ở xã hội, nhà ở công vụ, nhà ở phục vụ tái định cư, nhà ở cho các hộ nghèo tại khu vực nông thôn và nhà ở cho các đối tượng khác trong giai đoạn 05 năm hoặc 10 năm trước đây.

7. Thực trạng về dân số và thu nhập bình quân đầu người trên địa bàn tại thời điểm xây dựng chương trình, kế hoạch, dự kiến mức tăng dân số tự nhiên, dân số cơ học do cơ quan có thẩm quyền cung cấp trong giai đoạn thực hiện chương trình, kế hoạch phát triển nhà ở.
8. Dự kiến khả năng tài chính từ ngân sách của địa phương để hỗ trợ xây dựng nhà ở dành cho các đối tượng thuộc diện được hưởng chính sách nhà ở xã hội.”
```
Prediction:
```text
6. Current housing area in the administrative division provided by competent authorities at the time of formulation of housing development programs and plans; current commercial housing, social housing, official residence, housing for resettlement, housing provided for poor households in rural areas and housing for other entities in the previous 05 years or 10 years. 7. Current population and per capita income in the local division at the moment of formulating programs, plans, estimated natural population growth, mechanical population provided by the competent authority during the implementation of housing Development Programs and Plans. 8. Estimated financial capacity from the local budget to support the construction of housing for the subjects entitled to social housing policies.”
```

### Bat_dong_san/123::segment-0001::vi2en

Source:
```text
Căn cứ Luật Tiêu chuẩn và Quy chuẩn kỹ thuật ngày 29 tháng 6 năm 2006;
Căn cứ Luật Chất lượng sản phẩm, hàng hóa ngày 21 tháng 11 năm 2007;

Căn cứ Luật An toàn thực phẩm ngày 17 tháng 6 năm 2010;
Căn cứ Luật Dược ngày 14 tháng 6 năm 2015;

Căn cứ Nghị định số 109/2018/NĐ-CP ngày 29 tháng 8 năm 2018 của Chính phủ về nông nghiệp hữu cơ;
Căn cứ Quyết định số 1819/QĐ-TTg ngày 16 tháng 11 năm 2017 của Thủ tướng Chính phủ phê duyệt Kế hoạch cơ cấu lại ngành nông nghiệp giai đoạn 2017- 2020;

Theo đề nghị của Bộ trưởng Bộ Nông nghiệp và Phát triển nông thôn.
QUYẾT ĐỊNH:

Điều 1. Phê duyệt “Đề án phát triển nông nghiệp hữu cơ giai đoạn 2020- 2030” với các nội dung chủ yếu

sau:
I. QUAN ĐIỂM

1. Đề án phát triển nông nghiệp hữu cơ giai đoạn 2020 - 2030 (sau đây gọi tắt là Đề án) nhằm phục vụ Đề án tái cơ cấu ngành nông nghiệp theo hướng nâng cao giá trị gia tăng và phát triển bền vững, thực hiện các chương trình mục tiêu quốc gia và phát huy tiềm năng thế mạnh về nông nghiệp hữu cơ của các vùng miền và địa phương.
```
Prediction:
```text
Pursuant to the Law on Standards and Technical Regulations dated June 29, 2006; Pursuance to the November 21, 2007 Law on Product and Goods Quality; Purpose to the June 17, 2010 Law on Food Safety; PurSUant to Law on Pharmacy dated July 14, 2015; Purchasing from the Government’s Decree No. 109/2018/ND-CP dated August 29, 2018 on organic agriculture; Purchase from the Prime Minister’s Decision No. 1819/QD-TTg dated November 16, 2017 approving the Agricultural Restructuring Plan for the period of 2017- 2020; Upon the proposal of the Minister of Agriculture and Rural Development. DECISION: Article 1. The scheme for organic  agricultural development for the 2020- 2030 period is approved with the following main contents: I. VIEWPOINTS 1. The Scheme for organic agricultural growth for the 2019-2020 period (hereinafter referred to as “the Scheme") is aimed at serving the Scheme on agricultural restructuring towards value-added improvement and sustainable development, implementation of national target programs and promotion of potential and strengths in organic tourism of regions and localities.
```

### Bat_dong_san/123::segment-0002::vi2en

Source:
```text
2. Phát triển nông nghiệp hữu cơ gắn với mục tiêu bảo vệ môi trường, phát triển đa dạng sinh học, góp phần phát triển du lịch, dịch vụ.
3. Phát triển nông nghiệp hữu cơ phải được triển khai cả về chiều rộng và chiều sâu theo hướng: tăng cường áp dụng rộng rãi các biện pháp hữu cơ (phân bón hữu cơ, thuốc sinh học...) trong sản xuất nông nghiệp và từng bước tăng dần tỷ lệ sản phẩm hữu cơ được chứng nhận theo yêu cầu của thị trường trong nước và thế giới.

4. Phát triển nông nghiệp hữu cơ ở các quy mô, cấp độ từ hộ gia đình, tổ hợp tác, hợp tác xã, doanh nghiệp nhằm tạo ra thực phẩm hữu cơ, môi trường an toàn cho người nông dân và sản phẩm hàng hóa có giá trị gia tăng cao.

5. Phát triển nông nghiệp hữu cơ phải huy động sự tham gia của các nhà quản lý, nhà khoa học, các tổ chức quốc tế, các thành phần kinh tế, đặc biệt là doanh nghiệp, hợp tác xã, hộ gia đình.

II. MỤC TIÊU

1. Mục tiêu tổng quát
```
Prediction:
```text
2. Develop organic agriculture in association with environmental protection and biodiversity development, contributing to tourism and service development. 3. Develop organic farming in both width and depth with the aim of widely applying organic measures (organic fertilizers, biological drugs, etc.) in agricultural production and gradually increasing the rate of certified organic products according to the requirements of the domestic and international markets. 4. Develop organic agricultural farming at household, cooperative, cooperatives and enterprise scales and levels in order to create organic food, a safe environment for farmers and high-value-added products. 5. Developing organic  farming with the participation of managers, scientists, international organizations, economic sectors, especially enterprises, cooperations and households. II. OBJECTIVES 1. General objectives
```

### Bat_dong_san/123::segment-0003::vi2en

Source:
```text
Phát triển nền nông nghiệp hữu cơ có giá trị gia tăng cao, bền vững, thân thiện với môi trường sinh thái, gắn với kinh tế nông nghiệp tuần hoàn phục vụ tiêu dùng trong nước và xuất khẩu. Sản phẩm nông nghiệp hữu cơ được chứng nhận phù hợp với tiêu chuẩn nông nghiệp hữu cơ của khu vực và thế giới; đưa Việt Nam trở thành quốc gia có trình độ sản xuất nông nghiệp hữu cơ ngang bằng các nước tiên tiến trên thế giới.

2. Mục tiêu cụ thể

a) Đến năm 2025
- Diện tích nhóm đất nông nghiệp sản xuất hữu cơ đạt khoảng 1,5-2% tổng diện tích nhóm đất nông nghiệp.

- Diện tích đất trồng trọt hữu cơ đạt khoảng trên 1% tổng diện tích đất trồng trọt với các cây trồng chủ lực: lúa, rau đậu các loại, cây ăn quả, chè, hồ tiêu, cà phê, điều, dừa...

- Tỷ lệ sản phẩm chăn nuôi hữu cơ đạt khoảng 1 - 2% tính trên tổng sản phẩm chăn nuôi sản xuất trong nước.
Các sản phẩm chăn nuôi được chứng nhận hữu cơ theo tiềm năng thế mạnh được ưu tiên: Sữa, sản phẩm mật ong, sản phẩm yến sào, thịt gia súc gia cầm...
```
Prediction:
```text
To develop organic agriculture with high added value, sustainability and eco-friendliness, in association with the cyclic agricultural economy for domestic consumption and export. Organic agricultural products will be certified to conform to regional and world organic  agricultural standards; making Vietnam a country with organic agricultural production level equal to that of advanced countries in the world. 2. Specific objectives a) By 2025. - The area of organic agriculturally-produced land will account for around 1.5-2% of the total area of agricultural land. - Organic farming land will make up over 1% of the land area under major crops: rice, legumes, fruit trees, tea, pepper, coffee, cashew, coconut, etc. - Percentage of organic animal husbandry products will account to around 1 - 2% of the domestic animal husbandRY product. Animal husbandry production products certified organic according to their potential and strengths will be prioritized: Milk, honey products, bird's nest products, cattle and poultry meat, etc
```

### Bat_dong_san/123::segment-0004::vi2en

Source:
```text
- Diện tích nuôi trồng thủy sản hữu cơ đạt khoảng 0,5-1,5% tổng diện tích nuôi trồng thủy sản, trong đó một số loài thủy đặc sản có giá trị kinh tế: tôm nước lợ, tôm càng xanh, các loài thủy sản bản địa...

- Diện tích sản xuất muối dinh dưỡng hữu cơ đạt khoảng 5 - 10% tổng diện tích sản xuất muối dinh dưỡng.

- Đối với sản phẩm dược liệu và lâm sản ngoài gỗ từ tự nhiên, tỷ lệ sản lượng hữu cơ trên tổng sản lượng đạt khoảng 90 - 95%, đối với hình thức thâm canh (sử dụng môi trường rừng để sản xuất) tỷ lệ sản lượng hữu cơ trên tổng sản lượng đạt khoảng 75 - 80%.

- Nâng cao hiệu quả của sản xuất hữu cơ trên một đơn vị diện tích; giá trị sản phẩm trên 01 ha đất trồng trọt và nuôi trồng thủy sản hữu cơ cao gấp 1,3 - 1,5 lần so với sản xuất phi hữu cơ.
```
Prediction:
```text
- The area for organic aquaculture shall be 0.5 - 1.5% of the total area for aquaculture, including some specialty aquatic species of economic value: brackish-water shrimp, giant river prawn, native aquatic animals, etc. - The areas for production of organic nutritious salt shall be 5 - 10% of the area for production. - For non-timber medicinal products and forest products from nature, the ratio of organic output to total output shall be 90 - 95%; for intensive farming (using forest environment for production), the ratio between organic output and total output is 75 - 80%. - To raise the efficiency of organic production per acreage unit; the value of products per hectare of organic land shall be 1.3 - 1.5 times higher than that of non-organic production.
```

### Bat_dong_san/123::segment-0005::vi2en

Source:
```text
- Sản xuất và tiêu thụ phân bón hữu cơ trong nước đạt 3 triệu tấn vào năm 2020 và tăng dần trong các năm tiếp theo, tăng tỷ lệ sản phẩm phân bón hữu cơ trong tổng sản phẩm phân bón lên 15% năm 2025; tăng số lượng thuốc bảo vệ thực vật sinh học trong danh mục thuốc bảo vệ thực vật được phép sử dụng lên trên 30%.

b) Đến năm 2030
- Diện tích nhóm đất nông nghiệp sản xuất hữu cơ đạt khoảng 2,5 - 3% tổng diện tích nhóm đất nông nghiệp.

- Diện tích đất trồng trọt hữu cơ đạt khoảng trên 2% tổng diện tích đất trồng trọt với các cây trồng chủ lực: lúa, rau đậu các loại, cây ăn quả, chè, hồ tiêu, cà phê, điều, dừa...

- Tỷ lệ sản phẩm chăn nuôi hữu cơ đạt khoảng 2-3% tính trên tổng sản phẩm chăn nuôi sản xuất trong nước. Các sản phẩm chăn nuôi được chứng nhận hữu cơ bao gồm: Sữa, sản phẩm mật ong, sản phẩm yến sào, thịt gia súc gia cầm...
```
Prediction:
```text
- Domestic production and consumption of organic fertilizers will reach 3 million tonnes by 2020 and gradually increase in the following years, increasing the proportion of organic products in total fertilizer products to 15% by 2025; increasing the number of biological pesticides in the list of pesticide permitted for use to over 30%. b) By 2030 - Area of agricultural land for organic production will reach about 2.5 - 3% of the total area of the agricultural area group. - Organic farming land area will reach over 2% of total farming area with key crops: rice, legumes of all kinds, fruit trees, tea, pepper, coffee, cashew, coconut, etc. - The percentage of organic animal husbandry products will reach around 2-3% of total domestic animal production. The certified organic animal breeding products include: Milk, honey products, bird's nest products, cattle and poultry meat, etc
```

### Bat_dong_san/123::segment-0006::vi2en

Source:
```text
- Diện tích nuôi trồng thủy sản hữu cơ đạt khoảng 1,5 - 3% tổng diện tích nuôi trồng thủy sản, trong đó một số loài thủy đặc sản có giá trị kinh tế: tôm nước lợ, tôm càng xanh, các loài thủy sản bản địa...

- Diện tích sản xuất muối dinh dưỡng hữu cơ đạt khoảng trên 10% tổng diện tích sản xuất muối dinh dưỡng.

- Đối với sản phẩm dược liệu và lâm sản ngoài gỗ từ tự nhiên, tỷ lệ sản lượng hữu cơ trên tổng sản lượng đạt khoảng 95 - 98%, đối với hình thức thâm canh (sử dụng môi trường rừng để sản xuất) tỷ lệ sản lượng hữu cơ trên tổng sản lượng đạt khoảng 80 - 85%.

- Giá trị sản phẩm trên 01 ha đất trồng trọt và nuôi trồng thủy sản hữu cơ cao gấp 1,5 -1,8 lần so với sản xuất phi hữu cơ.

III. NHIỆM VỤ
1. Phát triển các vùng sản xuất nông nghiệp hữu cơ tập trung và các sản phẩm hữu cơ chủ lực
```
Prediction:
```text
- The area under organic aquaculture shall account for 1.5 - 3% of the total area under aquaculture, including some specialty aquatic species of economic value: brackish water shrimps, giant river prawns, and indigenous aquatic animals, etc. - The areas under organic nutritional salt production shall accounts for over 10% of the area under production of nutritious salt. - For pharmaceutical products and non-timber forest products from the nature, the ratio of organic output to total output shall be 95 - 98%, and 80 - 85% for intensive farming (using the forest environment for production). - The value of products per hectare of organic aquacultural land shall be 1.5 - 1.8 times higher than that of non-organic production. III. TASKS 1. Developing concentrated organic agricultural production areas and key organic products
```

### Bat_dong_san/123::segment-0007::vi2en

Source:
```text
Ưu tiên sử dụng các vùng có điều kiện đất đai, khí hậu thuận lợi cho từng đối tượng cây trồng, vật nuôi để sản xuất hữu cơ; ưu tiên lựa chọn loại cây trồng, vật nuôi và giống cây trồng, vật nuôi thích ứng tốt với điều kiện thổ nhưỡng, chống chịu sâu bệnh và có thị trường tiêu thụ sản phẩm hữu cơ.

Hình thành vùng sản xuất các sản phẩm bản địa, đặc trưng có tiềm năng để xây dựng nhãn hiệu, chỉ dẫn địa lý sản phẩm để đầu tư sản xuất hữu cơ.

a) Vùng trồng trọt hữu cơ

Xác định được các vùng sản xuất hữu cơ phù hợp với các sản phẩm chủ lực như lúa, rau đậu các loại, cây ăn quả, chè, hồ tiêu, cà phê, dừa, điều... cần có kế hoạch chuyển đổi các vùng đang sản xuất các sản phẩm chủ lực này sang sản xuất hữu cơ.

- Vùng lúa hữu cơ: diện tích gieo trồng khoảng 50 - 70 nghìn ha năm 2025 và khoảng 100 - 150 nghìn ha năm 2030.

- Vùng rau đậu hữu cơ: diện tích gieo trồng đạt khoảng 10 nghìn ha năm 2025 và trên 20 nghìn ha năm 2030.
```
Prediction:
```text
To prioritize the use of areas with favorable soil and climate conditions for each plant and animal for organic production; to prioritize selection of plants, animals and plant varieties and animal breeds that are well adapted to soil conditions, resistant to pests and diseases and have outlets for organic products. To form areas for production of indigenous and typical products with potential for establishing trademarks and geographical indications for investment in organic production. a) Organic farming areas To identify organic production areas suitable to such key products as rice, legumes of all kinds, fruit trees, tea, pepper, coffee, coconut, cashew, etc., there should be a plan to convert these key products into organic ones. - Organic rice areas: the sowing area will be around 50, 000 - 70, 000 ha by 2025 and around 100, 000- 150, 000 hectares by 2030. - Organically grown vegetables and beans: the cultivation area will reach around 10, 000ha by 2025, and over 20, 000h by 2030;
```

### Bat_dong_san/123::segment-0008::vi2en

Source:
```text
- Vùng cây ăn quả các loại hữu cơ: diện tích trồng đạt khoảng 10 - 12 nghìn ha năm 2025 và khoảng 20 - 25 nghìn ha năm 2030.

- Vùng chè hữu cơ: diện tích trồng đến năm 2025 đạt khoảng 1,5 - 2 nghìn ha, năm 2030 khoảng 3 - 5 nghìn ha.

- Vùng hồ tiêu hữu cơ: diện tích hồng đến năm 2025 đạt khoảng 1,5 - 2 nghìn ha, năm 2030 đạt khoảng 3 - 4 nghìn ha.
```
Prediction:
```text
- Area for organic fruit trees: area for planting will reach about 10 - 12 thousand ha by 2025 and about 20 - 25 thousand ha in 2030. - Area of organic tea: area of planting to 2025 will reach around 1.5 - 2 thousand ha, by 2030 will be around 3 - 5 thousand ha. - Organic pepper area: area in pink will reach 1.5 -2 thousand ha to 2025, by 2025 will be about 3 - 4 thousand ha and by 2030.
```

### Bat_dong_san/123::segment-0009::vi2en

Source:
```text
- Ngoài ra còn các vùng cây trồng hữu cơ tập trung khác như vùng dừa hữu cơ khoảng 2-4 nghìn ha, vùng ca cao hữu cơ tập trung khoảng 100 ha...

b) Vùng chăn nuôi hữu cơ

Xây dựng các vùng chăn nuôi hữu cơ với các sản phẩm chủ lực như: Sữa, sản phẩm mật ong, sản phẩm yến, thịt gia súc gia cầm... riêng vùng chăn nuôi trâu, bò hữu cơ gắn với vùng đồng cỏ, vùng trồng trọt sản xuất thức ăn thô xanh hữu cơ.

- Vùng chăn nuôi trâu, bò hữu cơ: đàn trâu, bò đến năm 2025 đạt khoảng 100 - 150 nghìn con và đến năm 2030 đạt khoảng 160 - 180 nghìn con, trong đó bò sữa khoảng 10-15 nghìn con năm 2025 và khoảng 20 - 30 nghìn con năm 2030.

- Vùng chăn nuôi lợn hữu cơ: đàn lợn đạt khoảng 250 - 400 nghìn con năm 2025 và khoảng 600 - 800 nghìn con năm 2030.

- Vùng chăn nuôi gia cầm hữu cơ: đàn gia cầm đạt khoảng 5 - 8 triệu con năm 2025 và khoảng 9 - 12 triệu con năm 2030, trong đó đàn gà hữu cơ khoảng 9 - 10 triệu con.
```
Prediction:
```text
- In addition, there are other concentrated organic crop areas such as organic coconut area of about 2 - 4 thousand ha, organic cocoa area of 100 ha... b) Organic breeding area: Build organic breeding areas with key products such as: Milk, honey products, swiftlet products, poultry and cattle meat... Particularly, organic buffalo and cow breeding zones associated with grassland areas, areas for cultivation and production of organic green and crude feeds. - Organic buffoon and cows breeding zone: the herd of buffons and cocks will reach about 100 - 150 thousand by 2025 and 160 - 180 thousand by 2030, including about 10-15 thousand cows by 2025, and about 20 - 30 thousand by 2020; - Organic pig breeding region: the pig herd will reach 250 - 400 thousand by 2015 and about 600 - 800 thousand by 2020. - Organic poulture breeding site: the poultice herd shall reach about 5 - 8 million by 2025; and about 9 - 12 million by 2030; including about 9 – 10 million organic chickens.
```

### Bat_dong_san/123::segment-0010::vi2en

Source:
```text
- Vùng nuôi ong hữu cơ: sản lượng mật ong hữu cơ khoảng 5 - 8 nghìn tấn.

c) Vùng nuôi trồng thủy sản hữu cơ

Xây dựng các vùng nuôi trồng thủy sản hữu cơ với các sản phẩm chủ lực như tôm nước lợ, tôm càng xanh, các loài thủy sản bản địa... Phát triển vùng nuôi trồng thủy sản hữu cơ gắn với thị trường trong nước, xuất khẩu.
Vùng nuôi trồng thủy sản hữu cơ tập trung với diện tích mặt nước nuôi trồng thủy sản hữu cơ đạt khoảng 60 - 80 nghìn ha.

d) Vùng sản xuất muối dinh dưỡng hữu cơ

Vùng sản xuất muối dinh dưỡng hữu cơ đạt khoảng 1,7 - 2 nghìn ha.

đ) Vùng sản xuất, khai thác sản phẩm từ tự nhiên

Xây dựng và phát triển vùng sản xuất hữu cơ được chứng nhận từ các vùng sản xuất, khai thác sản phẩm tự nhiên (rừng tự nhiên, ao hồ, sông suối tự nhiên).

2. Phát triển đa dạng các hình thức tổ chức sản xuất sản phẩm hữu cơ
```
Prediction:
```text
- Organic beekeeping zones: organic honey production is expected to reach 5 - 8 thousand tonnes. c) Organic aquaculture zones: Build organic aquaculture areas with key products such as brackish-water shrimps, giant river prawns, and native aquatic species, etc. Develop organic aquacultural zones in association with domestic market and export. Concentrated organic aquatic aquaculture zone with an area of 60 - 80 thousand ha of water surface for organic aqua cultivation. d) Organic nutrient salt production zones: Organic nutrients salt production areas: 1.7 - 2 thousand ha. e) Natural products production and extraction zones: Develop organic production zones certified from natural products production zones (natural forests, ponds, lakes, natural rivers and streams). 2. Diversify forms of organic production
```

### Bat_dong_san/123::segment-0011::vi2en

Source:
```text
- Xây dựng các mô hình liên kết theo chuỗi giá trị giữa các doanh nghiệp, hợp tác xã sản xuất, chế biến, kinh doanh các sản phẩm hữu cơ tại các vùng sản xuất tập trung tạo ra hàng hóa quy mô lớn đối với các sản phẩm chủ lực.

- Khuyến khích các hình thức sản xuất quy mô hợp tác xã, doanh nghiệp, tổ hợp tác sản xuất các sản phẩm đặc sản bản địa, sản phẩm khai thác từ tự nhiên có giá trị gia tăng cao và giá trị truyền thống.

- Đẩy mạnh phong trào xây dựng vườn cây hữu cơ gắn với thu gom rác thải, làm phân hữu cơ, xây dựng môi trường xanh, sạch, đẹp ở các xã nông thôn mới.

3. Nghiên cứu phát triển và ứng dụng công nghệ trong nông nghiệp hữu cơ

- Xây dựng và hoàn thiện quy trình kỹ thuật theo hướng ứng dụng công nghệ cao kết hợp với phát huy kiến thức bản địa, sản xuất hữu cơ gắn với chuỗi giá trị cho các sản phẩm chủ lực nhằm nâng cao năng suất, chất lượng, giảm chi phí đầu vào, giảm phát thải khí nhà kính.
```
Prediction:
```text
- Build value chain-based models among enterprises and cooperatives producing, processing and trading organic products in concentrated production areas to create large-scale goods for key products. - Encourage cooperatives, enterprises, and cooperative groups to produce local specialty products, products extracted from nature with high added value and traditional value. - Promote the movement of building organic gardens associated with collecting waste, making organic fertilizer, and creating a green, clean, and beautiful environment in new rural communes. 3. Research, develop, and apply technologies in organic agriculture - Develop and complete technical processes towards applying high technologies in combination with promoting local knowledge, organic production associated with value chains for major products in order to improve productivity, quality, reduce input costs, and reduce greenhouse gas emissions.
```

### Bat_dong_san/123::segment-0012::vi2en

Source:
```text
- Nghiên cứu phát triển và ứng dụng các chế phẩm sinh học, phân hữu cơ sinh học, tác nhân phòng trừ sinh học nhằm nâng cao năng suất, chất lượng sản phẩm, thay thế kháng sinh trong chăn nuôi, nuôi trồng thủy sản; các chế phẩm sinh học xử lý môi trường nông nghiệp.

- Nghiên cứu, đánh giá thực trạng độ phì nhiêu đất, nhu cầu dinh dưỡng cho các cây trồng chủ lực phục vụ sản xuất nông nghiệp hữu cơ bền vững.

- Bảo tồn, phục tráng, khai thác, phát triển và xây dựng chỉ dẫn địa lý, nhãn hiệu tập thể cho các giống cây trồng, vật nuôi bản địa, đặc hữu, có lợi thế so sánh và giá trị kinh tế cao.

- Nghiên cứu và phát triển sản phẩm nông nghiệp hữu cơ chất lượng cao và giá trị sinh học đặc thù, đảm bảo tính cạnh tranh và đáp ứng nhu cầu bảo vệ sức khỏe của người dân.

- Nghiên cứu chọn tạo các giống cây trồng, vật nuôi có năng suất, chất lượng, đặc biệt kháng sâu bệnh, phù hợp với sản xuất hữu cơ; nghiên cứu, phát triển và sử dụng con giống, vật tư đầu vào hữu cơ trong nuôi trồng thủy sản.
```
Prediction:
```text
- Research, develop and apply biological preparations, bio-organic fertilizers, and biological preventive agents to improve productivity and product quality, replace antibiotics in animal husbandry and aquaculture, and bio-products for agricultural environment treatment. - Research and assess soil fertility and nutritional needs of key crops for sustainable organic agriculture. - Preserve, restore, exploit, develop, and establish geographical indications and collective trademarks for indigenous and endemic plant varieties and animal breeds that have comparative advantages and high economic value. - Study and develop high-quality organic products and specific biological values to ensure competitiveness and meet people’s health protection needs. - Conduct research to select and create high-yield and quality plant and animal varieties that are particularly resistant to pests and diseases and suitable for organic production; research, develop; and use breeding stocks and organic inputs in aquaculture.
```

### Bat_dong_san/123::segment-0013::vi2en

Source:
```text
- Triển khai thí điểm các mô hình sản xuất nông nghiệp hữu cơ (trồng trọt, nuôi trồng thủy sản, chăn nuôi, dược liệu và muối) gắn với chuỗi giá trị cho một số sản phẩm chủ lực, đặc sản có lợi thế của các địa phương và mô hình nghiên cứu ứng dụng chuyển giao công nghệ sản xuất nông nghiệp hữu cơ, chứng nhận sản phẩm đạt tiêu chuẩn hữu cơ tại danh mục kèm theo; từng bước nhân rộng mô hình.

4. Đào tạo, tập huấn phát triển nguồn nhân lực
- Nâng cao năng lực cho các cán bộ, công chức các cấp làm công tác quản lý, kiểm tra giám sát các tổ chức chứng nhận và sản phẩm nông nghiệp hữu cơ.

- Nâng cao năng lực chứng nhận sản phẩm hữu cơ cho các tổ chức chứng nhận.

- Đào tạo, tập huấn cho doanh nghiệp, người sản xuất, kinh doanh sản phẩm hữu cơ.

- Tăng cường giáo dục về nông nghiệp hữu cơ cho học sinh phổ thông và sinh viên các trường dạy nghề, cao đẳng và trường đại học thuộc lĩnh vực nông lâm thủy sản.
```
Prediction:
```text
- Pilot organic agriculture production models (cultivation, aquaculture, animal husbandry, herbal ingredients and salt) associated with the value chain for some key products and specialties with advantages of localities and models of research and application of transfer of organic  agricultural production technology, certification of organic standard products in the attached list; gradually expanding the model. 4. Training and developing human resources - Enhancing capacity for officials and public servants at all levels in charge of management, inspection and supervision of certification organizations and organic agricultural products. - Improving capacity for certification of Organic products for the certification organization. - Training and coaching for enterprises, producers and traders of organic products.
```

### Bat_dong_san/123::segment-0014::vi2en

Source:
```text
- Nâng cao chất lượng nguồn nhân lực cho sản xuất hữu cơ, tăng cường công tác đào tạo chuyên gia chuyên sâu về nông nghiệp hữu cơ (ở cả trung ương và địa phương); nâng cao chất lượng đào tạo, thành lập cơ sở đào tạo chuyên sâu về nông nghiệp hữu cơ được cơ quan quản lý nhà nước chỉ định.

5. Phát triển các tổ chức chứng nhận, hoàn thiện hệ thống tiêu chuẩn, quy chuẩn và quy trình kỹ thuật

- Hỗ trợ, tạo điều kiện để thành lập và phát triển các tổ chức chứng nhận sản phẩm nông nghiệp hữu cơ phù hợp với tiêu chuẩn Việt Nam.

- Từng bước hình thành hệ thống tổ chức chứng nhận của Việt Nam được thừa nhận bởi các quốc gia nhập khẩu, tổ chức chứng nhận quốc tế.

- Các tổ chức chứng nhận sản phẩm nông nghiệp hữu cơ của Việt Nam phải thực hiện đúng và nghiêm túc việc quản lý giám sát các tổ chức, cá nhân sản xuất nông nghiệp hữu cơ do đơn vị chứng nhận.
```
Prediction:
```text
- Improve the quality of human resources for organic production, intensify the training of experts specialized in organic agriculture (at both central and local levels); improve the training quality, establish specialized training institutions specializing in organic farming appointed by state management agencies. 5. Develop certification organizations, improve the system of standards, regulations and technical processes - Support and facilitate the establishment and development of certification organization of organic agricultural products in accordance with Vietnamese standards. - Step by step form a system of Vietnamese certification organization recognized by importing countries and international certification organization. - Vietnamese organic  agricultural product certification organization must strictly comply with the management and supervision of organizations and individuals producing organic  Agriculture certified by the unit.
```

### Bat_dong_san/123::segment-0015::vi2en

Source:
```text
- Xây dựng các tiêu chuẩn, quy chuẩn, quy trình kỹ thuật phục vụ sản xuất và quản lý nông nghiệp hữu cơ.
6. Tăng cường chế biến, tiêu thụ và xuất khẩu sản phẩm hữu cơ

- Ưu tiên chế biến các sản phẩm hữu cơ bao gồm các món ăn, các loại thực phẩm, đồ uống, thuốc dược liệu, mỹ phẩm...để nâng cao giá trị gia tăng.
- Xây dựng mô hình liên kết chuỗi giá trị sản phẩm nông nghiệp hữu cơ từ sản xuất đến chế biến, tiêu thụ, ứng dụng công nghệ cao để chế biến sâu, tinh chế tạo ra sản phẩm nông nghiệp hữu cơ có giá trị cao mang thương hiệu Việt Nam.

- Hỗ trợ xây dựng thương hiệu, quảng bá sản phẩm và phát triển thị trường đối với sản phẩm nông nghiệp hữu cơ Việt Nam.

- Khuyến khích các doanh nghiệp đưa các sản phẩm nông nghiệp hữu cơ vào hệ thống các siêu thị, cửa hàng tiện ích và chuỗi cung ứng sản phẩm an toàn.

7. Phát triển các vật tư đầu vào phục vụ phát triển nông nghiệp hữu cơ

- Công bố công khai danh mục các vật tư đầu vào đảm bảo tiêu chuẩn nông nghiệp hữu cơ.
```
Prediction:
```text
- Establish technical standards, regulations and procedures for organic agriculture production and management. 6. Enhance processing, sale and export of organic products - Prioritize processing of organic foods, foodstuffs, beverages, herbal medicines, cosmetics, etc. to increase added value. - Develop a model for linking the value chain of organic agricultural products from production to processing and consumption, and apply high technology for deep processing or refining to create high-value organic products bearing Vietnamese brands. - Support branding, product promotion and market development for Vietnamese organic agriculturaL products. - Encourage enterprises to introduce organic products into supermarkets, convenience stores and safe product supply chains. 7. Develop input materials for organic farming development - Publish the list of input materials meeting organic  farming standards.
```

### Bat_dong_san/123::segment-0016::vi2en

Source:
```text
- Xây dựng chính sách khuyến khích sử dụng vật tư đầu vào hữu cơ để sản xuất sản phẩm hữu cơ trong các lĩnh vực nông lâm thủy sản.

- Đa dạng nguồn sản phẩm làm thức ăn chăn nuôi, thủy sản hữu cơ như các loại thức ăn xanh, ủ chua, sấy khô, bột cá... để phát triển chăn nuôi, thủy sản hữu cơ. Phát triển và sử dụng con giống, vật tư đầu vào hữu cơ trong nuôi trồng thủy sản.

IV. GIẢI PHÁP THỰC HIỆN

1. Nâng cao hiệu lực, hiệu quả thực thi pháp luật về nông nghiệp hữu cơ

a) Phát triển vùng sản xuất nông nghiệp hữu cơ tập trung

- Các địa phương căn cứ vào lợi thế về điều kiện sinh thái, sản phẩm có thế mạnh và thị trường tiêu thụ, xác định các sản phẩm nông nghiệp hữu cơ chủ lực, trên cơ sở đó tiến hành xây dựng đề án phát triển nông nghiệp hữu cơ, đánh giá đất đai, nguồn nước, xây dựng cơ chế, chính sách hỗ trợ, định hướng phát triển các vùng sản xuất nông nghiệp hữu cơ tập trung, kêu gọi các doanh nghiệp, các hợp tác xã và người dân có nhu cầu sản xuất hữu cơ đầu tư vào sản xuất.
```
Prediction:
```text
- Formulate policies to encourage the use of organic inputs for the production of organic products in the fields of agriculture, forestry and fisheries. - Diversify the sources of products to make organic animal and aquatic feeds such as green feeds, silage, drying, fish meal, etc. to develop organic animal husbandry and aquaculture. Develop and use breeds and organic input materials in aquaculture IV. IMPLEMENTATION SOLUTIONS 1. Improve the effectiveness and efficiency of the implementation of the law on organic agriculture a) Develop concentrated organic agricultural production areas - Localities shall base on the advantages of ecological conditions, advantageous products and consumption markets to identify key organic products, on which basis to formulate schemes for organic  agricultural development, assess land and water sources, formulate mechanisms and policies to support and orientate the development of concentrated areas of organic  farming, and call on enterprises, cooperatives and people who need to produce organic to invest in production.
```

### Bat_dong_san/123::segment-0017::vi2en

Source:
```text
- Xây dựng hệ thống phân phối theo chuỗi giá trị từ sản xuất, chế biến gắn với thị trường tiêu thụ sản phẩm hữu cơ (kết hợp với du lịch, nông nghiệp sinh thái) theo đặc thù vùng miền, qua đó tổng kết bài học thành công để hoàn thiện các quy trình kỹ thuật và tập huấn, chuyển giao.

- Tăng cường sử dụng vật liệu sẵn có, tái sử dụng, khép kín chu trình trong khu vực sản xuất tạo tiền đề cho sự phát triển nông nghiệp hữu cơ ổn định (thông qua sử dụng sản phẩm từ trồng trọt làm thức ăn chăn nuôi, thủy sản và cung cấp nguyên liệu làm phân bón hữu cơ cho trồng trọt).

- Xác định các vùng có tiềm năng thế mạnh về sản xuất các sản phẩm nông nghiệp hữu cơ để khuyến khích các doanh nghiệp, các hợp tác xã và người dân có nhu cầu sản xuất sản phẩm nông nghiệp hữu cơ đầu tư vào sản xuất.

b) Quản lý đầu vào của sản xuất hữu cơ

- Quản lý giống cây trồng, vật nuôi và thủy sản hữu cơ được chứng nhận phù hợp với tiêu chuẩn nông nghiệp hữu cơ.
```
Prediction:
```text
- Build a distribution system based on the value chain from production and processing associated with the organic product consumption market (in combination with tourism and eco-agriculture) according to regional characteristics, thereby summarizing successful lessons to improve technical processes, training and transfer. - Enhance the use of available materials, reuse and close the cycle in the production area to create a premise for the stable development of organic agriculture (through the uses of crop products as animal and aquatic feed and supply of raw materials for organic fertilizer for cultivation). - Identify areas with potential and strengths in producing organic agricultural products to encourage enterprises, cooperatives and people wishing to produce organic agriculturaL products to invest in production. b) Management of inputs of organic production - Management of organic plant varieties, livestock and aquaculture products certified in accordance with organic  agricultural standards.
```

## E3: 20 available examples (up to 20)

### Bat_dong_san/14::segment-0009::vi2en

Source:
```text
c) Ủy ban nhân dân cấp tỉnh ban hành đơn giá bồi thường thiệt hại về cây trồng, vật nuôi, rừng tự nhiên, rừng trồng bảo đảm phù hợp với tình hình thực tế của địa phương và phải xem xét điều chỉnh khi có biến động.

12. Ủy ban nhân dân cấp tỉnh quy định biện pháp, mức hỗ trợ khác để bảo đảm có chỗ ở, ổn định đời sống, sản xuất đối với người có đất thu hồi, chủ sở hữu tài sản gắn liền với đất phù hợp với tình hình thực tế tại địa phương. Căn cứ quy định của Ủy ban nhân dân cấp tỉnh, Ủy ban nhân dân cấp xã quyết định biện pháp, mức hỗ trợ khác đối với từng dự án cụ thể.

13. Quy định chuyển tiếp đối với thu hồi đất, bồi thường, hỗ trợ, tái định cư:

a) Trường hợp đã có quyết định thu hồi đất và quyết định phê duyệt phương án bồi thường, hỗ trợ, tái định cư trước ngày Nghị quyết này có hiệu lực thi hành thì tiếp tục thực hiện theo phương án bồi thường, hỗ trợ, tái định cư đã phê duyệt.
```
Prediction:
```text
c) Provincial-level People’s Committees shall promulgate unit prices of compensation for damage to plants, domestic animals, natural forests and planted forest to suit the actual situation of their localities and shall consider adjusting these unit prices in case of any change. 12. Provincial- level People's Committee shall stipulate other measures and levels of support to ensure residence, life and production stability for persons whose land is recovered and owners of land-attached assets in accordance with the actual condition of their respective localities. Based on the regulations of provincial-level people’s committees, commune- level people’
```

### Bat_dong_san/14::segment-0030::vi2en

Source:
```text
2. Bảng giá đất được xây dựng theo loại đất, khu vực, vị trí. Đối với khu vực có bản đồ địa chính dạng số và cơ sở dữ liệu giá đất thì được xây dựng bảng giá đất đến từng thửa đất.

3. Hội đồng nhân dân cấp tỉnh quyết định bảng giá đất, công bố và áp dụng từ ngày 01 tháng 01 năm 2026; sửa đổi, bổ sung bảng giá đất khi cần thiết.
4. Đối với các trường hợp áp dụng giá đất cụ thể quy định tại Điều 160 của Luật Đất đai nhưng đến ngày Nghị quyết này có hiệu lực thi hành, cơ quan, người có thẩm quyền chưa ban hành quyết định về giá đất cụ thể thì Ủy ban nhân dân cấp tỉnh quyết định việc áp dụng xác định giá đất theo quy định của Nghị quyết này hoặc tiếp tục xác định giá đất cụ thể theo quy định của Luật Đất đai.
```
Prediction:
```text
2. The land price list shall be formulated according to land type, area and location. For areas with digital cadastral maps and land price databases, the land price table may be developed for each land plot. 3. Provincial People’s Councils shall decide on the land prices, announce and apply from January 1, 2026; amend and supplement the land pricing table when necessary. 4. For the cases of application of specific land prices specified in Article 160 of the Land Law but by the effective date of this Resolution, the competent agencies and persons have not issued decisions on specific land price, the provincial People’
```

### Bat_dong_san/14::segment-0034::vi2en

Source:
```text
1. Chủ tịch Ủy ban nhân dân cấp tỉnh quyết định thành lập Hội đồng thẩm định bảng giá đất, thẩm định hệ số điều chỉnh giá đất bao gồm Chủ tịch Ủy ban nhân dân cấp tỉnh hoặc 01 Phó Chủ tịch Ủy ban nhân dân cấp tỉnh làm Chủ tịch Hội đồng, Thủ trưởng cơ quan có chức năng tài chính cấp tỉnh làm Phó Chủ tịch Hội đồng, các thành viên Ủy ban nhân dân cấp tỉnh là thủ trưởng các cơ quan chuyên môn cấp tỉnh; Chủ tịch Ủy ban nhân dân cấp xã; đại diện của cơ quan, tổ chức có liên quan, tổ chức tư vấn xác định giá đất và chuyên gia.

Hội đồng thẩm định bảng giá đất, thẩm định hệ số điều chỉnh giá đất quyết định thành lập Tổ giúp việc cho Hội đồng và được thuê tổ chức tư vấn xác định giá đất để tư vấn thẩm định bảng giá đất, hệ số điều chỉnh giá đất.
2. Tổ chức được hoạt động tư vấn xác định giá đất khi có đủ các điều kiện sau đây:
```
Prediction:
```text
1. The Chairperson of the provincial People’s Committee shall decide to establish the Council for appraisal of land price lists and land price adjustment coefficients, which is composed of the Chairman of the Provincial People’S Committee or 01 Vice Chairwoman of provincial People's Committee as the Council's Chair, the Head of the financial authority of the province as the Deputy Chair of the Council, the members of the People’
```

### Bat_dong_san/2::segment-0000::vi2en

Source:
```text
CHÍNH PHỦ CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM

------- Độc lập - Tự do - Hạnh phúc

Số: 228/2026/NĐ-CP Hà Nội, ngày 25 tháng 6 năm 2026

NGHỊ ĐỊNH
SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA NGHỊ ĐỊNH SỐ 18/2020/NĐ-CP NGÀY 11 THÁNG 02 NĂM 2020 CỦA CHÍNH PHỦ XỬ PHẠT VI PHẠM HÀNH CHÍNH TRONG LĨNH VỰC ĐO ĐẠC VÀ BẢN ĐỒ ĐƯỢC SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU BỞI NGHỊ ĐỊNH SỐ 04/2022/NĐ-CP NGÀY 06 THÁNG 01 NĂM 2022 CỦA CHÍNH PHỦ

Căn cứ Luật Tổ chức Chính phủ số 63/2025/QH15;
Căn cứ Luật Tổ chức chính quyền địa phương số 72/2025/QH15;

Căn cứ Luật Xử lý vi phạm hành chính số 15/2012/QH13 được sửa đổi, bổ sung một số điều bởi Luật số 54/2014/QH13, Luật số 18/2017/QH14, Luật số 67/2020/QH14, Luật số 09/2022/QH15, Luật số 11/2022/QH15, Luật số 56/2024/QH15, Luật số 88/2025/QH15;

Căn cứ Luật Đo đạc và bản đồ số 27/2018/QH14 được sửa đổi, bổ sung một số điều bởi Luật số 84/2025/QH15 và Luật số 146/2025/QH15;

Căn cứ Luật Đo lường số 04/2011/QH13 được sửa đổi, bổ sung một số điều bởi Luật số 35/2018/QH14 và Luật số 84/2025/QH15;

Theo đề nghị của Bộ trưởng Bộ Nông nghiệp và Môi trường;
```
Prediction:
```text
THE GOVERNMENT SOCIALIST REPUBLIC OF VIETNAM ------- Independence - Freedom - Happiness No. 228/2026/ND-CP Hanoi, June 25, 2026 DECREE AMENDING AND SUPPLEMENTING A NUMBER OF ARTICLES OF DECREE NO. 18/2020/ND
```

### Bat_dong_san/2::segment-0030::vi2en

Source:
```text
Điều 19. Điều khoản chuyển tiếp

1. Đối với hành vi vi phạm hành chính trong lĩnh vực đo đạc và bản đồ xảy ra và kết thúc trước thời điểm Nghị định này có hiệu lực mà sau đó mới bị phát hiện hoặc đang xem xét, giải quyết tại thời điểm Nghị định này đã có hiệu lực thì áp dụng Nghị định số 18/2020/NĐ-CP ngày 11 tháng 02 năm 2020 của Chính phủ xử phạt vi phạm hành chính trong lĩnh vực đo đạc và bản đồ được sửa đổi, bổ sung bởi Nghị định số 04/2022/NĐ-CP để xử lý.

2. Đối với hành vi vi phạm trong lĩnh vực đo đạc và bản đồ xảy ra trước thời điểm Nghị định này có hiệu lực thi hành nhưng vẫn đang diễn ra khi nghị định này đã có hiệu lực thì áp dụng quy định của Nghị định này để xử lý
TM. CHÍNH PHỦ KT. THỦ TƯỚNG PHÓ THỦ TƯỚNG

Hồ Quốc Dũng
```
Prediction:
```text
Article 19. Transitional provisions 1. For administrative violations against regulations on topography and cartography that are committed and terminated before the effective date of this Decree but are discovered afterwards or are under consideration at the effective time of this Circular, the Government’s Decrees No. 18/2020/ND-CP dated February 11, 2020 on penalties for administrative violation against regulations in topography, cartography and geodesy amended by the Decreed No. 04/2022/ND
```

### Bat_dong_san/45::segment-0020::vi2en

Source:
```text
1. Người đại diện theo pháp luật của tổ chức trong nước, tổ chức kinh tế có vốn đầu tư nước ngoài; người đứng đầu của tổ chức nước ngoài có chức năng ngoại giao đối với việc sử dụng đất của tổ chức mình.
2. Chủ tịch Ủy ban nhân dân cấp xã đối với việc sử dụng đất nông nghiệp vào mục đích công ích; đất phi nông nghiệp đã giao cho Ủy ban nhân dân cấp xã để sử dụng vào mục đích xây dựng trụ sở Ủy ban nhân dân, các công trình công cộng phục vụ hoạt động văn hóa, giáo dục, y tế, thể dục, thể thao, vui chơi, giải trí, chợ, nghĩa trang và công trình công cộng khác của xã, phường, thị trấn; đất tôn giáo, đất tín ngưỡng chưa giao quản lý, sử dụng.

3. Người đại diện cho cộng đồng dân cư là trưởng thôn, làng, ấp, bản, bon, buôn, phum, sóc, tổ dân phố và điểm dân cư tương tự hoặc người được cộng đồng dân cư thỏa thuận cử ra.

4. Người đại diện tổ chức tôn giáo, tổ chức tôn giáo trực thuộc đối với việc sử dụng đất của tổ chức tôn giáo, tổ chức tôn giáo trực thuộc.
```
Prediction:
```text
1. Legal representatives of domestic organizations, foreign-invested economic organizations; heads of foreign organizations with diplomatic functions for the use of land of their organizations. 2. Chairpersons of commune-level People’s Committees for use of agricultural land for public purposes; non-agricultural land already allocated to commune- level People's Committee for use for the purpose of construction of People’
```

### Bat_dong_san/45::segment-0036::vi2en

Source:
```text
4. Đất để thực hiện chính sách quy định tại các khoản 1, 2 và 3 Điều này được bố trí từ quỹ đất do cơ quan, tổ chức của Nhà nước quản lý hoặc từ quỹ đất thu hồi theo quy định tại khoản 29 Điều 79 của Luật này.
5. Ủy ban nhân dân cấp tỉnh căn cứ tình hình thực tế và quỹ đất của địa phương quyết định diện tích giao đất, cho thuê đất để thực hiện chính sách hỗ trợ đất đai đối với cá nhân là người dân tộc thiểu số theo quy định tại khoản 3 Điều này.

6. Ủy ban nhân dân cấp tỉnh trình Hội đồng nhân dân cùng cấp ban hành chính sách của địa phương về đất đai đối với đồng bào dân tộc thiểu số sinh sống trên địa bàn phù hợp với điều kiện thực tế của địa phương và tổ chức thực hiện.
```
Prediction:
```text
4. Land for implementation of the policies specified in Clauses 1, 2 and 3 of this Article shall be allocated from the land fund managed by state agencies or organizations or from the recovered land fund under Clause 29, Article 79 of this Law. 5. Provincial-level People’s Committees shall base themselves on the practical situation and local land funds to decide on land allocation or lease areas for implementation the land support policy for individuals being ethnic minority people according to the provisions of Clause 3 of This Article. 6. Provincial- level People’
```

### Bat_dong_san/45::segment-0040::vi2en

Source:
```text
trong quản lý và sử dụng đất đai
1. Ủy ban Trung ương Mặt trận Tổ quốc Việt Nam tham gia xây dựng pháp luật, thực hiện phản biện xã hội đối với dự thảo văn bản pháp luật về đất đai, dự thảo quy hoạch, kế hoạch sử dụng đất quốc gia, dự án có sử dụng đất do Quốc hội, Thủ tướng Chính phủ quyết định, chấp thuận chủ trương đầu tư.

2. Ủy ban Mặt trận Tổ quốc Việt Nam các cấp có trách nhiệm sau đây:

a) Tham gia xây dựng pháp luật; thực hiện phản biện xã hội đối với dự thảo văn bản pháp luật về đất đai, dự thảo quy hoạch, kế hoạch sử dụng đất cùng cấp, dự án có sử dụng đất do Hội đồng nhân dân, Ủy ban nhân dân cùng cấp quyết định, chấp thuận chủ trương đầu tư;
b) Tham gia ý kiến về trường hợp thu hồi đất, phương án bồi thường, hỗ trợ, tái định cư, trường hợp cưỡng chế khi thực hiện thu hồi đất;

c) Tham gia ý kiến, giám sát quá trình xây dựng bảng giá đất và thực hiện bảng giá đất;

d) Tham gia hòa giải tranh chấp đất đai theo quy định của pháp luật;
```
Prediction:
```text
in land management and use 1. The Central Committee of the Vietnamese Fatherland Front shall participate in formulating laws, conducting social criticism for draft legal documents on land, draft national land use planning and plans, projects using land decided and approved by the National Assembly, the Prime Minister. 2. The Committees of Vietnamese Motherland Front at all levels shall: a) Participate in formulation of laws; conduct social criticization for draft land legal documents, draft land use plans at the same level, projects utilizing land decided, approved by People’s Councils, People’
```

### Bat_dong_san/45::segment-0044::vi2en

Source:
```text
5. Chính quyền địa phương các cấp có trách nhiệm quản lý nhà nước về đất đai tại địa phương theo thẩm quyền quy định của Luật này.
Ở đơn vị hành chính cấp huyện không thành lập đơn vị hành chính cấp xã thì Hội đồng nhân dân, Ủy ban nhân dân cấp huyện thực hiện nhiệm vụ, quyền hạn của Hội đồng nhân dân, Ủy ban nhân dân cấp xã quy định của Luật này.

Điều 22. Cơ quan có chức năng quản lý đất đai và công chức làm công tác địa chính ở cấp xã

1. Hệ thống cơ quan có chức năng quản lý đất đai được tổ chức thống nhất ở trung ương và địa phương.

2. Cơ quan có chức năng quản lý nhà nước về đất đai ở trung ương là Bộ Tài nguyên và Môi trường.
3. Cơ quan có chức năng quản lý đất đai ở địa phương được thành lập ở cấp tỉnh và ở cấp huyện.

4. Tổ chức dịch vụ công về đất đai, bao gồm tổ chức đăng ký đất đai, tổ chức phát triển quỹ đất và các tổ chức dịch vụ công khác được thành lập và hoạt động theo quy định của Chính phủ.
```
Prediction:
```text
5. Local governments at all levels shall be responsible for state management of land within their jurisdiction in accordance with this Law. In district-level administrative units where commune-level administration units are not established, district- level People’s Councils and People’
```

### Bat_dong_san/45::segment-0161::vi2en

Source:
```text
d) Chính phủ quy định về việc áp dụng phương pháp định giá đất và khoản tiền người sử dụng đất phải nộp bổ sung đối với thời gian chưa tính tiền sử dụng đất, tiền thuê đất của các trường hợp quy định tại các điểm a, b và c khoản này.

3. Trường hợp phương án giá đất đã trình Ủy ban nhân dân cấp có thẩm quyền quyết định giá đất cụ thể theo quy định của pháp luật trước ngày Luật này có hiệu lực thi hành thì Ủy ban nhân dân cấp có thẩm quyền quyết định giá đất cụ thể theo phương án đã trình mà không áp dụng quy định của Luật này.

Điều 258. Giải quyết về thời hạn sử dụng đất khi Luật này có hiệu lực thi hành
```
Prediction:
```text
d) The Government shall provide for the application of land pricing methods and additional payments by land users for the period during which land levies and land rents are not yet calculated in the cases specified in Points a, b and c of this Clause. 3. In case the land price plan has been submitted to the competent People’s Committee for decision on specific land prices as prescribed by law before the effective date of this Law, the People’
```

### Bat_dong_san/81::segment-0000::vi2en

Source:
```text
BỘ XÂY DỰNG CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM

------- Độc lập - Tự do - Hạnh phúc

Số: 03/2023/TT-BXD Hà Nội, ngày 28 tháng 4 năm 2023

THÔNG TƯ
SỬA ĐỔI, BỔ SUNG ĐIỀU 3 THÔNG TƯ SỐ 09/2021/TT-BXD NGÀY 16 THÁNG 8 NĂM 2021 CỦA BỘ TRƯỞNG BỘ XÂY DỰNG HƯỚNG DẪN THỰC HIỆN MỘT SỐ NỘI DUNG CỦA NGHỊ ĐỊNH SỐ 100/2015/NĐ-CP NGÀY 20 THÁNG 10 NĂM 2015 CỦA CHÍNH PHỦ VỀ PHÁT TRIỂN VÀ QUẢN LÝ NHÀ Ở XÃ HỘI VÀ NGHỊ ĐỊNH SỐ 49/2021/NĐ-CP NGÀY 01 THÁNG 4 NĂM 2021 CỦA CHÍNH PHỦ SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA NGHỊ ĐỊNH SỐ 100/2015/NĐ-CP NGÀY 20 THÁNG 10 NĂM 2015 CỦA CHÍNH PHỦ VỀ PHÁT TRIỂN VÀ QUẢN LÝ NHÀ Ở XÃ HỘI

Căn cứ Luật Đấu thầu ngày 26 tháng 11 năm 2013;
Căn cứ Luật Nhà ở ngày 25 tháng 11 năm 2014;

Căn cứ Luật Đầu tư ngày 17 tháng 6 năm 2020;
Căn cứ Luật Quy hoạch đô thị ngày 17 tháng 6 năm 2009;
```
Prediction:
```text
THE MINISTRY OF CONSTRUCTION SOCIALIST REPUBLIC OF VIETNAM ------- Independence - Freedom - Happiness No. 03/2023/TT-BXD Hanoi, April 28, 2023 CIRCULAR AMENDING AND SUPPLEMENTING ARTICLE 3 CIRCULATION NO. 09/2021/TT–BXD DATED AUGUST 16, 2021 OF THE MINISTER OF CONstructION GUIDING THE IMPLEMENTATION OF A NUMBER OF ARTICLES OF THE GOVERNMENT’S DECREE NO. 100/2015/ND-CP DATED OCTOBER 20, 2015 ON DEVELOPMENT AND MANAGEMENT OF SOCIAL HOUSING AND THE  GOVERS DECREE No. 49/2021-ND- CP DATED APRIL 01, 2021 ON AMENDMENTS TO THE AUTHORITY’S Decree No. 100 2015/ND
```

### Bat_dong_san/9::segment-0024::vi2en

Source:
```text
3. Xử lý chuyển tiếp đối với trường hợp quy định tại khoản 4 Điều 7 Nghị quyết số 254/2025/QH15 Trường hợp Ủy ban nhân dân cấp tỉnh quyết định việc áp dụng xác định giá đất theo quy định của Nghị quyết số 254/2025/QH15 để tính tiền sử dụng đất, tiền thuê đất đối với các trường hợp áp dụng giá đất cụ thể quy định tại Điều 160 Luật Đất đai năm 2024 nhưng đến ngày 01 tháng 01 năm 2026, cơ quan, người có thẩm quyền chưa ban hành quyết định giá đất cụ thể thì thực hiện theo quy định tại khoản 4 Điều 7 Nghị quyết số 254/2025/QH15.

Chương III

ĐIỀU KHOẢN THI HÀNH

Điều 13. Sửa đổi, bổ sung một số điều của Nghị định số 103/2024/NĐ-CP (được sửa đổi, bổ

sung tại Nghị định số 291/2025/NĐ-CP) của Chính phủ quy định về tiền sử dụng đất, tiền thuê đất
```
Prediction:
```text
3. Transitional handling of the cases specified in Clause 4 Article 7 of Resolution No. 254/2025/QH15 In case the provincial People’s Committee decides to apply the land price determination under Resolution 254/ 2025/Q H15 to calculate land levy and land rent in the cases of application of specific land prices specified under Article 160 of the 2024 Land Law but by January 1, 2026, the competent authority or person has not issued a decision on specific land price, the provisions of Clause 4. Article 7 Resolution no. 254-2025/ QH15 shall be complied with. Chapter III IMPLEMENTATION PROVISIONS Article 13. Amendments to some articles of Decree No. 103/2024/ND-CP (amended and supplemented in Decrees No. 291/2025/ND
```

### Bat_dong_san/9::segment-0041::vi2en

Source:
```text
10. Sửa đổi, bổ sung một số điểm, khoản của Điều 17 như sau:

a) Sửa đổi, bổ sung điểm a khoản 10 như sau:

“ a) Tổ chức trong nước đã được miễn, giảm tiền sử dụng đất theo quy định của pháp luật mà nay chuyển nhượng, góp vốn bằng quyền sử dụng đất theo đúng quy định của pháp luật thì phải nộp cho Nhà nước khoản tiền tương ứng với số tiền sử dụng đất đã được miễn, giảm tại thời điểm giao đất, cho phép chuyển mục đích sử dụng đất theo quy định tại điểm b khoản 3 Điều 33 Luật Đất đai và phải nộp khoản tiền bổ sung đối với thời gian kể từ ngày được miễn, giảm tiền sử dụng đất đến ngày chuyển nhượng, góp vốn bằng quyền sử dụng đất theo mức quy định tại điểm d khoản 2 Điều 257 Luật Đất đai năm 2024, khoản 2 Điều 50, khoản 9 Điều 51 Nghị định số 103/2024/NĐ-CP (được sửa đổi, bổ sung tại điểm b khoản 18, điểm đ khoản 19 Điều 1 Nghị định số 291/2025/NĐ-CP).
```
Prediction:
```text
10. Amendments to certain points and clauses of Article 17: a) Point a Clause 10 is amended as follows: “a) A domestic organization that has been exempted from or reduced in land levy as prescribed by law and now transfers or contributes land use rights as capital in accordance with regulations of law shall pay to the State an amount equivalent to the land levy exempted or decreased at the time of land allocation or permission for change of land use purpose in accordance to Point b Clause 3 Article 33 of the Land Law and pay an additional amount for the period from the date of exemption or reduction of land levy to the date on which the land use right is transferred or contributed as capital at the rate specified in Point d Clause 2 Article 257 of the 2024 Land Law, Clause 2. Article 50, and Clause 9 Article 51 of the Decree No. 103/2024/ND-CP (as amended in Point b, Clauses 18 and dd, Clauss 19 Article 1 of the Government’s Decrees No. 291/2025/ND
```

### Bat_dong_san/9::segment-0067::vi2en

Source:
```text
a) Thay thế các cụm từ: “Giá đất ở quy định tại Bảng giá đất” tại điểm a khoản 1, điểm a khoản 2, điểm a, điểm b khoản 3, điểm a, điểm b khoản 4 Điều 10; điểm a, điểm b khoản 1, điểm a, điểm b khoản 2, điểm a, điểm b khoản 3, điểm a khoản 4 Điều 11; điểm a khoản 3 Điều 12 và cụm từ “Giá đất của loại đất được công nhận quy định tại bảng giá đất” tại điểm b khoản 1, điểm b khoản 2, điểm c, điểm d khoản 3, điểm c, điểm d khoản 4 Điều 10; điểm c khoản 1, điểm c khoản 2, điểm c khoản 3, điểm b khoản 4 Điều 11 thành “Giá đất tính tiền sử dụng đất”.

Thay thế cụm từ “Ủy ban nhân dân cấp xã” tại khoản 2 Điều 52 Nghị định số 103/2024/NĐ-CP (được sửa đổi, bổ sung tại điểm a khoản 2 Điều 1 Nghị định số 291/2025/NĐ-CP) thành “Chủ tịch Ủy ban nhân dân cấp xã”.

b) Bỏ cụm từ “, dịch vụ phi hàng không” tại điểm a khoản 1 Điều 40.

Điều 14. Điều khoản thi hành
```
Prediction:
```text
a) The phrase “Giá đất ở quy định tại bảng giá đất” (Residential land prices) in Point a Clause 1, Point a clause 2, Points a and b Clause 3, Point and b clause 4 Article 10; Point a and Point b Clauses 1, and Points and b of Clause 2; Point and Point a of Clauses 3 and a Clauses 4 Article 11; Point b of clause 3 Article 12; and the phrase “Gá đất của loại đất được công nhận quy định ở bảng giá land” (Land prices of recognized land types) in point b clauses 1 and 2, point c and point d of clauses 3, and point c, and b, clause4 Article 10, and points c clause 1 and c, clauses 2, and c clauses, and d, of claused 4 Article 12 are replaced with “Giấ đất tính tiền sử dụng đất” (“Land prices for calculation of land levy”) in Clause 2. Article 52 of the Decree No. 103/2024/ND-CP (as amended in point a clauses 2. Article 1 of the Government’s Decrees No. 291/2025/ND
```

### Dich_vu_phap_ly/128::segment-0014::vi2en

Source:
```text
1. Phối hợp với Bộ Tư pháp trong việc chỉ đạo, hướng dẫn, kiểm tra, thanh tra việc thực hiện công chứng của Cơ quan đại diện Việt Nam ở nước ngoài theo quy định của pháp luật về công chứng; tổ chức bồi dưỡng nghiệp vụ công chứng cho viên chức lãnh sự của Cơ quan đại diện Việt Nam ở nước ngoài;

2. Giải quyết khiếu nại, tố cáo về công chứng theo thẩm quyền;
3. Tổng hợp tình hình và thống kê số liệu về công chứng của Cơ quan đại diện Việt Nam ở nước ngoài gửi Bộ Tư pháp theo định kỳ 6 tháng và hàng năm.

Điều 19. Nhiệm vụ, quyền hạn củaUỷ ban nhân dân cấp tỉnh trong việc quản lý nhà nước về công chứng, chứng

thực
1. Uỷ ban nhân dân cấp tỉnh thực hiện quản lý nhà nước về công chứng, chứng thực trong địa phương mình, có nhiệm vụ, quyền hạn sau đây:

a) Chỉ đạo hoạt động công chứng, chứng thực;
b) Giải quyết khiếu nại, tố cáo về công chứng, chứng thực theo thẩm quyền;
```
Prediction:
```text
1. To coordinate with the Ministry of Justice in directing, guiding, examining and inspecting the notarization by overseas Vietnamese representative missions according to the provisions of law on notarization; to organize professional fostering in notarization for consular officers of oversea Vietnamese representation missions; 2. To settle complaints and denunciations about notarization according to their competence; 3. To sum up the situation and make statistics on notarized data of the foreign-based Vietnamese missions and send them biannually and annually to the Ministry Of Justice. Article 19.- Tasks and powers of the provincial-level People’s Committees in performing the State management over notarization and authentication 1. The provincial- level People’
```

### Dich_vu_phap_ly/128::segment-0016::vi2en

Source:
```text
Điều 20. Nhiệm vụ, quyền hạn củaUỷ ban nhân dân cấp huyện trong việc quản lý nhà nước về chứng thực

1. Uỷ ban nhân dân cấp huyện thực hiện quản lý nhà nước về chứng thực trong địa phương mình, có nhiệm vụ, quyền hạn sau đây:
```
Prediction:
```text
Article 20.- Tasks and powers of the district-level People’s Committees in the State management over authentication 1. The district- level People’
```

### Dich_vu_phap_ly/128::segment-0020::vi2en

Source:
```text
chứng thực hợp đồng, giao dịch liên quan đến bất động sản
1. Chủ tịch Uỷ ban nhân dân cấp tỉnh quyết định thẩm quyền địa hạt công chứng hợp đồng, giao dịch liên quan đến bất động sản trong địa phương mình cho từng Phòng Công chứng. "Địa hạt" là một hoặc một số quận, huyện, thị xã, thành phố thuộc tỉnh.

2. Uỷ ban nhân dân huyện, quận, thị xã chứng thực hợp đồng, giao dịch liên quan đến bất động sản trong phạm vi địa hạt của huyện, quận, thị xã mình mà không thuộc thẩm quyền địa hạt của Phòng Công chứng quy định tại khoản 1 Điều này.
3. Việc công chứng, chứng thực di chúc, văn bản từ chối nhận di sản liên quan đến bất động sản không phải tuân theo quy định tại khoản 1 và khoản 2 Điều này.

Điều 24. Thẩm quyền chứng thực củaUỷ ban nhân dân cấp xã

1. Uỷ ban nhân dân cấp xã có thẩm quyền thực hiện các việc sau đây:
a) Chứng thực chữ ký của công dân Việt Nam trong các giấy tờ phục vụ cho việc thực hiện các giao dịch dân sự ở trong nước;
```
Prediction:
```text
authentication of contracts and transactions related to real estate 1. The presidents of the provincial-level People’s Committees shall decide on the local competence to notarize contracts, transactions relating to real property in their respective localities for each Notary Public office. “Locality" means one or several urban districts, rural districts or provincial capitals or towns. 2. The People’
```

### Dich_vu_phap_ly/128::segment-0066::vi2en

Source:
```text
2. Thành phần Hội đồng tiêu hủy hồ sơ bản sao giấy tờ tại Uỷ ban nhân dân cấp huyện gồm có: Trưởng phòng hoặc Phó Trưởng phòng Tư pháp, công chức phụ trách lưu trữ của Uỷ ban nhân dân cấp huyện, đại diện cơ quan lưu trữ cấp tỉnh, đại diện Sở Tư pháp là uỷ viên, Chủ tịch hoặc Phó Chủ tịch Uỷ ban nhân dân cấp huyện là Chủ tịch Hội đồng. Chủ tịch Uỷ ban nhân dân cấp huyện ra quyết định về việc thành lập Hội đồng.

Thành phần Hội đồng tiêu hủy hồ sơ bản sao, hồ sơ bản dịch giấy tờ tại Phòng Công chứng gồm có: Trưởng phòng hoặc Phó Trưởng phòng Công chứng, công chức phụ trách lưu trữ tại Phòng Công chứng, Chánh Văn phòng Sở Tư pháp, đại diện cơ quan lưu trữ cấp tỉnh là uỷ viên, Giám đốc hoặc Phó Giám đốc Sở Tư pháp là Chủ tịch Hội đồng. Giám đốc Sở Tư pháp ra quyết định về việc thành lập Hội đồng.
```
Prediction:
```text
2. The composition of the Council for destruction of dossiers on copies of papers at the district-level People’s Committees shall include: the head or deputy head of the Justice Section, the official in charge of archive of the district level People's Committee, the representative of the provincial-level archive agency, the provincial/municipal Justice Service’s representative as a member, the chairman or deputies of the District-level people’s committee as the Council chairman. The chairman of the People’
```

### Dich_vu_phap_ly/128::segment-0067::vi2en

Source:
```text
3. Việc tiêu hủy hồ sơ bản sao, hồ sơ bản dịch giấy tờ phải lập thành biên bản có chữ ký của tất cả các thành viên trong Hội đồng và tuân theo quy định của pháp luật về lưu trữ; trong biên bản ghi rõ việc tiêu hủy đó từ số nào đến số nào, trong quyển nào.
Chương 9:

GIẢI QUYẾT KHIẾU NẠI, TỐ CÁO, VÀ KHEN THƯỞNG, XỬ LÝ VI PHẠM

Điều 64. Quyền khiếu nại của người yêu cầu công chứng, chứng thực

Người yêu cầu công chứng, chứng thực có quyền khiếu nại việc từ chối công chứng, chứng thực không đúng với quy định của pháp luật.

Điều 65. Thẩm quyền và thời hạn giải quyết khiếu nại đối với Uỷ ban nhân dân cấp xã

1. Chủ tịch Uỷ ban nhân dân cấp xã giải quyết khiếu nại lần đầu đối với việc từ chối chứng thực thuộc thẩm quyền của Uỷ ban nhân dân cấp xã, trong thời hạn không quá 5 ngày làm việc, kể từ ngày thụ lý để giải quyết khiếu nại.
```
Prediction:
```text
3. The destruction of dossiers on copies or dossiers of translations of papers must be recorded in writing with signatures of all members of the Council and comply with the law provisions on archives; such destruction must be clearly inscribed in the written records from which number to which number and in which volume. Chapter 9: SETTLEMENT OF COMPLAINTS, DENUNCIATIONS, COMMENDATION AND HANDLING OF VIOLATIONS Article 64.- The right to complaints of notarization or authentication requesters The notarization and authentication applicants may lodge complaints about the refusal to make notarizations or authentications in contravention of law. Article 65.- Competence and time limit for settlement of complaints against commune-level People’s Committees 1. The presidents of the commune- level People’
```

### Dich_vu_phap_ly/128::segment-0069::vi2en

Source:
```text
3. Người yêu cầu chứng thực không đồng ý với giải quyết khiếu nại của Chủ tịch Uỷ ban nhân dân cấp huyện, thì có quyền khiếu nại tiếp lên Chủ tịch Uỷ ban nhân dân cấp tỉnh. Trong trường hợp này, người khiếu nại phải gửi đơn kèm theo bản sao quyết định giải quyết khiếu nại của Chủ tịch Uỷ ban nhân dân cấp huyện, cấp xã và các tài liệu liên quan (nếu có) đến Chủ tịch Uỷ ban nhân dân cấp tỉnh.

Trong thời hạn không quá 20 ngày làm việc, kể từ ngày thụ lý để giải quyết tiếp đơn khiếu nại, Chủ tịch Uỷ ban nhân dân cấp tỉnh phải giải quyết và thông báo bằng văn bản cho người khiếu nại và Chủ tịch Uỷ ban nhân dân cấp huyện, cấp xã đã giải quyết khiếu nại trước đó biết. Quyết định giải quyết khiếu nại của Chủ tịch Uỷ ban nhân dân cấp tỉnh là quyết định cuối cùng.

4. Đối với khiếu nại về chứng thực phức tạp, thì thời hạn giải quyết khiếu nại của Chủ tịch Uỷ ban nhân dân cấp huyện, cấp tỉnh có thể được kéo dài nhưng không quá 30 ngày, kể từ ngày thụ lý để giải quyết.
```
Prediction:
```text
3. If the authentication requesters disagree with the complaint settlement by the district-level People’s Committee presidents, they may further lodge their complaints to the presidents of the provincial-level people’s committees. In this case, the complainants shall have to send their written complaints enclosed with copies of complaint-settling decisions of the district or commune-level presidents and relevant documents (if any) to the provincial–level People's Committees presidents. Within 20 working days as from the date of accepting the complaints for further settlement, the provincial – level People’
```

## E4: 0 available examples (up to 20)

## E5: 20 available examples (up to 20)

### Bat_dong_san/113::segment-0003::vi2en

Source:
```text
1. Sửa đổi, bổ sung khoản 5 Điều 3 như sau:

“5. Kinh phí phục vụ cho việc xây dựng, điều chỉnh kế hoạch phát triển nhà ở của địa phương được xác định như sau:
a) Kinh phí lập kế hoạch phát triển nhà ở kỳ 05 năm và năm đầu kỳ chương trình không vượt quá 50% tổng mức kinh phí xây dựng chương trình phát triển nhà ở mới được xác định tại thời điểm lập dự toán; kinh phí phục vụ cho việc nghiên cứu để điều chỉnh kế hoạch phát triển nhà ở kỳ 05 năm không vượt quá 60% tổng mức kinh phí xây dựng kế hoạch phát triển nhà ở quy định tại điểm này;

b) Kinh phí lập kế hoạch phát triển nhà ở hàng năm (trừ năm đầu kỳ chương trình) không vượt quá 20% tổng mức kinh phí xây dựng chương trình phát triển nhà ở mới được xác định tại thời điểm lập dự toán; kinh phí phục vụ cho lập điều chỉnh kế hoạch phát triển nhà ở hàng năm không vượt quá 60% tổng mức kinh phí xây dựng kế hoạch phát triển nhà ở hàng năm quy định tại điểm này.

2. Bổ sung Điều 3a vào sau Điều 3 như sau:
```
Prediction:
```text
1. Clause 5 Article 3 is amended as follows: “5. Funding for formulation and adjustment of local housing development plans shall be determined as follow: a) Funding used for formulating housing development plan for the 5th and first year of the program period shall not exceed 50% of total funding for formulate new housing development program determined at the time of estimation; funding used for research for adjustment to housing development planning for the 05th period shall be not exceed 60% of total fund for formulated housing development Plan specified at this point; b) Fundings used for making annual housing development (except for the first year) shall not be exceed 20% of total expenditure for formulates new housing Development Program defined at time of calculation; funds used for preparing adjustments to annual housing Development Plan shall not excess 60% of the total expended for formulations of annual housing growth Plan as specified in this point. 2. Article 3a shall be added after Article 3 as follow
```

### Bat_dong_san/113::segment-0004::vi2en

Source:
```text
“Điều 3a. Tiêu chí xác định nhu cầu nhà ở để xây dựng chương trình, kế hoạch phát triển nhà ở
Việc xác định nhu cầu về nhà ở khi xây dựng chương trình, kế hoạch phát triển nhà ở của địa phương được căn cứ vào các tiêu chí sau đây:

1. Các chỉ tiêu, yêu cầu về phát triển nhà ở nêu trong Chiến lược phát triển nhà ở quốc gia được Thủ tướng Chính phủ phê duyệt.

2. Các chỉ tiêu liên quan đến phát triển nhà ở nêu trong quy hoạch tỉnh, quy hoạch xây dựng của địa phương của giai đoạn thực hiện chương trình, kế hoạch phát triển nhà ở đã được cơ quan có thẩm quyền phê duyệt.
3. Quỹ đất dành cho phát triển nhà ở được xác định trong quy hoạch xây dựng, quy hoạch, kế hoạch sử dụng đất của địa phương đã được cơ quan có thẩm quyền phê duyệt.

4. Nhu cầu về diện tích nhà ở của từng đối tượng trên địa bàn theo quy định tại Điều 49 của Luật Nhà ở.

5. Các cơ chế, chính sách hỗ trợ nhà ở do Nhà nước ban hành tại thời điểm nghiên cứu, xây dựng chương trình, kế hoạch phát triển nhà ở.
```
Prediction:
```text
“Article 3a. Criteria for determination of housing demand for development of housing development programs and plans The determination on housing demand when developing local housing development program and plan shall be based on the following criteria: 1. Criteria and requirements for housing development stated in the national housing development strategy approved by the Prime Minister. 2. Criteria related to housing development specified in provincial planning, local construction planning of the stage of implementation of the housing development plan and program approved by competent agencies. 3. Land funds for housing growth shall be determined in construction planning, land use planning and plan of the locality approved by a competent agency. 4. Demand for housing area of each subject in the area under the provisions of Article 49 of the Housing Law. 5. Housing support mechanisms and policies issued by the State at the time of research and development of the program and plans for housing.
```

### Bat_dong_san/113::segment-0005::vi2en

Source:
```text
6. Thực trạng về diện tích nhà ở trên địa bàn do cơ quan có thẩm quyền cung cấp tại thời điểm xây dựng chương trình, kế hoạch phát triển nhà ở; thực trạng về nhà ở thương mại, nhà ở xã hội, nhà ở công vụ, nhà ở phục vụ tái định cư, nhà ở cho các hộ nghèo tại khu vực nông thôn và nhà ở cho các đối tượng khác trong giai đoạn 05 năm hoặc 10 năm trước đây.

7. Thực trạng về dân số và thu nhập bình quân đầu người trên địa bàn tại thời điểm xây dựng chương trình, kế hoạch, dự kiến mức tăng dân số tự nhiên, dân số cơ học do cơ quan có thẩm quyền cung cấp trong giai đoạn thực hiện chương trình, kế hoạch phát triển nhà ở.
8. Dự kiến khả năng tài chính từ ngân sách của địa phương để hỗ trợ xây dựng nhà ở dành cho các đối tượng thuộc diện được hưởng chính sách nhà ở xã hội.”
```
Prediction:
```text
6. Current housing area in the administrative division provided by competent authorities at the time of formulation of housing development programs and plans; current commercial housing, social housing, official residence, housing for resettlement, housing provided for poor households in rural areas and housing for other entities in the previous 05 years or 10 years. 7. Current population and per capita income in the local division at the moment of formulating programs, plans, estimated natural population growth, mechanical population provided by the competent authority during the implementation of housing Development Programs and Plans. 8. Estimated financial capacity from the local budget to support the construction of housing for the subjects entitled to social housing policies.”
```

### Bat_dong_san/123::segment-0001::vi2en

Source:
```text
Căn cứ Luật Tiêu chuẩn và Quy chuẩn kỹ thuật ngày 29 tháng 6 năm 2006;
Căn cứ Luật Chất lượng sản phẩm, hàng hóa ngày 21 tháng 11 năm 2007;

Căn cứ Luật An toàn thực phẩm ngày 17 tháng 6 năm 2010;
Căn cứ Luật Dược ngày 14 tháng 6 năm 2015;

Căn cứ Nghị định số 109/2018/NĐ-CP ngày 29 tháng 8 năm 2018 của Chính phủ về nông nghiệp hữu cơ;
Căn cứ Quyết định số 1819/QĐ-TTg ngày 16 tháng 11 năm 2017 của Thủ tướng Chính phủ phê duyệt Kế hoạch cơ cấu lại ngành nông nghiệp giai đoạn 2017- 2020;

Theo đề nghị của Bộ trưởng Bộ Nông nghiệp và Phát triển nông thôn.
QUYẾT ĐỊNH:

Điều 1. Phê duyệt “Đề án phát triển nông nghiệp hữu cơ giai đoạn 2020- 2030” với các nội dung chủ yếu

sau:
I. QUAN ĐIỂM

1. Đề án phát triển nông nghiệp hữu cơ giai đoạn 2020 - 2030 (sau đây gọi tắt là Đề án) nhằm phục vụ Đề án tái cơ cấu ngành nông nghiệp theo hướng nâng cao giá trị gia tăng và phát triển bền vững, thực hiện các chương trình mục tiêu quốc gia và phát huy tiềm năng thế mạnh về nông nghiệp hữu cơ của các vùng miền và địa phương.
```
Prediction:
```text
Pursuant to the Law on Standards and Technical Regulations dated June 29, 2006; Pursuance to the November 21, 2007 Law on Product and Goods Quality; Purpose to the June 17, 2010 Law on Food Safety; PurSUant to Law on Pharmacy dated July 14, 2015; Purchasing from the Government’s Decree No. 109/2018/ND-CP dated August 29, 2018 on organic agriculture; Purchase from the Prime Minister’s Decision No. 1819/QD-TTg dated November 16, 2017 approving the Agricultural Restructuring Plan for the period of 2017- 2020; Upon the proposal of the Minister of Agriculture and Rural Development. DECISION: Article 1. The scheme for organic  agricultural development for the 2020- 2030 period is approved with the following main contents: I. VIEWPOINTS 1. The Scheme for organic agricultural growth for the 2019-2020 period (hereinafter referred to as “the Scheme") is aimed at serving the Scheme on agricultural restructuring towards value-added improvement and sustainable development, implementation of national target programs and promotion of potential and strengths in organic tourism of regions and localities.
```

### Bat_dong_san/123::segment-0002::vi2en

Source:
```text
2. Phát triển nông nghiệp hữu cơ gắn với mục tiêu bảo vệ môi trường, phát triển đa dạng sinh học, góp phần phát triển du lịch, dịch vụ.
3. Phát triển nông nghiệp hữu cơ phải được triển khai cả về chiều rộng và chiều sâu theo hướng: tăng cường áp dụng rộng rãi các biện pháp hữu cơ (phân bón hữu cơ, thuốc sinh học...) trong sản xuất nông nghiệp và từng bước tăng dần tỷ lệ sản phẩm hữu cơ được chứng nhận theo yêu cầu của thị trường trong nước và thế giới.

4. Phát triển nông nghiệp hữu cơ ở các quy mô, cấp độ từ hộ gia đình, tổ hợp tác, hợp tác xã, doanh nghiệp nhằm tạo ra thực phẩm hữu cơ, môi trường an toàn cho người nông dân và sản phẩm hàng hóa có giá trị gia tăng cao.

5. Phát triển nông nghiệp hữu cơ phải huy động sự tham gia của các nhà quản lý, nhà khoa học, các tổ chức quốc tế, các thành phần kinh tế, đặc biệt là doanh nghiệp, hợp tác xã, hộ gia đình.

II. MỤC TIÊU

1. Mục tiêu tổng quát
```
Prediction:
```text
2. Develop organic agriculture in association with environmental protection and biodiversity development, contributing to tourism and service development. 3. Develop organic farming in both width and depth with the aim of widely applying organic measures (organic fertilizers, biological drugs, etc.) in agricultural production and gradually increasing the rate of certified organic products according to the requirements of the domestic and international markets. 4. Develop organic agricultural farming at household, cooperative, cooperatives and enterprise scales and levels in order to create organic food, a safe environment for farmers and high-value-added products. 5. Developing organic  farming with the participation of managers, scientists, international organizations, economic sectors, especially enterprises, cooperations and households. II. OBJECTIVES 1. General objectives
```

### Bat_dong_san/123::segment-0003::vi2en

Source:
```text
Phát triển nền nông nghiệp hữu cơ có giá trị gia tăng cao, bền vững, thân thiện với môi trường sinh thái, gắn với kinh tế nông nghiệp tuần hoàn phục vụ tiêu dùng trong nước và xuất khẩu. Sản phẩm nông nghiệp hữu cơ được chứng nhận phù hợp với tiêu chuẩn nông nghiệp hữu cơ của khu vực và thế giới; đưa Việt Nam trở thành quốc gia có trình độ sản xuất nông nghiệp hữu cơ ngang bằng các nước tiên tiến trên thế giới.

2. Mục tiêu cụ thể

a) Đến năm 2025
- Diện tích nhóm đất nông nghiệp sản xuất hữu cơ đạt khoảng 1,5-2% tổng diện tích nhóm đất nông nghiệp.

- Diện tích đất trồng trọt hữu cơ đạt khoảng trên 1% tổng diện tích đất trồng trọt với các cây trồng chủ lực: lúa, rau đậu các loại, cây ăn quả, chè, hồ tiêu, cà phê, điều, dừa...

- Tỷ lệ sản phẩm chăn nuôi hữu cơ đạt khoảng 1 - 2% tính trên tổng sản phẩm chăn nuôi sản xuất trong nước.
Các sản phẩm chăn nuôi được chứng nhận hữu cơ theo tiềm năng thế mạnh được ưu tiên: Sữa, sản phẩm mật ong, sản phẩm yến sào, thịt gia súc gia cầm...
```
Prediction:
```text
To develop organic agriculture with high added value, sustainability and eco-friendliness, in association with the cyclic agricultural economy for domestic consumption and export. Organic agricultural products will be certified to conform to regional and world organic  agricultural standards; making Vietnam a country with organic agricultural production level equal to that of advanced countries in the world. 2. Specific objectives a) By 2025. - The area of organic agriculturally-produced land will account for around 1.5-2% of the total area of agricultural land. - Organic farming land will make up over 1% of the land area under major crops: rice, legumes, fruit trees, tea, pepper, coffee, cashew, coconut, etc. - Percentage of organic animal husbandry products will account to around 1 - 2% of the domestic animal husbandRY product. Animal husbandry production products certified organic according to their potential and strengths will be prioritized: Milk, honey products, bird's nest products, cattle and poultry meat, etc
```

### Bat_dong_san/123::segment-0004::vi2en

Source:
```text
- Diện tích nuôi trồng thủy sản hữu cơ đạt khoảng 0,5-1,5% tổng diện tích nuôi trồng thủy sản, trong đó một số loài thủy đặc sản có giá trị kinh tế: tôm nước lợ, tôm càng xanh, các loài thủy sản bản địa...

- Diện tích sản xuất muối dinh dưỡng hữu cơ đạt khoảng 5 - 10% tổng diện tích sản xuất muối dinh dưỡng.

- Đối với sản phẩm dược liệu và lâm sản ngoài gỗ từ tự nhiên, tỷ lệ sản lượng hữu cơ trên tổng sản lượng đạt khoảng 90 - 95%, đối với hình thức thâm canh (sử dụng môi trường rừng để sản xuất) tỷ lệ sản lượng hữu cơ trên tổng sản lượng đạt khoảng 75 - 80%.

- Nâng cao hiệu quả của sản xuất hữu cơ trên một đơn vị diện tích; giá trị sản phẩm trên 01 ha đất trồng trọt và nuôi trồng thủy sản hữu cơ cao gấp 1,3 - 1,5 lần so với sản xuất phi hữu cơ.
```
Prediction:
```text
- The area for organic aquaculture shall be 0.5 - 1.5% of the total area for aquaculture, including some specialty aquatic species of economic value: brackish-water shrimp, giant river prawn, native aquatic animals, etc. - The areas for production of organic nutritious salt shall be 5 - 10% of the area for production. - For non-timber medicinal products and forest products from nature, the ratio of organic output to total output shall be 90 - 95%; for intensive farming (using forest environment for production), the ratio between organic output and total output is 75 - 80%. - To raise the efficiency of organic production per acreage unit; the value of products per hectare of organic land shall be 1.3 - 1.5 times higher than that of non-organic production.
```

### Bat_dong_san/123::segment-0005::vi2en

Source:
```text
- Sản xuất và tiêu thụ phân bón hữu cơ trong nước đạt 3 triệu tấn vào năm 2020 và tăng dần trong các năm tiếp theo, tăng tỷ lệ sản phẩm phân bón hữu cơ trong tổng sản phẩm phân bón lên 15% năm 2025; tăng số lượng thuốc bảo vệ thực vật sinh học trong danh mục thuốc bảo vệ thực vật được phép sử dụng lên trên 30%.

b) Đến năm 2030
- Diện tích nhóm đất nông nghiệp sản xuất hữu cơ đạt khoảng 2,5 - 3% tổng diện tích nhóm đất nông nghiệp.

- Diện tích đất trồng trọt hữu cơ đạt khoảng trên 2% tổng diện tích đất trồng trọt với các cây trồng chủ lực: lúa, rau đậu các loại, cây ăn quả, chè, hồ tiêu, cà phê, điều, dừa...

- Tỷ lệ sản phẩm chăn nuôi hữu cơ đạt khoảng 2-3% tính trên tổng sản phẩm chăn nuôi sản xuất trong nước. Các sản phẩm chăn nuôi được chứng nhận hữu cơ bao gồm: Sữa, sản phẩm mật ong, sản phẩm yến sào, thịt gia súc gia cầm...
```
Prediction:
```text
- Domestic production and consumption of organic fertilizers will reach 3 million tonnes by 2020 and gradually increase in the following years, increasing the proportion of organic products in total fertilizer products to 15% by 2025; increasing the number of biological pesticides in the list of pesticide permitted for use to over 30%. b) By 2030 - Area of agricultural land for organic production will reach about 2.5 - 3% of the total area of the agricultural area group. - Organic farming land area will reach over 2% of total farming area with key crops: rice, legumes of all kinds, fruit trees, tea, pepper, coffee, cashew, coconut, etc. - The percentage of organic animal husbandry products will reach around 2-3% of total domestic animal production. The certified organic animal breeding products include: Milk, honey products, bird's nest products, cattle and poultry meat, etc
```

### Bat_dong_san/123::segment-0006::vi2en

Source:
```text
- Diện tích nuôi trồng thủy sản hữu cơ đạt khoảng 1,5 - 3% tổng diện tích nuôi trồng thủy sản, trong đó một số loài thủy đặc sản có giá trị kinh tế: tôm nước lợ, tôm càng xanh, các loài thủy sản bản địa...

- Diện tích sản xuất muối dinh dưỡng hữu cơ đạt khoảng trên 10% tổng diện tích sản xuất muối dinh dưỡng.

- Đối với sản phẩm dược liệu và lâm sản ngoài gỗ từ tự nhiên, tỷ lệ sản lượng hữu cơ trên tổng sản lượng đạt khoảng 95 - 98%, đối với hình thức thâm canh (sử dụng môi trường rừng để sản xuất) tỷ lệ sản lượng hữu cơ trên tổng sản lượng đạt khoảng 80 - 85%.

- Giá trị sản phẩm trên 01 ha đất trồng trọt và nuôi trồng thủy sản hữu cơ cao gấp 1,5 -1,8 lần so với sản xuất phi hữu cơ.

III. NHIỆM VỤ
1. Phát triển các vùng sản xuất nông nghiệp hữu cơ tập trung và các sản phẩm hữu cơ chủ lực
```
Prediction:
```text
- The area under organic aquaculture shall account for 1.5 - 3% of the total area under aquaculture, including some specialty aquatic species of economic value: brackish water shrimps, giant river prawns, and indigenous aquatic animals, etc. - The areas under organic nutritional salt production shall accounts for over 10% of the area under production of nutritious salt. - For pharmaceutical products and non-timber forest products from the nature, the ratio of organic output to total output shall be 95 - 98%, and 80 - 85% for intensive farming (using the forest environment for production). - The value of products per hectare of organic aquacultural land shall be 1.5 - 1.8 times higher than that of non-organic production. III. TASKS 1. Developing concentrated organic agricultural production areas and key organic products
```

### Bat_dong_san/123::segment-0007::vi2en

Source:
```text
Ưu tiên sử dụng các vùng có điều kiện đất đai, khí hậu thuận lợi cho từng đối tượng cây trồng, vật nuôi để sản xuất hữu cơ; ưu tiên lựa chọn loại cây trồng, vật nuôi và giống cây trồng, vật nuôi thích ứng tốt với điều kiện thổ nhưỡng, chống chịu sâu bệnh và có thị trường tiêu thụ sản phẩm hữu cơ.

Hình thành vùng sản xuất các sản phẩm bản địa, đặc trưng có tiềm năng để xây dựng nhãn hiệu, chỉ dẫn địa lý sản phẩm để đầu tư sản xuất hữu cơ.

a) Vùng trồng trọt hữu cơ

Xác định được các vùng sản xuất hữu cơ phù hợp với các sản phẩm chủ lực như lúa, rau đậu các loại, cây ăn quả, chè, hồ tiêu, cà phê, dừa, điều... cần có kế hoạch chuyển đổi các vùng đang sản xuất các sản phẩm chủ lực này sang sản xuất hữu cơ.

- Vùng lúa hữu cơ: diện tích gieo trồng khoảng 50 - 70 nghìn ha năm 2025 và khoảng 100 - 150 nghìn ha năm 2030.

- Vùng rau đậu hữu cơ: diện tích gieo trồng đạt khoảng 10 nghìn ha năm 2025 và trên 20 nghìn ha năm 2030.
```
Prediction:
```text
To prioritize the use of areas with favorable soil and climate conditions for each plant and animal for organic production; to prioritize selection of plants, animals and plant varieties and animal breeds that are well adapted to soil conditions, resistant to pests and diseases and have outlets for organic products. To form areas for production of indigenous and typical products with potential for establishing trademarks and geographical indications for investment in organic production. a) Organic farming areas To identify organic production areas suitable to such key products as rice, legumes of all kinds, fruit trees, tea, pepper, coffee, coconut, cashew, etc., there should be a plan to convert these key products into organic ones. - Organic rice areas: the sowing area will be around 50, 000 - 70, 000 ha by 2025 and around 100, 000- 150, 000 hectares by 2030. - Organically grown vegetables and beans: the cultivation area will reach around 10, 000ha by 2025, and over 20, 000h by 2030;
```

### Bat_dong_san/123::segment-0008::vi2en

Source:
```text
- Vùng cây ăn quả các loại hữu cơ: diện tích trồng đạt khoảng 10 - 12 nghìn ha năm 2025 và khoảng 20 - 25 nghìn ha năm 2030.

- Vùng chè hữu cơ: diện tích trồng đến năm 2025 đạt khoảng 1,5 - 2 nghìn ha, năm 2030 khoảng 3 - 5 nghìn ha.

- Vùng hồ tiêu hữu cơ: diện tích hồng đến năm 2025 đạt khoảng 1,5 - 2 nghìn ha, năm 2030 đạt khoảng 3 - 4 nghìn ha.
```
Prediction:
```text
- Area for organic fruit trees: area for planting will reach about 10 - 12 thousand ha by 2025 and about 20 - 25 thousand ha in 2030. - Area of organic tea: area of planting to 2025 will reach around 1.5 - 2 thousand ha, by 2030 will be around 3 - 5 thousand ha. - Organic pepper area: area in pink will reach 1.5 -2 thousand ha to 2025, by 2025 will be about 3 - 4 thousand ha and by 2030.
```

### Bat_dong_san/123::segment-0009::vi2en

Source:
```text
- Ngoài ra còn các vùng cây trồng hữu cơ tập trung khác như vùng dừa hữu cơ khoảng 2-4 nghìn ha, vùng ca cao hữu cơ tập trung khoảng 100 ha...

b) Vùng chăn nuôi hữu cơ

Xây dựng các vùng chăn nuôi hữu cơ với các sản phẩm chủ lực như: Sữa, sản phẩm mật ong, sản phẩm yến, thịt gia súc gia cầm... riêng vùng chăn nuôi trâu, bò hữu cơ gắn với vùng đồng cỏ, vùng trồng trọt sản xuất thức ăn thô xanh hữu cơ.

- Vùng chăn nuôi trâu, bò hữu cơ: đàn trâu, bò đến năm 2025 đạt khoảng 100 - 150 nghìn con và đến năm 2030 đạt khoảng 160 - 180 nghìn con, trong đó bò sữa khoảng 10-15 nghìn con năm 2025 và khoảng 20 - 30 nghìn con năm 2030.

- Vùng chăn nuôi lợn hữu cơ: đàn lợn đạt khoảng 250 - 400 nghìn con năm 2025 và khoảng 600 - 800 nghìn con năm 2030.

- Vùng chăn nuôi gia cầm hữu cơ: đàn gia cầm đạt khoảng 5 - 8 triệu con năm 2025 và khoảng 9 - 12 triệu con năm 2030, trong đó đàn gà hữu cơ khoảng 9 - 10 triệu con.
```
Prediction:
```text
- In addition, there are other concentrated organic crop areas such as organic coconut area of about 2 - 4 thousand ha, organic cocoa area of 100 ha... b) Organic breeding area: Build organic breeding areas with key products such as: Milk, honey products, swiftlet products, poultry and cattle meat... Particularly, organic buffalo and cow breeding zones associated with grassland areas, areas for cultivation and production of organic green and crude feeds. - Organic buffoon and cows breeding zone: the herd of buffons and cocks will reach about 100 - 150 thousand by 2025 and 160 - 180 thousand by 2030, including about 10-15 thousand cows by 2025, and about 20 - 30 thousand by 2020; - Organic pig breeding region: the pig herd will reach 250 - 400 thousand by 2015 and about 600 - 800 thousand by 2020. - Organic poulture breeding site: the poultice herd shall reach about 5 - 8 million by 2025; and about 9 - 12 million by 2030; including about 9 – 10 million organic chickens.
```

### Bat_dong_san/123::segment-0010::vi2en

Source:
```text
- Vùng nuôi ong hữu cơ: sản lượng mật ong hữu cơ khoảng 5 - 8 nghìn tấn.

c) Vùng nuôi trồng thủy sản hữu cơ

Xây dựng các vùng nuôi trồng thủy sản hữu cơ với các sản phẩm chủ lực như tôm nước lợ, tôm càng xanh, các loài thủy sản bản địa... Phát triển vùng nuôi trồng thủy sản hữu cơ gắn với thị trường trong nước, xuất khẩu.
Vùng nuôi trồng thủy sản hữu cơ tập trung với diện tích mặt nước nuôi trồng thủy sản hữu cơ đạt khoảng 60 - 80 nghìn ha.

d) Vùng sản xuất muối dinh dưỡng hữu cơ

Vùng sản xuất muối dinh dưỡng hữu cơ đạt khoảng 1,7 - 2 nghìn ha.

đ) Vùng sản xuất, khai thác sản phẩm từ tự nhiên

Xây dựng và phát triển vùng sản xuất hữu cơ được chứng nhận từ các vùng sản xuất, khai thác sản phẩm tự nhiên (rừng tự nhiên, ao hồ, sông suối tự nhiên).

2. Phát triển đa dạng các hình thức tổ chức sản xuất sản phẩm hữu cơ
```
Prediction:
```text
- Organic beekeeping zones: organic honey production is expected to reach 5 - 8 thousand tonnes. c) Organic aquaculture zones: Build organic aquaculture areas with key products such as brackish-water shrimps, giant river prawns, and native aquatic species, etc. Develop organic aquacultural zones in association with domestic market and export. Concentrated organic aquatic aquaculture zone with an area of 60 - 80 thousand ha of water surface for organic aqua cultivation. d) Organic nutrient salt production zones: Organic nutrients salt production areas: 1.7 - 2 thousand ha. e) Natural products production and extraction zones: Develop organic production zones certified from natural products production zones (natural forests, ponds, lakes, natural rivers and streams). 2. Diversify forms of organic production
```

### Bat_dong_san/123::segment-0011::vi2en

Source:
```text
- Xây dựng các mô hình liên kết theo chuỗi giá trị giữa các doanh nghiệp, hợp tác xã sản xuất, chế biến, kinh doanh các sản phẩm hữu cơ tại các vùng sản xuất tập trung tạo ra hàng hóa quy mô lớn đối với các sản phẩm chủ lực.

- Khuyến khích các hình thức sản xuất quy mô hợp tác xã, doanh nghiệp, tổ hợp tác sản xuất các sản phẩm đặc sản bản địa, sản phẩm khai thác từ tự nhiên có giá trị gia tăng cao và giá trị truyền thống.

- Đẩy mạnh phong trào xây dựng vườn cây hữu cơ gắn với thu gom rác thải, làm phân hữu cơ, xây dựng môi trường xanh, sạch, đẹp ở các xã nông thôn mới.

3. Nghiên cứu phát triển và ứng dụng công nghệ trong nông nghiệp hữu cơ

- Xây dựng và hoàn thiện quy trình kỹ thuật theo hướng ứng dụng công nghệ cao kết hợp với phát huy kiến thức bản địa, sản xuất hữu cơ gắn với chuỗi giá trị cho các sản phẩm chủ lực nhằm nâng cao năng suất, chất lượng, giảm chi phí đầu vào, giảm phát thải khí nhà kính.
```
Prediction:
```text
- Build value chain-based models among enterprises and cooperatives producing, processing and trading organic products in concentrated production areas to create large-scale goods for key products. - Encourage cooperatives, enterprises, and cooperative groups to produce local specialty products, products extracted from nature with high added value and traditional value. - Promote the movement of building organic gardens associated with collecting waste, making organic fertilizer, and creating a green, clean, and beautiful environment in new rural communes. 3. Research, develop, and apply technologies in organic agriculture - Develop and complete technical processes towards applying high technologies in combination with promoting local knowledge, organic production associated with value chains for major products in order to improve productivity, quality, reduce input costs, and reduce greenhouse gas emissions.
```

### Bat_dong_san/123::segment-0012::vi2en

Source:
```text
- Nghiên cứu phát triển và ứng dụng các chế phẩm sinh học, phân hữu cơ sinh học, tác nhân phòng trừ sinh học nhằm nâng cao năng suất, chất lượng sản phẩm, thay thế kháng sinh trong chăn nuôi, nuôi trồng thủy sản; các chế phẩm sinh học xử lý môi trường nông nghiệp.

- Nghiên cứu, đánh giá thực trạng độ phì nhiêu đất, nhu cầu dinh dưỡng cho các cây trồng chủ lực phục vụ sản xuất nông nghiệp hữu cơ bền vững.

- Bảo tồn, phục tráng, khai thác, phát triển và xây dựng chỉ dẫn địa lý, nhãn hiệu tập thể cho các giống cây trồng, vật nuôi bản địa, đặc hữu, có lợi thế so sánh và giá trị kinh tế cao.

- Nghiên cứu và phát triển sản phẩm nông nghiệp hữu cơ chất lượng cao và giá trị sinh học đặc thù, đảm bảo tính cạnh tranh và đáp ứng nhu cầu bảo vệ sức khỏe của người dân.

- Nghiên cứu chọn tạo các giống cây trồng, vật nuôi có năng suất, chất lượng, đặc biệt kháng sâu bệnh, phù hợp với sản xuất hữu cơ; nghiên cứu, phát triển và sử dụng con giống, vật tư đầu vào hữu cơ trong nuôi trồng thủy sản.
```
Prediction:
```text
- Research, develop and apply biological preparations, bio-organic fertilizers, and biological preventive agents to improve productivity and product quality, replace antibiotics in animal husbandry and aquaculture, and bio-products for agricultural environment treatment. - Research and assess soil fertility and nutritional needs of key crops for sustainable organic agriculture. - Preserve, restore, exploit, develop, and establish geographical indications and collective trademarks for indigenous and endemic plant varieties and animal breeds that have comparative advantages and high economic value. - Study and develop high-quality organic products and specific biological values to ensure competitiveness and meet people’s health protection needs. - Conduct research to select and create high-yield and quality plant and animal varieties that are particularly resistant to pests and diseases and suitable for organic production; research, develop; and use breeding stocks and organic inputs in aquaculture.
```

### Bat_dong_san/123::segment-0013::vi2en

Source:
```text
- Triển khai thí điểm các mô hình sản xuất nông nghiệp hữu cơ (trồng trọt, nuôi trồng thủy sản, chăn nuôi, dược liệu và muối) gắn với chuỗi giá trị cho một số sản phẩm chủ lực, đặc sản có lợi thế của các địa phương và mô hình nghiên cứu ứng dụng chuyển giao công nghệ sản xuất nông nghiệp hữu cơ, chứng nhận sản phẩm đạt tiêu chuẩn hữu cơ tại danh mục kèm theo; từng bước nhân rộng mô hình.

4. Đào tạo, tập huấn phát triển nguồn nhân lực
- Nâng cao năng lực cho các cán bộ, công chức các cấp làm công tác quản lý, kiểm tra giám sát các tổ chức chứng nhận và sản phẩm nông nghiệp hữu cơ.

- Nâng cao năng lực chứng nhận sản phẩm hữu cơ cho các tổ chức chứng nhận.

- Đào tạo, tập huấn cho doanh nghiệp, người sản xuất, kinh doanh sản phẩm hữu cơ.

- Tăng cường giáo dục về nông nghiệp hữu cơ cho học sinh phổ thông và sinh viên các trường dạy nghề, cao đẳng và trường đại học thuộc lĩnh vực nông lâm thủy sản.
```
Prediction:
```text
- Pilot organic agriculture production models (cultivation, aquaculture, animal husbandry, herbal ingredients and salt) associated with the value chain for some key products and specialties with advantages of localities and models of research and application of transfer of organic  agricultural production technology, certification of organic standard products in the attached list; gradually expanding the model. 4. Training and developing human resources - Enhancing capacity for officials and public servants at all levels in charge of management, inspection and supervision of certification organizations and organic agricultural products. - Improving capacity for certification of Organic products for the certification organization. - Training and coaching for enterprises, producers and traders of organic products.
```

### Bat_dong_san/123::segment-0014::vi2en

Source:
```text
- Nâng cao chất lượng nguồn nhân lực cho sản xuất hữu cơ, tăng cường công tác đào tạo chuyên gia chuyên sâu về nông nghiệp hữu cơ (ở cả trung ương và địa phương); nâng cao chất lượng đào tạo, thành lập cơ sở đào tạo chuyên sâu về nông nghiệp hữu cơ được cơ quan quản lý nhà nước chỉ định.

5. Phát triển các tổ chức chứng nhận, hoàn thiện hệ thống tiêu chuẩn, quy chuẩn và quy trình kỹ thuật

- Hỗ trợ, tạo điều kiện để thành lập và phát triển các tổ chức chứng nhận sản phẩm nông nghiệp hữu cơ phù hợp với tiêu chuẩn Việt Nam.

- Từng bước hình thành hệ thống tổ chức chứng nhận của Việt Nam được thừa nhận bởi các quốc gia nhập khẩu, tổ chức chứng nhận quốc tế.

- Các tổ chức chứng nhận sản phẩm nông nghiệp hữu cơ của Việt Nam phải thực hiện đúng và nghiêm túc việc quản lý giám sát các tổ chức, cá nhân sản xuất nông nghiệp hữu cơ do đơn vị chứng nhận.
```
Prediction:
```text
- Improve the quality of human resources for organic production, intensify the training of experts specialized in organic agriculture (at both central and local levels); improve the training quality, establish specialized training institutions specializing in organic farming appointed by state management agencies. 5. Develop certification organizations, improve the system of standards, regulations and technical processes - Support and facilitate the establishment and development of certification organization of organic agricultural products in accordance with Vietnamese standards. - Step by step form a system of Vietnamese certification organization recognized by importing countries and international certification organization. - Vietnamese organic  agricultural product certification organization must strictly comply with the management and supervision of organizations and individuals producing organic  Agriculture certified by the unit.
```

### Bat_dong_san/123::segment-0015::vi2en

Source:
```text
- Xây dựng các tiêu chuẩn, quy chuẩn, quy trình kỹ thuật phục vụ sản xuất và quản lý nông nghiệp hữu cơ.
6. Tăng cường chế biến, tiêu thụ và xuất khẩu sản phẩm hữu cơ

- Ưu tiên chế biến các sản phẩm hữu cơ bao gồm các món ăn, các loại thực phẩm, đồ uống, thuốc dược liệu, mỹ phẩm...để nâng cao giá trị gia tăng.
- Xây dựng mô hình liên kết chuỗi giá trị sản phẩm nông nghiệp hữu cơ từ sản xuất đến chế biến, tiêu thụ, ứng dụng công nghệ cao để chế biến sâu, tinh chế tạo ra sản phẩm nông nghiệp hữu cơ có giá trị cao mang thương hiệu Việt Nam.

- Hỗ trợ xây dựng thương hiệu, quảng bá sản phẩm và phát triển thị trường đối với sản phẩm nông nghiệp hữu cơ Việt Nam.

- Khuyến khích các doanh nghiệp đưa các sản phẩm nông nghiệp hữu cơ vào hệ thống các siêu thị, cửa hàng tiện ích và chuỗi cung ứng sản phẩm an toàn.

7. Phát triển các vật tư đầu vào phục vụ phát triển nông nghiệp hữu cơ

- Công bố công khai danh mục các vật tư đầu vào đảm bảo tiêu chuẩn nông nghiệp hữu cơ.
```
Prediction:
```text
- Establish technical standards, regulations and procedures for organic agriculture production and management. 6. Enhance processing, sale and export of organic products - Prioritize processing of organic foods, foodstuffs, beverages, herbal medicines, cosmetics, etc. to increase added value. - Develop a model for linking the value chain of organic agricultural products from production to processing and consumption, and apply high technology for deep processing or refining to create high-value organic products bearing Vietnamese brands. - Support branding, product promotion and market development for Vietnamese organic agriculturaL products. - Encourage enterprises to introduce organic products into supermarkets, convenience stores and safe product supply chains. 7. Develop input materials for organic farming development - Publish the list of input materials meeting organic  farming standards.
```

### Bat_dong_san/123::segment-0016::vi2en

Source:
```text
- Xây dựng chính sách khuyến khích sử dụng vật tư đầu vào hữu cơ để sản xuất sản phẩm hữu cơ trong các lĩnh vực nông lâm thủy sản.

- Đa dạng nguồn sản phẩm làm thức ăn chăn nuôi, thủy sản hữu cơ như các loại thức ăn xanh, ủ chua, sấy khô, bột cá... để phát triển chăn nuôi, thủy sản hữu cơ. Phát triển và sử dụng con giống, vật tư đầu vào hữu cơ trong nuôi trồng thủy sản.

IV. GIẢI PHÁP THỰC HIỆN

1. Nâng cao hiệu lực, hiệu quả thực thi pháp luật về nông nghiệp hữu cơ

a) Phát triển vùng sản xuất nông nghiệp hữu cơ tập trung

- Các địa phương căn cứ vào lợi thế về điều kiện sinh thái, sản phẩm có thế mạnh và thị trường tiêu thụ, xác định các sản phẩm nông nghiệp hữu cơ chủ lực, trên cơ sở đó tiến hành xây dựng đề án phát triển nông nghiệp hữu cơ, đánh giá đất đai, nguồn nước, xây dựng cơ chế, chính sách hỗ trợ, định hướng phát triển các vùng sản xuất nông nghiệp hữu cơ tập trung, kêu gọi các doanh nghiệp, các hợp tác xã và người dân có nhu cầu sản xuất hữu cơ đầu tư vào sản xuất.
```
Prediction:
```text
- Formulate policies to encourage the use of organic inputs for the production of organic products in the fields of agriculture, forestry and fisheries. - Diversify the sources of products to make organic animal and aquatic feeds such as green feeds, silage, drying, fish meal, etc. to develop organic animal husbandry and aquaculture. Develop and use breeds and organic input materials in aquaculture IV. IMPLEMENTATION SOLUTIONS 1. Improve the effectiveness and efficiency of the implementation of the law on organic agriculture a) Develop concentrated organic agricultural production areas - Localities shall base on the advantages of ecological conditions, advantageous products and consumption markets to identify key organic products, on which basis to formulate schemes for organic  agricultural development, assess land and water sources, formulate mechanisms and policies to support and orientate the development of concentrated areas of organic  farming, and call on enterprises, cooperatives and people who need to produce organic to invest in production.
```

### Bat_dong_san/123::segment-0017::vi2en

Source:
```text
- Xây dựng hệ thống phân phối theo chuỗi giá trị từ sản xuất, chế biến gắn với thị trường tiêu thụ sản phẩm hữu cơ (kết hợp với du lịch, nông nghiệp sinh thái) theo đặc thù vùng miền, qua đó tổng kết bài học thành công để hoàn thiện các quy trình kỹ thuật và tập huấn, chuyển giao.

- Tăng cường sử dụng vật liệu sẵn có, tái sử dụng, khép kín chu trình trong khu vực sản xuất tạo tiền đề cho sự phát triển nông nghiệp hữu cơ ổn định (thông qua sử dụng sản phẩm từ trồng trọt làm thức ăn chăn nuôi, thủy sản và cung cấp nguyên liệu làm phân bón hữu cơ cho trồng trọt).

- Xác định các vùng có tiềm năng thế mạnh về sản xuất các sản phẩm nông nghiệp hữu cơ để khuyến khích các doanh nghiệp, các hợp tác xã và người dân có nhu cầu sản xuất sản phẩm nông nghiệp hữu cơ đầu tư vào sản xuất.

b) Quản lý đầu vào của sản xuất hữu cơ

- Quản lý giống cây trồng, vật nuôi và thủy sản hữu cơ được chứng nhận phù hợp với tiêu chuẩn nông nghiệp hữu cơ.
```
Prediction:
```text
- Build a distribution system based on the value chain from production and processing associated with the organic product consumption market (in combination with tourism and eco-agriculture) according to regional characteristics, thereby summarizing successful lessons to improve technical processes, training and transfer. - Enhance the use of available materials, reuse and close the cycle in the production area to create a premise for the stable development of organic agriculture (through the uses of crop products as animal and aquatic feed and supply of raw materials for organic fertilizer for cultivation). - Identify areas with potential and strengths in producing organic agricultural products to encourage enterprises, cooperatives and people wishing to produce organic agriculturaL products to invest in production. b) Management of inputs of organic production - Management of organic plant varieties, livestock and aquaculture products certified in accordance with organic  agricultural standards.
```

## E6: 20 available examples (up to 20)

### Bat_dong_san/113::segment-0001::vi2en

Source:
```text
SỬA ĐỔI, BỔ SUNG, BÃI BỎ MỘT SỐ ĐIỀU CỦA THÔNG TƯ SỐ 19/2016/TT-BXD NGÀY 30 THÁNG 6 NĂM 2016 VÀ THÔNG TƯ SỐ 02/2016/TT-BXD NGÀY 15 THÁNG 02 NĂM 2016 CỦA BỘ TRƯỞNG BỘ XÂY DỰNG
Căn cứ Luật Nhà ở ngày 25 tháng 11 năm 2014;

Căn cứ Nghị định số 99/2015/NĐ-CP ngày 20 tháng 10 năm 2015 của Chính phủ quy định chi tiết và hướng dẫn thi hành một số điều của Luật Nhà ở và Nghị định số 30/2021/NĐ-CP ngày 26 tháng 3 năm 2021 sửa đổi, bổ sung một số điều của Nghị định số 99/2015/NĐ-CP của Chính phủ quy định chi tiết và hướng dẫn thi hành một số điều của Luật Nhà ở;
Căn cứ Nghị định số 81/2017/NĐ-CP ngày 17 tháng 7 năm 2017 của Chính phủ quy định chức năng, nhiệm vụ, quyền hạn và cơ cấu tổ chức của Bộ Xây dựng;

Theo đề nghị của Cục trưởng Cục Quản lý nhà và thị trường bất động sản;

Bộ trưởng Bộ Xây dựng ban hành Thông tư sửa đổi, bổ sung, bãi bỏ một số điều của Thông tư số 19/2016/TT- BXD ngày 30 tháng 6 năm 2016 và Thông tư số 02/2016/TT-BXD ngày 15 tháng 02 năm 2016.
```
Prediction:
```text
AMENDMENTS TO CIRCULAR NO. 19/2016/TT-BXD DATED JUNE 30, 2016 AND CIRCULATION NO. 02/2016/ TT-B XD DATED FEBRUARY 15, 2016 OF THE MINISTER OF CONSTRUCTION Pursuant to the Housing Law dated November 25, 2014; Pursuance to the Government’s Decree No. 99/2015/ND-CP dated October 20, 2015 on guidelines for the Law on Housing and the Government's Degree No
```

### Bat_dong_san/113::segment-0006::vi2en

Source:
```text
Điều 2. Sửa đổi Quy chế quản lý, sử dụng nhà chung cư ban hành kèm theo Thông tư số 02/2016/TT-BXD

ngày 15 tháng 02 năm 2016 về ban hành Quy chế quản lý, sử dụng nhà chung cư như sau:

Bãi bỏ điểm e khoản 4 Điều 8 Quy chế quản lý, sử dụng nhà chung cư ban hành kèm theo Thông tư số 02/2016/TT-BXD ngày 15 tháng 02 năm 2016 về ban hành Quy chế quản lý, sử dụng nhà chung cư.

Điều 3. Điều khoản thi hành
```
Prediction:
```text
Article 2. Amendments to the Regulation on management and use of apartment buildings enclosed with the Circular No. 02/2016/TT-BXD dated February 15, 2016 on promulgation of the Regulations on management, use of Apartment buildings as follows: Point e Clause 4 Article 8 of the regulation on managing, using apartment building promulgated together with the Ministry of Construction's Circular no. 02/ 2016/TT
```

### Bat_dong_san/14::segment-0000::vi2en

Source:
```text
QUỐC HỘI CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM

------- Độc lập - Tự do - Hạnh phúc

Nghị quyết số: 254/2025/QH15 Hà Nội, ngày 11 tháng 12 năm 2025

NGHỊ QUYẾT
QUY ĐỊNH MỘT SỐ CƠ CHẾ, CHÍNH SÁCH THÁO GỠ KHÓ KHĂN, VƯỚNG MẮC TRONG TỔ CHỨC THI HÀNH LUẬT ĐẤT ĐAI

QUỐC HỘI
Căn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam đã được sửa đổi, bổ sung một số điều theo Nghị quyết số 203/2025/QH15;

Căn cứ Luật Ban hành văn bản quy phạm pháp luật số 64/2025/QH15 đã được sửa đổi, bổ sung một số điều theo Luật số 87/2025/QH15.
QUYẾT NGHỊ:

Chương I

QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh

Nghị quyết này quy định một số cơ chế, chính sách tháo gỡ khó khăn, vướng mắc trong tổ chức thi hành Luật Đất đai số 31/2024/QH15 đã được sửa đổi, bổ sung một số điều theo Luật số 43/2024/QH15, Luật số 47/2024/QH15, Luật số 58/2024/QH15, Luật số 71/2025/QH15, Luật số 84/2025/QH15, Luật số 93/2025/QH15 và Luật số 95/2025/QH15 (sau đây gọi là Luật Đất đai).

Điều 2. Đối tượng áp dụng

Nghị quyết này áp dụng đối với cơ quan nhà nước, người sử dụng đất, tổ chức, cá nhân có liên quan.

Chương II
```
Prediction:
```text
THE NATIONAL ASSEMBLY OF SOCIALIST REPUBLIC OF VIETNAM ------- Independence - Freedom - Happiness Resolution No. 254/2025/QH15 Hanoi, December 11, 2025 RESOLUTION DEFINING A NUMBER OF MECHANISMS AND POLICIES TO REMOVE DIFFICULTIES AND obstacles IN THE IMPLEMENTATION OF THE LAND LAW Pursuant to the Constitution of the Socialist Republic of Vietnam, which has been amended and supplemented under Resolution 203/2025-QH; Pursuance to Law No. 64/2025 on Promulgation of Legal Documents, which was amended, supplemented in accordance with the Law No
```

### Bat_dong_san/14::segment-0020::vi2en

Source:
```text
đ) Đối với dự án đầu tư thuộc trường hợp giao đất, cho thuê đất không thông qua hình thức đấu giá quyền sử dụng đất theo quy định của Luật Đất đai số 45/2013/QH13 đã được sửa đổi, bổ sung một số điều theo Luật số 35/2018/QH14, pháp luật có liên quan và phù hợp với quy hoạch sử dụng đất cấp huyện hoặc kế hoạch sử dụng đất hằng năm cấp huyện hoặc quy hoạch được lập theo quy định của pháp luật về quy hoạch đô thị và nông thôn mà các quy hoạch, kế hoạch này đã được cơ quan nhà nước có thẩm quyền phê duyệt theo quy định của pháp luật trước ngày 01 tháng 7 năm 2025 trên địa bàn hoặc chỉ tiêu sử dụng đất trong phương án phân bổ và khoanh vùng đất đai của quy hoạch tỉnh được phân bổ đến đơn vị hành chính cấp xã mà chưa thu hồi đất, giao đất, cho thuê đất thì được tiếp tục thực hiện các bước tiếp theo trong trình tự, thủ tục quy định tại Luật Đất đai nếu thuộc một trong các trường hợp sau đây:
```
Prediction:
```text
dd) If an investment project is eligible for land allocation or land lease not through auction of land use rights as prescribed in the Law on Land No. 45/2013/QH13, amended by the Law No. 35/2018/Q H14, relevant laws, and is conformable with the district-level land use planning or annual district- level land use plan, or the planning formulated in accordance with the law on urban and rural planning, and such planning or plan has been approved by a competent state authority in compliance with regulations of law before July 01, 2025 in the administrative division, or land use norms in the land distribution and zoning plan of the provincial planning have been allocated to the commune-level administrative unit, and land has not been recovered, allocates, or leases out, the following steps in the order and procedures prescribe in the Land Law shall be continued if they fall into one of the following cases:
```

### Bat_dong_san/2::segment-0000::vi2en

Source:
```text
CHÍNH PHỦ CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM

------- Độc lập - Tự do - Hạnh phúc

Số: 228/2026/NĐ-CP Hà Nội, ngày 25 tháng 6 năm 2026

NGHỊ ĐỊNH
SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA NGHỊ ĐỊNH SỐ 18/2020/NĐ-CP NGÀY 11 THÁNG 02 NĂM 2020 CỦA CHÍNH PHỦ XỬ PHẠT VI PHẠM HÀNH CHÍNH TRONG LĨNH VỰC ĐO ĐẠC VÀ BẢN ĐỒ ĐƯỢC SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU BỞI NGHỊ ĐỊNH SỐ 04/2022/NĐ-CP NGÀY 06 THÁNG 01 NĂM 2022 CỦA CHÍNH PHỦ

Căn cứ Luật Tổ chức Chính phủ số 63/2025/QH15;
Căn cứ Luật Tổ chức chính quyền địa phương số 72/2025/QH15;

Căn cứ Luật Xử lý vi phạm hành chính số 15/2012/QH13 được sửa đổi, bổ sung một số điều bởi Luật số 54/2014/QH13, Luật số 18/2017/QH14, Luật số 67/2020/QH14, Luật số 09/2022/QH15, Luật số 11/2022/QH15, Luật số 56/2024/QH15, Luật số 88/2025/QH15;

Căn cứ Luật Đo đạc và bản đồ số 27/2018/QH14 được sửa đổi, bổ sung một số điều bởi Luật số 84/2025/QH15 và Luật số 146/2025/QH15;

Căn cứ Luật Đo lường số 04/2011/QH13 được sửa đổi, bổ sung một số điều bởi Luật số 35/2018/QH14 và Luật số 84/2025/QH15;

Theo đề nghị của Bộ trưởng Bộ Nông nghiệp và Môi trường;
```
Prediction:
```text
THE GOVERNMENT SOCIALIST REPUBLIC OF VIETNAM ------- Independence - Freedom - Happiness No. 228/2026/ND-CP Hanoi, June 25, 2026 DECREE AMENDING AND SUPPLEMENTING A NUMBER OF ARTICLES OF DECREE NO. 18/2020/ND
```

### Bat_dong_san/2::segment-0001::vi2en

Source:
```text
Chính phủ ban hành Nghị định sửa đổi, bổ sung một số điều của Nghị định số 18/2020/NĐ-CP ngày 11 tháng 02 năm 2020 của Chính phủ xử phạt vi phạm hành chính trong lĩnh vực đo đạc và bản đồ được sửa đổi, bổ sung một số điều bởi Nghị định số 04/2022/NĐ-CP ngày 06 tháng 01 năm 2022 của Chính phủ.

Điều 1. Bổ sung một số điểm tại khoản 2, khoản 3 Điều 3

1. Bổ sung điểm c vào sau điểm b khoản 2

“c) Tước quyền sử dụng giấy phép hoạt động đo đạc và bản đồ, chứng chỉ hành nghề đo đạc và bản đồ từ 03 đến 09 tháng.”.

2. Bổ sung điểm k, điểm l vào sau điểm i khoản 3

“k) Buộc hủy bỏ dữ liệu, sản phẩm đo đạc và bản đồ sau khi chủ đầu tư kiểm tra, đánh giá, kết luận dữ liệu, sản phẩm không đảm bảo chất lượng theo quy định của pháp luật về đo đạc và bản đồ;
l) Buộc nộp lại số tiền bằng với giá trị tang vật, phương tiện vi phạm hành chính đã bị tiêu thụ, tẩu tán, tiêu hủy trái quy định của pháp luật.”.

Điều 2. Sửa đổi, bổ sung điểm h khoản 2 Điều 4a
```
Prediction:
```text
The Government hereby promulgates a Decree on amendments to certain articles of the Government’s Decrees No. 18/2020/ND-CP dated February 11, 2020 on penalties for administrative violations against regulations on topography and cartography amended by the Government's Degree No. 04/2022/ND–CP dating January 6, 2022. Article 1. Adding certain points to Clause 2 and Clause 3 Article 3 1. Added point c after point b of clause 2 “c) Suspension of the license for topography or cartography operations or the certificate of topography/ cartography practice for 03 to 09 months.”. 2. Added points k and l after point i of clauses 3 “k) Enforced destruction of topographic and cartographic data and products after the investor inspects, assesses and concludes that such data and product fail to meet quality standards as prescribed in law on topology and cartology; l) En forced return of an amount equal to the value of exhibits and instrumentalities of administrative violation which have been sold, dispersed or destroyed in contravention of law.”. Article 2. Amendments and supplements to point h of claus
```

### Bat_dong_san/2::segment-0028::vi2en

Source:
```text
“Điều 23a. Xử lý vi phạm hành chính trên môi trường điện tử
Việc xử lý vi phạm hành chính trong lĩnh vực đo đạc và bản đồ trên môi trường điện tử được thực hiện theo quy định tại Điều 18a Luật Xử lý vi phạm hành chính; Điều 28a và Điều 28b Nghị định số 118/2021/NĐ-CP ngày 23 tháng 12 năm 2021 của Chính phủ quy định chi tiết một số điều và biện pháp thi hành Luật Xử lý vi phạm hành chính được sửa đổi, bổ sung một số điều bởi Nghị định số 190/2025/NĐ-CP ngày 01 tháng 7 năm 2025 của Chính phủ.”.

Điều 17. Thay thế, bãi bỏ một số điều, khoản
```
Prediction:
```text
“Article 23a. Penalties for administrative violations committed in electronic environment The penalties for violations against regulations on electronic geodesy and cartography shall comply with Article 18a of the Law on Penalties For Administrative Violations; Articles 28a and 28b of the Government’s Decree No. 118/2021/ND-CP dated December 23, 2021 elaborating a number of Articles and measures for implementation of the Decrees on Penalty for Administrative violations amended by the Government's Dece
```

### Bat_dong_san/2::segment-0030::vi2en

Source:
```text
Điều 19. Điều khoản chuyển tiếp

1. Đối với hành vi vi phạm hành chính trong lĩnh vực đo đạc và bản đồ xảy ra và kết thúc trước thời điểm Nghị định này có hiệu lực mà sau đó mới bị phát hiện hoặc đang xem xét, giải quyết tại thời điểm Nghị định này đã có hiệu lực thì áp dụng Nghị định số 18/2020/NĐ-CP ngày 11 tháng 02 năm 2020 của Chính phủ xử phạt vi phạm hành chính trong lĩnh vực đo đạc và bản đồ được sửa đổi, bổ sung bởi Nghị định số 04/2022/NĐ-CP để xử lý.

2. Đối với hành vi vi phạm trong lĩnh vực đo đạc và bản đồ xảy ra trước thời điểm Nghị định này có hiệu lực thi hành nhưng vẫn đang diễn ra khi nghị định này đã có hiệu lực thì áp dụng quy định của Nghị định này để xử lý
TM. CHÍNH PHỦ KT. THỦ TƯỚNG PHÓ THỦ TƯỚNG

Hồ Quốc Dũng
```
Prediction:
```text
Article 19. Transitional provisions 1. For administrative violations against regulations on topography and cartography that are committed and terminated before the effective date of this Decree but are discovered afterwards or are under consideration at the effective time of this Circular, the Government’s Decrees No. 18/2020/ND-CP dated February 11, 2020 on penalties for administrative violation against regulations in topography, cartography and geodesy amended by the Decreed No. 04/2022/ND
```

### Bat_dong_san/45::segment-0001::vi2en

Source:
```text
ĐẤT ĐAI

Luật Đất đai số 31/2024/QH15 ngày 18 tháng 01 năm 2024 của Quốc hội, có hiệu lực kể từ ngày 01 tháng 8 năm 2024[1], được sửa đổi, bổ sung bởi:
Luật số 43/2024/QH15 ngày 29 tháng 6 năm 2024 của Quốc hội sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15, Luật Nhà ở số 27/2023/QH15, Luật Kinh doanh bất động sản số 29/2023/QH15 và Luật Các tổ chức tín dụng số 32/2024/QH15, có hiệu lực kể từ ngày 01 tháng 8 năm 2024.

Căn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam;
Quốc hội ban hành Luật Đất đai[2].

Chương I

QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh

Luật này quy định về chế độ sở hữu đất đai, quyền hạn và trách nhiệm của Nhà nước đại diện chủ sở hữu toàn dân về đất đai và thống nhất quản lý về đất đai, chế độ quản lý và sử dụng đất đai, quyền và nghĩa vụ của công dân, người sử dụng đất đối với đất đai thuộc lãnh thổ của nước Cộng hòa xã hội chủ nghĩa Việt Nam.

Điều 2. Đối tượng áp dụng
```
Prediction:
```text
LAND Law on Land No. 31/2024/QH15 dated January 18, 2024 of the National Assembly, coming into force as of August 1, 2024.[1], amended by: Law No. 43/2024 / QH15 of June 29, 2024 amending and supplementing a number of articles of Law on land No. 31, 2024/ QH 15, Law on Housing No. 27, 2023/ Q H15, Law No, 29/2023/Q H15 on real estate business and Law No 32/2024 on credit institutions, coming in force as from August 1st, 20 24. Pursuant to the Constitution of the Socialist Republic of Vietnam; The National AssemblY hereby promulgates the Land Law[2]. Chapter I GENERAL PROVISIONS Article 1. Scope This Law provides for the regime of land ownership, powers and responsibilities of the State acting as the representative of the all-people ownership of land and uniform management of land, the regime for land management and use, and rights and obligations of citizens and land users with respect to land within the territory of the socialist Republic of Viet Nam. Article 2. Subjects of application
```

### Bat_dong_san/45::segment-0142::vi2en

Source:
```text
Điều 252. Hiệu lực thi hành

1.14[13] Luật này có hiệu lực thi hành từ ngày 01 tháng 8 năm 2024, trừ trường hợp quy định tại khoản 2 và khoản 3 Điều này.
2. Điều 190 và Điều 248 của Luật này có hiệu lực thi hành từ ngày 01 tháng 4 năm 2024.

3. Việc lập, phê duyệt quy hoạch sử dụng đất được tiếp tục thực hiện theo quy định của Nghị quyết số 61/2022/QH15 ngày 16 tháng 6 năm 2022 của Quốc hội về tiếp tục tăng cường hiệu lực, hiệu quả thực hiện chính sách, pháp luật về quy hoạch và một số giải pháp tháo gỡ khó khăn, vướng mắc, đẩy nhanh tiến độ lập và nâng cao chất lượng quy hoạch thời kỳ 2021 - 2030.

Khoản 9 Điều 60 của Luật này có hiệu lực thi hành từ ngày Nghị quyết số 61/2022/QH15 hết hiệu lực.

4. Luật Đất đai số 45/2013/QH13 đã được sửa đổi, bổ sung một số điều theo Luật số 35/2018/QH14 (sau đây gọi là Luật Đất đai số 45/2013/QH13) hết hiệu lực kể từ ngày Luật này có hiệu lực thi hành.

Điều 253. Quy định chuyển tiếp về quy hoạch, kế hoạch sử dụng đất khi Luật này có hiệu lực thi hành
```
Prediction:
```text
Article 252. Effect 1.14[13] This Law comes into force from August 01, 2024, except for the cases specified in Clause 2 and Clause 3 of this Article. 2. Article 190 and Article 248 of this Law come into effect from April 01,2024. 3. The formulation and approval for land use planning shall continue to comply with the National Assembly’s Resolution No. 61/2022/QH15 dated June 16, 2022 on enhancing the effect and effectiveness of the implementation of planning policies and laws and some solutions for resolving difficulties and obstacles, accelerating the formulation progress and improving the quality of planning for the 2021- 2030 period. Clause 9 Article 60 of this law comes into effect on the date on which the Resolution no. 61-2022/ QH15 expires. 4. The Law on Land No. 45/2013/Qh13, which is amended by the Law No. 35/2018/Q H14 (hereinafter referred to as “the Law on land No.45/2013/ Q H13), shall cease to be effective on the effective date hereof. Article 253. Transitional provisions on land use plans and planning when this Law comes in force
```

### Bat_dong_san/45::segment-0149::vi2en

Source:
```text
4. Tổ chức kinh tế, hộ gia đình, cá nhân, người Việt Nam định cư ở nước ngoài thuộc trường hợp được tiếp tục sử dụng đất theo quy định tại khoản 3 Điều 60 của Luật Đất đai số 45/2013/QH13 thì được tiếp tục sử dụng đất trong thời hạn sử dụng đất còn lại mà không phải chuyển sang thuê đất theo quy định của Luật này.

5. Tổ chức kinh tế thuộc trường hợp được tiếp tục sử dụng đất theo quy định tại khoản 4 Điều 60 của Luật Đất đai số 45/2013/QH13 thì được tiếp tục sử dụng đất trong thời hạn còn lại của dự án mà không phải chuyển sang thuê đất theo quy định của Luật này.
6. Người sử dụng đất thuộc trường hợp được tiếp tục sử dụng đất theo quy định tại khoản 5 Điều 60 của Luật Đất đai số 45/2013/QH13 thì được lựa chọn tiếp tục thuê đất trong thời hạn sử dụng đất còn lại hoặc chuyển sang giao đất có thu tiền sử dụng đất theo quy định của Luật này.
```
Prediction:
```text
4. Economic organizations, households, individuals and overseas Vietnamese who are eligible for continued land use under Clause 3, Article 60 of Land Law No. 45/2013/QH13 may continue using land for the remaining land use term without having to shift to land lease under this Law. 5. Economic organization which is eligible for further land use as prescribed in Clause 4, Article60 of Land law No.45/2013/ QH13 shall be eligible for continuing using land during the remainder of the project without having To shift to lease land under this law. 6. Land users who are entitled to continue using the land as specified in Clauses 5, Articles 60 of the Land law shall be entitled to choose whether to continue renting land for remaining Land use term or shift to assigning land with collection of land use levy under this laws.
```

### Bat_dong_san/45::segment-0159::vi2en

Source:
```text
a) Đối với trường hợp giao đất, cho thuê đất theo quy định của Luật Đất đai năm 1993, Luật Đất đai số 13/2003/QH11 và các văn bản quy định chi tiết, hướng dẫn thi hành mà được bàn giao đất trên thực tế trước
ngày 01 tháng 01 năm 2005 thì chính sách thu tiền sử dụng đất, tiền thuê đất và giá đất để tính tiền sử dụng đất, tiền thuê đất áp dụng tại thời điểm bảng giá đất năm 2005 do Ủy ban nhân dân cấp tỉnh ban hành có hiệu lực thi hành;

b) Đối với trường hợp giao đất, cho thuê đất theo quy định của Luật Đất đai năm 1993, Luật Đất đai số 13/2003/QH11 và các văn bản quy định chi tiết, hướng dẫn thi hành mà được cơ quan nhà nước có thẩm quyền bàn giao đất trên thực tế từ ngày 01 tháng 01 năm 2005 đến trước ngày Luật này có hiệu lực thi hành thì chính sách thu tiền sử dụng đất, tiền thuê đất và giá đất để tính tiền sử dụng đất, tiền thuê đất được xác định tại thời điểm bàn giao đất trên thực tế;
```
Prediction:
```text
a/ For cases of land allocation or lease under the 1993 Land Law, Land Law No. 13/2003/QH11 and documents detailing and guiding the implementation, which have been actually handed over before January 1, 2005, the policies on collection of land use levy, land rent and land prices for calculation of land levy or land rent shall be applied at the effective date of the 2005 land price table promulgated by provincial-level People’s Committees; b/ For case of land allotment or leasing under the1993 Land Law or Land Law no. 13/ 2003/Qh11 and the documents detailer and guidering the implementation which have already been actually Handed over by competent state agencies from January 1st, 2005, to the date before this Law takes effect, the policies for collection of Land levy, Land rent and Land prices for determination of Land use levy or Land rent shall have to be determined at the time of actual handover;
```

### Bat_dong_san/45::segment-0166::vi2en

Source:
```text
3. Tổ chức kinh tế, hộ gia đình, cá nhân, người Việt Nam định cư ở nước ngoài đầu tư sản xuất, kinh doanh trong khu công nghiệp, cụm công nghiệp, khu chế xuất được tiếp tục sử dụng đất theo thời hạn còn lại của dự án quy định tại khoản 5 Điều 149 của Luật Đất đai số 45/2013/QH13 thì được tiếp tục sử dụng đất theo thời hạn còn lại của dự án mà không phải chuyển sang thuê đất. Khi hết thời hạn thực hiện dự án nếu có nhu cầu thì được Nhà nước xem xét cho thuê đất theo quy định của Luật này.

4. Phương án sử dụng đất, phương án xử lý, phương án sắp xếp lại, xử lý nhà, đất đã được cấp có thẩm quyền phê duyệt theo quy định tại Nghị quyết số 132/2020/QH14 của Quốc hội thí điểm một số chính sách để tháo gỡ vướng mắc, tồn đọng trong quản lý, sử dụng đất quốc phòng, an ninh kết hợp với hoạt động lao động sản xuất, xây dựng kinh tế trước ngày 01 tháng 01 năm 2025 thì thực hiện theo phương án đã phê duyệt.15[15]
```
Prediction:
```text
3. Economic organizations, households, individuals and overseas Vietnamese investing in production and business in industrial parks, industrial clusters and export processing zones may continue using land for the remaining duration of the project as prescribed in Clause 5 Article 149 of the Land Law No. 45/2013/QH13. They may continue to use land for such duration without having to lease land. Upon the expiry of the duration, if they wish, the State shall consider leasing out land in accordance with this Law. 4. Land use plans, disposition plans, property disposition plans approved by competent authorities in accordance With the National Assembly’s Resolution No. 132/2020/Q H14 on pilot implementation of a number of policies to resolve difficulties and problems in land management and use for national defense and security purposes in combination with labor, production and economic construction activities before January 1, 2025, shall be implemented in accordance to the approved plan.15[15]
```

### Bat_dong_san/77::segment-0000::vi2en

Source:
```text
BỘ XÂY DỰNG CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM

------- Độc lập - Tự do - Hạnh phúc
Số: 08/VBHN-BXD Hà Nội, ngày 25 tháng 08 năm 2023

NGHỊ ĐỊNH
VỀ PHÁT TRIỂN VÀ QUẢN LÝ NHÀ Ở XÃ HỘI

Nghị định số 100/2015/NĐ-CP ngày 20 tháng 10 năm 2015 của Chính phủ về phát triển và quản lý nhà ở xã hội được sửa đổi, bổ sung bởi:
Nghị định số 49/2021/NĐ-CP ngày 01 tháng 4 năm 2021 của Chính phủ sửa đổi, bổ sung một số điều của Nghị định số 100/2015/NĐ-CP ngày 20 tháng 10 năm 2015 của Chính phủ về phát triển và quản lý nhà ở xã hội, có hiệu lực thi hành kể từ ngày 01/4/2021.
```
Prediction:
```text
THE MINISTRY OF CONSTRUCTION SOCIALIST REPUBLIC OF VIETNAM ------- Independence - Freedom - Happiness No. 08/VBHN-BXD Hanoi, August 25, 2023 DECREE ON DEVELOPMENT AND MANAGEMENT OF SOCIAL HOUSING The Government’s Decree No. 100/2015/ND-CP dated October 20, 2015 on development and management of social housing is amended by: The Government's Degree No
```

### Bat_dong_san/77::segment-0001::vi2en

Source:
```text
Nghị định số 104/2022/NĐ-CP ngày 21 tháng 12 năm 2022 của Chính phủ sửa đổi, bổ sung một số điều của các nghị định liên quan đến việc nộp, xuất trình sổ hộ khẩu, sổ tạm trú giấy khi thực hiện thủ tục hành chính, cung cấp dịch vụ công, có hiệu lực thi hành kể từ ngày 01/01/2023.
Nghị định số 35/2023/NĐ-CP ngày 20 tháng 6 năm 2023 của Chính phủ sửa đổi, bổ sung một số điều của các Nghị định thuộc lĩnh vực quản lý nhà nước của Bộ Xây dựng, có hiệu lực thi hành kể từ ngày 20/6/2023.

Căn cứ Luật Tổ chức Chính phủ ngày 25 tháng 12 năm 2001;
Căn cứ Luật Nhà ở ngày 25 tháng 11 năm 2014;

Căn cứ Luật Xây dựng ngày 18 tháng 6 năm 2014;
Căn cứ Luật Đất đai ngày 29 tháng 11 năm 2013;

Theo đề nghị của Bộ trưởng Bộ Xây dựng;
Chính phủ ban hành Nghị định về phát triển và quản lý nhà ở xã hội1.

Chương I

NHỮNG QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
```
Prediction:
```text
The Government’s Decree No. 104/2022/ND-CP dated December 21, 2022 on amendments to a number of articles of decrees related to submission and presentation of household registration books and paper temporary residence books when carrying out administrative procedures and providing public services, which comes into force from January 01, 2020. The Government's Degree No
```

### Bat_dong_san/77::segment-0010::vi2en

Source:
```text
5. Trường hợp Nhà nước sử dụng quỹ đất 20% để xây dựng nhà ở xã hội bằng nguồn vốn hoặc hình thức quy định tại khoản 1 Điều 53 của Luật Nhà ở số 65/2014/QH13 đã được sửa đổi, bổ sung tại điểm b khoản 6 Điều 99 của Luật PPP số 64/2020/QH1414 thì chủ đầu tư dự án đầu tư xây dựng nhà ở thương mại, khu đô thị có trách nhiệm đầu tư xây dựng đồng bộ hệ thống hạ tầng kỹ thuật theo quy hoạch đã được cơ quan có thẩm quyền phê duyệt trước khi bàn giao quỹ đất này cho Nhà nước.

Khi chủ đầu tư bàn giao quỹ đất 20% để xây dựng nhà ở xã hội cho Nhà nước thì số tiền đền bù giải phóng mặt bằng theo phương án đã được cấp có thẩm quyền phê duyệt đối với quỹ đất 20% này (nếu có) sẽ được trừ vào nghĩa vụ tài chính (tiền sử dụng đất, tiền thuê đất) mà chủ đầu tư phải nộp của dự án đầu tư xây dựng nhà ở thương mại, khu đô thị đó.
```
Prediction:
```text
5. In case the State uses 20% of the land area to build social houses by using the capital sources or methods specified in Clause 1 Article 53 of the Law on Housing No. 65/2014/QH13, amended by Point b Clause 6 Article 99 of the PPP Law No. 64/2020/Q H1414, the investor in the commercial housing or urban area construction project shall be responsible for investing in the construction of a synchronous technical infrastructure system according to the planning approved by a competent authority before transferring this 20% of land area. When the investor transfers the 20% land area for building social housing to the State, the amount of land clearance compensation according to a plan approved by the competent authorities for this 20% land areas (if any) shall be deducted from the financial obligations (land levies, land rents) that the investor must pay for such commercial housing and urban area development project.
```

### Bat_dong_san/81::segment-0000::vi2en

Source:
```text
BỘ XÂY DỰNG CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM

------- Độc lập - Tự do - Hạnh phúc

Số: 03/2023/TT-BXD Hà Nội, ngày 28 tháng 4 năm 2023

THÔNG TƯ
SỬA ĐỔI, BỔ SUNG ĐIỀU 3 THÔNG TƯ SỐ 09/2021/TT-BXD NGÀY 16 THÁNG 8 NĂM 2021 CỦA BỘ TRƯỞNG BỘ XÂY DỰNG HƯỚNG DẪN THỰC HIỆN MỘT SỐ NỘI DUNG CỦA NGHỊ ĐỊNH SỐ 100/2015/NĐ-CP NGÀY 20 THÁNG 10 NĂM 2015 CỦA CHÍNH PHỦ VỀ PHÁT TRIỂN VÀ QUẢN LÝ NHÀ Ở XÃ HỘI VÀ NGHỊ ĐỊNH SỐ 49/2021/NĐ-CP NGÀY 01 THÁNG 4 NĂM 2021 CỦA CHÍNH PHỦ SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA NGHỊ ĐỊNH SỐ 100/2015/NĐ-CP NGÀY 20 THÁNG 10 NĂM 2015 CỦA CHÍNH PHỦ VỀ PHÁT TRIỂN VÀ QUẢN LÝ NHÀ Ở XÃ HỘI

Căn cứ Luật Đấu thầu ngày 26 tháng 11 năm 2013;
Căn cứ Luật Nhà ở ngày 25 tháng 11 năm 2014;

Căn cứ Luật Đầu tư ngày 17 tháng 6 năm 2020;
Căn cứ Luật Quy hoạch đô thị ngày 17 tháng 6 năm 2009;
```
Prediction:
```text
THE MINISTRY OF CONSTRUCTION SOCIALIST REPUBLIC OF VIETNAM ------- Independence - Freedom - Happiness No. 03/2023/TT-BXD Hanoi, April 28, 2023 CIRCULAR AMENDING AND SUPPLEMENTING ARTICLE 3 CIRCULATION NO. 09/2021/TT–BXD DATED AUGUST 16, 2021 OF THE MINISTER OF CONstructION GUIDING THE IMPLEMENTATION OF A NUMBER OF ARTICLES OF THE GOVERNMENT’S DECREE NO. 100/2015/ND-CP DATED OCTOBER 20, 2015 ON DEVELOPMENT AND MANAGEMENT OF SOCIAL HOUSING AND THE  GOVERS DECREE No. 49/2021-ND- CP DATED APRIL 01, 2021 ON AMENDMENTS TO THE AUTHORITY’S Decree No. 100 2015/ND
```

### Bat_dong_san/81::segment-0001::vi2en

Source:
```text
Căn cứ Luật Xây dựng ngày 18 tháng 6 năm 2014 và Luật sửa đổi, bổ sung một số điều của Luật Xây dựng ngày 17 tháng 6 năm 2020;
Căn cứ Nghị định số 100/2015/NĐ-CP ngày 20 tháng 10 năm 2015 của Chính phủ về phát triển và quản lý nhà ở xã hội và Nghị định số 49/2021/NĐ-CP ngày 01 tháng 4 năm 2021 của Chính phủ sửa đổi, bổ sung một số điều của Nghị định số 100/2015/NĐ-CP ngày 20 tháng 10 năm 2015 của Chính phủ về phát triển và quản lý nhà ở xã hội;

Căn cứ Nghị định số 25/2020/NĐ-CP ngày 28 tháng 02 năm 2020 của Chính phủ quy định chi tiết thi hành một số điều của Luật Đấu thầu về lựa chọn nhà đầu tư;
Căn cứ Nghị định số 31/2021/NĐ-CP ngày 26 tháng 3 năm 2021 của Chính phủ quy định chi tiết và hướng dẫn thi hành Luật Đầu tư;

Căn cứ Nghị định số 52/2022/NĐ-CP ngày 08 tháng 8 năm 2022 của Chính phủ quy định chức năng, nhiệm vụ, quyền hạn và cơ cấu tổ chức của Bộ Xây dựng;
```
Prediction:
```text
Pursuant to the Law on Construction dated June 18, 2014 and the Law amending and supplementing a number of articles of the Construction Law dated July 17, 2020; Pursuance to the Government’s Decree No. 100/2015/ND-CP dated October 20, 2015 on development and management of social housing and the Government's Degree No
```

### Bat_dong_san/81::segment-0002::vi2en

Source:
```text
Theo đề nghị của Cục trưởng Cục Quản lý nhà và thị trường bất động sản.
Bộ trưởng Bộ Xây dựng ban hành Thông tư sửa đổi, bổ sung Điều 3 Thông tư số 09/2021/TT-BXD ngày 16 tháng 8 năm 2021 hướng dẫn thực hiện một số nội dung của Nghị định số 100/2015/NĐ-CP ngày 20 tháng 10 năm 2015 của Chính phủ về phát triển và quản lý nhà ở xã hội và Nghị định số 49/2021/NĐ-CP ngày 01 tháng 4 năm 2021 của Chính phủ sửa đổi, bổ sung một số điều của Nghị định số 100/2015/NĐ-CP ngày 20 tháng 10 năm 2015 của Chính phủ về phát triển và quản lý nhà ở xã hội.

Điều 1. Sửa đổi, bổ sung điểm d khoản 1 Điều 3

“d. Có quy hoạch chi tiết xây dựng đã được cơ quan có thẩm quyền phê duyệt theo đúng quy định của pháp luật.
```
Prediction:
```text
At the request of the Director of the Department of Housing and Real Estate Market Management. The Minister of Construction hereby promulgates a Circular on amendments to Article 3 of the Circular No. 09/2021/TT-BXD dated August 16, 2021 providing guidance on implementation of certain contents of the Government’s Decree No. 100/2015/ND-CP dated October 20, 2015 on development and management of social housing and the Government's Degree No
```

### Bat_dong_san/9::segment-0000::vi2en

Source:
```text
CHÍNH PHỦ CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM

------- Độc lập - Tự do - Hạnh phúc

Số: 50/2026/NĐ-CP Hà Nội, ngày 31 tháng 01 năm 2026
NGHỊ ĐỊNH QUY ĐỊNH CHI TIẾT MỘT SỐ ĐIỀU CỦA NGHỊ QUYẾT SỐ 254/2025/QH15 NGÀY 11 THÁNG 12 NĂM 2025 CỦA QUỐC HỘI QUY ĐỊNH MỘT SỐ CƠ CHẾ, CHÍNH SÁCH THÁO GỠ KHÓ KHĂN, VƯỚNG MẮC TRONG TỔ CHỨC THI HÀNH LUẬT ĐẤT ĐAI VỀ TIỀN SỬ DỤNG ĐẤT, TIỀN THUÊ

ĐẤT Căn cứ Luật Tổ chức Chính phủ số 63/2025/QH15;

Căn cứ Luật Tổ chức chính quyền địa phương số 72/2025/QH15;

Căn cứ Luật Đất đai số 31/2024/QH15; được sửa đổi, bổ sung một số điều bởi các Luật số 43/2024/QH15, số 47/2024/QH15, số 58/2024/QH15, số 71/2025/QH15, số 84/2025/QH15, số 93/2025/QH15 và số 95/2025/QH15;
```
Prediction:
```text
THE GOVERNMENT SOCIALIST REPUBLIC OF VIETNAM ------- Independence - Freedom - Happiness No. 50/2026/ND-CP Hanoi, January 31, 2026 DECREE DETAILING A NUMBER OF ARTICLES OF THE NATIONAL ASSEMBLY’S RESOLUTION No. 254/2025/QH15 OF DECEMBER 11, 2025, PROVIDING FOR A  number of MECHANISM AND POLICIES TO REMOVE DIFFICULTIES IN THE IMPLEMENTATION OF THE LAND LAW REGARDING LAND USE LEVY AND LAND LEASE Pursuant to Law on Organization of the Government No. 63/2025 / QH15; Pursuance to Law No. 72/2025
```

## E7: 0 available examples (up to 20)
