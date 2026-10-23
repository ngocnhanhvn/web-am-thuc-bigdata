import os
import re
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN & GOOGLE MATERIAL CSS
# ==========================================
st.set_page_config(
    page_title="Big Data Analytics - Google Maps Food Reviews",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Tổng thể ứng dụng: Nền trắng xám chuẩn Material Design */
    .stApp { background-color: #F8F9FA; font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif; }
    
    /* Header chính: Tối ưu hóa để chữ SIÊU TO, NỔI BẬT và CỰC KỲ RÕ NÉT */
    .main-title-container {
        background: #FFFFFF;
        padding: 32px 36px;
        border-radius: 10px;
        border: 1px solid #DADCE0;
        border-left: 10px solid #1A73E8;
        box-shadow: 0 4px 12px rgba(26, 115, 232, 0.15);
        margin-bottom: 24px;
    }
    .main-title-container h1 { 
        color: #1A73E8 !important; 
        font-weight: 900 !important; 
        margin: 0 !important; 
        font-size: 42px !important; 
        letter-spacing: -0.5px; 
        line-height: 1.25;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
    }
    .main-title-container p { 
        color: #3C4043 !important; 
        margin-top: 10px !important; 
        font-size: 18px !important; 
        font-weight: 600; 
    }

    /* Sidebar chuẩn Google */
    section[data-testid="stSidebar"] { background-color: #F1F3F4 !important; border-right: 1px solid #DADCE0; }
    
    /* Làm nổi bật tiêu đề trong Sidebar */
    section[data-testid="stSidebar"] h3 {
        font-size: 18px !important;
        font-weight: 800 !important;
        color: #1A73E8 !important;
        letter-spacing: 0.5px;
        margin-top: 10px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }

    /* Tăng kích thước chữ của các tùy chọn Radio Button trong Sidebar */
    section[data-testid="stSidebar"] .stRadio label p {
        font-size: 17px !important;
        font-weight: 600 !important;
        color: #202124 !important;
    }

    /* Tăng kích thước và độ đậm của nhãn bộ lọc Sidebar */
    section[data-testid="stSidebar"] label {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #202124 !important;
    }
    
    /* KPI Card to rõ, nổi bật */
    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 20px 16px;
        border: 1px solid #DADCE0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        text-align: center;
    }
    .kpi-value { font-size: 30px; font-weight: 800; color: #1A73E8; margin-bottom: 4px; }
    .kpi-label { font-size: 13px; font-weight: 700; color: #3C4043; text-transform: uppercase; letter-spacing: 0.8px; }

    /* Review Card chuẩn Google Maps */
    .review-card {
        background-color: #FFFFFF;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #E8EAED;
        border-left: 4px solid #1A73E8;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    }
    
    /* Tăng kích thước chữ thường chuẩn */
    h3 { font-size: 22px !important; font-weight: 700 !important; color: #202124 !important; }
    h5 { font-size: 18px !important; font-weight: 700 !important; color: #3C4043 !important; }
    p, span, .stTextInput, .stSelectbox { font-size: 16px !important; color: #202124; }

    /* Tùy chỉnh màu sắc nút bấm Google Blue */
    .stButton>button {
        background-color: #1A73E8;
        color: white;
        border-radius: 4px;
        border: none;
        font-weight: 600;
        font-size: 16px;
        padding: 8px 20px;
    }
    .stButton>button:hover {
        background-color: #1557B0;
        color: white;
    }
    </style>
""",
    unsafe_allow_html=True,
)

DB_NAME = "reviews.db"


# ==========================================
# 2. HÀM XỬ LÝ & BÓC TÁCH ĐỊA LÝ THÔNG MINH
# ==========================================
def extract_geo_info(row):
  address = str(row.get("address", ""))
  district_raw = str(row.get("district", ""))
  clean_address = re.sub(r"\d{4,6}", "", address).replace("", "").strip()
  full_text = f"{clean_address} {district_raw}".lower()

  province = "Khác"
  if (
      "huế" in full_text
      or "thừa thiên huế" in full_text
      or "thua thien hue" in full_text
  ):
    province = (
        "Hà Nội"
        if "hai bà trưng, hà nội" in full_text or "ngõ huế" in full_text
        else "Huế"
    )
  elif (
      "đà nẵng" in full_text
      or "da nang" in full_text
      or "hải châu" in full_text
      or "sơn trà" in full_text
      or "ngũ hành sơn" in full_text
  ):
    province = "Đà Nẵng"
  elif (
      "quảng nam" in full_text
      or "hội an" in full_text
      or "hoi an" in full_text
      or "tam kỳ" in full_text
  ):
    province = "Quảng Nam"
  elif (
      "hà nội" in full_text
      or "ha noi" in full_text
      and "thuận hóa" not in full_text
  ):
    province = "Hà Nội"
  elif (
      "hồ chí minh" in full_text
      or "tp.hcm" in full_text
      or "sài gòn" in full_text
      or "ho chi minh" in full_text
      or district_raw in [
          "Quận 1",
          "Quận 3",
          "Quận 7",
          "Quận 9",
          "Quận 11",
          "Thủ Đức",
          "Quận Gò Vấp",
      ]
  ):
    province = "TP.HCM"
  elif "lâm đồng" in full_text or "đà lạt" in full_text:
    province = "Lâm Đồng"
  elif district_raw and district_raw != "nan" and district_raw != "None":
    province = district_raw

  sub_district = "Trung tâm " + province
  dist_match = re.search(
      r"(Quận\s+\d+|Quận\s+[A-Za-zÀ-ỹ\s]+|Huyện\s+[A-Za-zÀ-ỹ\s]+|Thị"
      r" xã\s+[A-Za-zÀ-ỹ\s]+|TP\.\s*[A-Za-zÀ-ỹ\s]+)",
      clean_address,
      re.I,
  )
  if dist_match:
    sub_district = dist_match.group(1).strip().strip(",")
  elif district_raw and district_raw not in [
      "Đà Nẵng",
      "Huế",
      "Hà Nội",
      "TP.HCM",
      "Lâm Đồng",
      "Quảng Nam",
  ]:
    sub_district = district_raw

  return pd.Series([province, sub_district])


@st.cache_data(show_spinner=False)
def load_data():
  df = pd.DataFrame()
  possible_files = [
      "merged_reviews TONG.csv",
      "merged_reviews TONG_2.csv",
      "merged_reviews.csv",
  ]

  for csv_file in possible_files:
    if os.path.exists(csv_file):
      try:
        df = pd.read_csv(csv_file, encoding="utf-8")
        break
      except Exception:
        try:
          df = pd.read_csv(csv_file, encoding="utf-8-sig")
          break
        except Exception:
          pass

  if df.empty and os.path.exists(DB_NAME):
    try:
      conn = sqlite3.connect(DB_NAME)
      df = pd.read_sql_query("SELECT * FROM restaurant_reviews", conn)
      conn.close()
    except Exception:
      pass

  if df.empty:
    return pd.DataFrame()

  try:
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("restaurant_reviews", conn, if_exists="replace", index=False)
    conn.close()
  except Exception:
    pass

  if "rating_score" in df.columns:
    df["rating_score"] = pd.to_numeric(
        df["rating_score"], errors="coerce"
    ).fillna(5.0)
  elif "rating" in df.columns:
    df["rating_score"] = pd.to_numeric(df["rating"], errors="coerce").fillna(
        5.0
    )
  else:
    df["rating_score"] = 5.0

  if "restaurant_name" not in df.columns and "Tên quán" in df.columns:
    df["restaurant_name"] = df["Tên quán"]

  if "review_text" not in df.columns and "Review text" in df.columns:
    df["review_text"] = df["Review text"]

  # Lọc bỏ các tên quán không hợp lệ / rác
  df["restaurant_name"] = df["restaurant_name"].fillna("").astype(str).str.strip()
  invalid_names = ["", "nan", "None", "Sponsored", "Quán chưa rõ tên"]
  df = df[~df["restaurant_name"].isin(invalid_names)]

  df["aspect"] = (
      df["aspect"].fillna("Món ăn") if "aspect" in df.columns else "Món ăn"
  )
  df[["Province", "SubDistrict"]] = df.apply(extract_geo_info, axis=1)

  return df


df = load_data()

# ==========================================
# 3. TIÊU ĐỀ CHÍNH ỨNG DỤNG (SIÊU TO, NỔI BẬT)
# ==========================================
st.markdown(
    """
    <div class="main-title-container">
        <h1>HỆ THỐNG PHÂN TÍCH BIG DATA ĐÁNH GIÁ ẨM THỰC GOOGLE MAPS</h1>
        <p>Nền tảng trực quan hóa dữ liệu không gian, phân tích cảm xúc và thống kê vĩ mô nhà hàng đa tỉnh thành</p>
    </div>
""",
    unsafe_allow_html=True,
)

if df.empty:
  st.warning("Chưa tìm thấy dữ liệu hợp lệ trong file CSV!")
  st.stop()

# ==========================================
# 4. SIDEBAR: ĐIỀU HƯỚNG DASHBOARD & BỘ LỌC LIÊN KẾT ĐA CẤP
# ==========================================
st.sidebar.markdown("### ĐIỀU HƯỚNG HỆ THỐNG")
dashboard_mode = st.sidebar.radio(
    "Chọn Module phân tích:",
    [
        "1. Tổng Quan Vĩ Mô & KPI",
        "2. Không Gian & Mật Độ Địa Lý",
        "3. Phân Tích Cảm Xúc & Khía Cạnh",
        "4. Xếp Hạng & Tra Cứu Drill-down",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### BỘ LỌC ĐỒNG BỘ DỮ LIỆU")

# 4.1 Bộ lọc Tỉnh / Thành phố
provinces_list = ["Tất cả Tỉnh/Thành"] + sorted(
    [p for p in df["Province"].dropna().unique() if str(p).strip()]
)
sel_province = st.sidebar.selectbox("Tỉnh / Thành phố:", provinces_list)

filtered_df = df.copy()

# 4.2 Liên kết Đa Cấp (Cascading Filter cho Quận/Huyện)
if sel_province != "Tất cả Tỉnh/Thành":
  filtered_df = filtered_df[filtered_df["Province"] == sel_province]
  subdistricts_list = ["Tất cả Quận/Huyện"] + sorted(
      [s for s in filtered_df["SubDistrict"].dropna().unique() if str(s).strip()]
  )
  sel_subdistrict = st.sidebar.selectbox(
      f"Quận/Huyện thuộc {sel_province}:", subdistricts_list
  )
  if sel_subdistrict != "Tất cả Quận/Huyện":
    filtered_df = filtered_df[filtered_df["SubDistrict"] == sel_subdistrict]

# ==========================================
# DASHBOARD 1: TỔNG QUAN VĨ MÔ & KPI
# ==========================================
if dashboard_mode == "1. Tổng Quan Vĩ Mô & KPI":
  st.markdown("### Dashboard 1: Tổng Quan Chỉ Số Vĩ Mô & Xu Hướng Tương Tác")

  k1, k2, k3, k4 = st.columns(4)
  k1.markdown(
      f'<div class="kpi-card"><div'
      f' class="kpi-value">{len(filtered_df):,}</div><div'
      ' class="kpi-label">TỔNG LƯỢT REVIEW</div></div>',
      unsafe_allow_html=True,
  )
  k2.markdown(
      f'<div class="kpi-card"><div'
      f' class="kpi-value">{filtered_df["restaurant_name"].nunique():,}</div><div'
      ' class="kpi-label">TỔNG SỐ QUÁN ĂN</div></div>',
      unsafe_allow_html=True,
  )
  avg_s = filtered_df["rating_score"].mean() if len(filtered_df) > 0 else 0
  k3.markdown(
      f'<div class="kpi-card"><div class="kpi-value"'
      f' style="color:#FBBC04;">{avg_s:.2f} ⭐</div><div'
      ' class="kpi-label">ĐIỂM SAO TRUNG BÌNH</div></div>',
      unsafe_allow_html=True,
  )
  pos_r = (
      (filtered_df["rating_score"] >= 4).mean() * 100
      if len(filtered_df) > 0
      else 0
  )
  k4.markdown(
      f'<div class="kpi-card"><div class="kpi-value"'
      f' style="color:#34A853;">{pos_r:.1f}%</div><div class="kpi-label">TỶ LỆ'
      ' HÀI LÒNG (≥4★)</div></div>',
      unsafe_allow_html=True,
  )

  st.markdown("<br>", unsafe_allow_html=True)

  c1, c2 = st.columns(2)
  with c1:
    st.markdown("##### Phân Bổ Mức Độ Đánh Giá Sao (Rating Distribution)")
    star_dist = (
        filtered_df["rating_score"].value_counts().reset_index(name="count")
    )
    star_dist.columns = ["rating", "count"]
    star_dist = star_dist.sort_values("rating")
    fig_star = px.bar(
        star_dist,
        x="rating",
        y="count",
        text="count",
        color="rating",
        color_continuous_scale="Blues",
        labels={"rating": "Mức Sao", "count": "Số Lượng Review"},
    )
    fig_star.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_star.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=350,
        showlegend=False,
    )
    st.plotly_chart(fig_star, use_container_width=True)

  with c2:
    st.markdown("##### Tỷ Lệ Đánh Giá Theo Nền Tảng (Platform Share)")
    if "platform" in filtered_df.columns:
      plat_df = (
          filtered_df["platform"].value_counts().reset_index(name="count")
      )
      plat_df.columns = ["platform", "count"]
      fig_plat = px.pie(
          plat_df,
          names="platform",
          values="count",
          hole=0.5,
          color_discrete_sequence=["#1A73E8", "#34A853", "#FBBC04", "#EA4335"],
      )
      fig_plat.update_layout(
          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350
      )
      st.plotly_chart(fig_plat, use_container_width=True)
    else:
      st.info("Không có dữ liệu trường platform.")

# ==========================================
# DASHBOARD 2: KHÔNG GIAN & MẬT ĐỘ ĐỊA LÝ
# ==========================================
elif dashboard_mode == "2. Không Gian & Mật Độ Địa Lý":
  st.markdown("### Dashboard 2: Phân Tích Mật Độ Địa Lý & Phủ Sóng Nhà Hàng")

  c1, c2 = st.columns(2)
  with c1:
    geo_col, chart_title = (
        ("Province", "Mật Độ Quán Ăn Theo Tỉnh / Thành Phố")
        if sel_province == "Tất cả Tỉnh/Thành"
        else (
            "SubDistrict",
            f"Mật Độ Quán Ăn Theo Quận / Phường ({sel_province})",
        )
    )
    st.markdown(f"##### {chart_title}")
    geo_df = (
        filtered_df.groupby(geo_col)["restaurant_name"]
        .nunique()
        .reset_index(name="so_quan")
        .sort_values(by="so_quan", ascending=False)
    )
    fig_geo = px.bar(
        geo_df,
        x="so_quan",
        y=geo_col,
        orientation="h",
        text="so_quan",
        color="so_quan",
        color_continuous_scale="Blues",
    )
    fig_geo.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_geo.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_geo, use_container_width=True)

  with c2:
    st.markdown("##### Tổng Lượng Phản Hồi (Reviews) Theo Khu Vực")
    rev_geo = (
        filtered_df.groupby(geo_col)["rating_score"]
        .count()
        .reset_index(name="tong_review")
        .sort_values(by="tong_review", ascending=False)
    )
    fig_rev_geo = px.pie(
        rev_geo,
        names=geo_col,
        values="tong_review",
        hole=0.45,
        color_discrete_sequence=["#1A73E8", "#34A853", "#FBBC04", "#EA4335"],
    )
    fig_rev_geo.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=400
    )
    st.plotly_chart(fig_rev_geo, use_container_width=True)

# ==========================================
# DASHBOARD 3: PHÂN TÍCH CẢM XÚC & KHÍA CẠNH
# ==========================================
elif dashboard_mode == "3. Phân Tích Cảm Xúc & Khía Cạnh":
  st.markdown("### Dashboard 3: Đánh Giá Cảm Xúc & Khám Phá Khía Cạnh Dịch Vụ")

  c1, c2 = st.columns(2)
  with c1:
    st.markdown("##### Phân Bổ Điểm Số Theo Các Khía Cạnh (Aspects)")
    aspect_df = (
        filtered_df.groupby(["aspect", "rating_score"])
        .size()
        .reset_index(name="count")
    )
    fig_aspect = px.bar(
        aspect_df,
        x="aspect",
        y="count",
        color="rating_score",
        barmode="stack",
        labels={
            "aspect": "Khía Cạnh",
            "count": "Số Lượng",
            "rating_score": "Mức Sao",
        },
        color_continuous_scale=["#EA4335", "#FBBC04", "#34A853"],
    )
    fig_aspect.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380
    )
    st.plotly_chart(fig_aspect, use_container_width=True)

  with c2:
    st.markdown("##### Tỷ Lệ Phân Khúc Cảm Xúc Theo Bộ Lọc")
    pos_cnt = (filtered_df["rating_score"] >= 4).sum()
    neu_cnt = (filtered_df["rating_score"] == 3).sum()
    neg_cnt = (filtered_df["rating_score"] <= 2).sum()

    fig_pie = px.pie(
        names=["Tích cực (4-5★)", "Trung tính (3★)", "Tiêu cực (1-2★)"],
        values=[pos_cnt, neu_cnt, neg_cnt],
        hole=0.5,
        color_discrete_sequence=["#34A853", "#FBBC04", "#EA4335"],
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# DASHBOARD 4: XẾP HẠNG & TRA CỨU DRILL-DOWN (LIÊN KẾT CHẶT CHẼ)
# ==========================================
elif dashboard_mode == "4. Xếp Hạng & Tra Cứu Drill-down":
  loc_label = (
      f"tại {sel_province}"
      if sel_province != "Tất cả Tỉnh/Thành"
      else "trên Toàn Quốc"
  )
  st.markdown(
      f"### Dashboard 4: Top Xếp Hạng & Tra Cứu Drill-down Thực Tế {loc_label}"
  )

  search_kw = st.text_input(
      "Nhập tên nhà hàng hoặc món ăn (VD: Cơm tấm, Bún bò, Mì Quảng...):",
      value="",
      placeholder="Gõ từ khóa để lọc...",
  )

  # [Tính liên kết 1 & 3]: Tìm kiếm CHỈ thực hiện trên filtered_df (đã lọc theo Sidebar)
  search_target_df = filtered_df.copy()

  if search_kw.strip():
    mask = search_target_df["restaurant_name"].astype(str).str.contains(
        search_kw, case=False, na=False
    ) | search_target_df["review_text"].astype(str).str.contains(
        search_kw, case=False, na=False
    )
    search_target_df = search_target_df[mask]

  if search_target_df.empty:
    st.info(
        f"Không tìm thấy nhà hàng nào phù hợp với yêu cầu {loc_label} và từ"
        " khóa."
    )
  else:
    # Gom nhóm theo quán ăn & tính điểm sao trung bình, sắp xếp giảm dần
    grouped_shops = (
        search_target_df.groupby("restaurant_name")
        .agg(
            sao_trung_binh=("rating_score", "mean"),
            tong_review=("rating_score", "count"),
            dia_chi=("address", "first"),
            url_maps=("URL", "first") if "URL" in search_target_df.columns else (
                "address",
                "first",
            ),
        )
        .reset_index()
    )

    grouped_shops = grouped_shops.sort_values(
        by=["sao_trung_binh", "tong_review"], ascending=[False, False]
    )

    st.success(
        f"Tìm thấy **{len(grouped_shops)} nhà hàng/quán ăn** thỏa mãn điều kiện"
        f" {loc_label}:"
    )

    # [Tính liên kết 3]: Drill-down hiển thị danh sách chi tiết từng quán
    for idx, shop in grouped_shops.iterrows():
      s_name = shop["restaurant_name"]
      s_star = shop["sao_trung_binh"]
      s_count = shop["tong_review"]
      s_addr = shop["dia_chi"] if pd.notna(shop["dia_chi"]) else "Chưa cập nhật"

      shop_reviews = search_target_df[
          search_target_df["restaurant_name"] == s_name
      ]

      with st.expander(
          f"🏪 {s_name} — ⭐ {s_star:.2f}/5.0 ({s_count} đánh giá)",
          expanded=(idx == 0),
      ):
        c_info, c_chart = st.columns([1.4, 1])

        with c_info:
          st.write(f"**Địa chỉ:** {s_addr}")
          st.write(f"**Điểm đánh giá trung bình:** `{s_star:.2f} / 5.0`")
          st.write(f"**Tổng số lượt bình luận:** `{s_count}` bài")

          maps_url = str(shop.get("url_maps", ""))
          if maps_url and maps_url.startswith("http"):
            st.markdown(f"[Xem chỉ đường trên Google Maps]({maps_url})")

        with c_chart:
          # [Tính liên kết 3]: Biểu đồ cảm xúc riêng biệt cho từng quán
          pos_cnt = (shop_reviews["rating_score"] >= 4).sum()
          neu_cnt = (shop_reviews["rating_score"] == 3).sum()
          neg_cnt = (shop_reviews["rating_score"] <= 2).sum()

          fig_senti = px.pie(
              names=["Tích cực (4-5★)", "Trung tính (3★)", "Tiêu cực (1-2★)"],
              values=[pos_cnt, neu_cnt, neg_cnt],
              hole=0.45,
              title=f"Biểu Đồ Cảm Xúc: {s_name}",
              color_discrete_sequence=["#34A853", "#FBBC04", "#EA4335"],
          )
          fig_senti.update_layout(
              height=220, margin=dict(l=10, r=10, t=40, b=10)
          )
          st.plotly_chart(fig_senti, use_container_width=True)

        st.markdown("---")
        # [Tính liên kết 4]: Form gửi bình luận thời gian thực (Read/Write CSDL SQLite)
        st.markdown("##### Gửi đánh giá trực tiếp cho quán này")
        with st.form(f"form_comment_{idx}"):
          col_1, col_2, col_3 = st.columns(3)
          with col_1:
            r_name = st.text_input("Tên của bạn:", value="Khách hàng")
          with col_2:
            r_star = st.selectbox("Số sao:", [5.0, 4.0, 3.0, 2.0, 1.0])
          with col_3:
            r_aspect = st.selectbox(
                "Khía cạnh:",
                ["Món ăn", "Thái độ phục vụ", "Giá cả", "Không gian", "Vị trí"],
            )

          r_text = st.text_area(
              "Nội dung nhận xét thực tế:",
              placeholder="Viết cảm nhận của bạn tại đây...",
          )
          sub_btn = st.form_submit_button("Gửi Bình Luận")

          if sub_btn:
            if r_text.strip():
              conn = sqlite3.connect(DB_NAME)
              cursor = conn.cursor()
              cursor.execute(
                  """
                                INSERT INTO restaurant_reviews 
                                (restaurant_name, address, district, reviewer_name, rating_score, review_date, review_text, aspect, platform)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                  (
                      s_name,
                      s_addr,
                      sel_province,
                      r_name,
                      r_star,
                      datetime.now().strftime("%Y-%m-%d"),
                      r_text,
                      r_aspect,
                      "Web User",
                  ),
              )
              conn.commit()
              conn.close()
              st.success("Đã gửi bình luận thành công! Hãy tải lại trang.")
              st.cache_data.clear()
            else:
              st.warning("Vui lòng nhập nội dung nhận xét!")

        st.markdown("##### Các Bài Đánh Giá Thực Tế")
        for _, r in shop_reviews.head(10).iterrows():
          star_v = r["rating_score"]
          b_color = "🟢" if star_v >= 4 else ("🟡" if star_v == 3 else "🔴")
          rev_user = (
              r.get("reviewer_name")
              if pd.notna(r.get("reviewer_name"))
              else "Khách hàng"
          )
          rev_date = (
              r.get("review_date")
              if pd.notna(r.get("review_date"))
              else "Gần đây"
          )
          rev_body = (
              r.get("review_text")
              if pd.notna(r.get("review_text"))
              else "Không có nhận xét."
          )

          st.markdown(
              f"""
                        <div class="review-card">
                            <b>{rev_user}</b> · <small>{rev_date}</small> · {b_color} <b>{star_v} ⭐</b>
                            <p style="margin-top: 6px; color: #202124; font-size: 16px;">"{rev_body}"</p>
                        </div>
                        """,
              unsafe_allow_html=True,
          )