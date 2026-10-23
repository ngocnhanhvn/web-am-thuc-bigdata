import os
import re
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ==========================================
# 1. CẤU HÌNH TRANG WEB & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="Báo Cáo Phân Tích Ẩm Thực Trong Big Data",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #F4FBF7; }
    .main-title-container {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        padding: 24px; border-radius: 20px; color: white; text-align: center;
        box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.2); margin-bottom: 25px;
    }
    .main-title-container h1 { color: #FFFFFF !important; font-weight: 800 !important; margin: 0 !important; font-size: 28px !important; }
    .main-title-container p { color: #D1FAE5 !important; margin-top: 6px !important; font-size: 14px !important; }
    section[data-testid="stSidebar"] { background-color: #E6F4ED !important; border-right: 1px solid #D1FAE5; }
    .kpi-card {
        background-color: #FFFFFF; border-radius: 16px; padding: 20px 16px;
        border: 1px solid #A7F3D0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03); text-align: center;
    }
    .kpi-value { font-size: 28px; font-weight: 800; color: #047857; margin-bottom: 4px; }
    .kpi-label { font-size: 13px; font-weight: 600; color: #6B7280; text-transform: uppercase; }
    button[data-baseweb="tab"] { border-radius: 12px !important; padding: 10px 20px !important; font-weight: 700 !important; }
    button[aria-selected="true"] { background-color: #10B981 !important; color: white !important; }
    
    /* Card Review UI */
    .review-card {
        background-color: #FFFFFF; padding: 16px; border-radius: 12px;
        border-left: 5px solid #10B981; box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 12px;
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
  if "huế" in full_text or "thừa thiên huế" in full_text:
    province = (
        "Hà Nội"
        if "hai bà trưng, hà nội" in full_text or "ngõ huế" in full_text
        else "Huế"
    )
  elif (
      "đà nẵng" in full_text
      or "hải châu" in full_text
      or "sơn trà" in full_text
      or "ngũ hành sơn" in full_text
  ):
    province = "Đà Nẵng"
  elif "quảng nam" in full_text or "hội an" in full_text:
    province = "Quảng Nam"
  elif "hà nội" in full_text and "thuận hóa" not in full_text:
    province = "Hà Nội"
  elif "hồ chí minh" in full_text or "tp.hcm" in full_text or "sài gòn" in full_text:
    province = "TP.HCM"
  elif "lâm đồng" in full_text or "đà lạt" in full_text:
    province = "Lâm Đồng"
  elif "bình định" in full_text or "quy nhơn" in full_text:
    province = "Bình Định"
  elif "an giang" in full_text or "long xuyên" in full_text:
    province = "An Giang"
  elif district_raw and district_raw != "nan":
    province = district_raw

  sub_district = "Chưa rõ"
  if province == "Huế":
    hue_sub = [
        "Thuận Hóa",
        "Phú Xuân",
        "Vỹ Dạ",
        "Vĩnh Ninh",
        "Thủy Xuân",
        "Hương Thủy",
        "Hương Trà",
        "Phú Hội",
        "Thuận Lộc",
    ]
    for sub in hue_sub:
      if sub.lower() in full_text:
        sub_district = sub
        break
    if sub_district == "Chưa rõ":
      sub_district = (
          "Đường Hà Nội (Thuận Hóa)"
          if "hà nội" in full_text or "nguyễn huệ" in full_text
          else "Trung tâm TP. Huế"
      )
  elif province == "Quảng Nam":
    qn_sub = [
        "Tam Kỳ",
        "Hội An",
        "Điện Bàn",
        "Đại Lộc",
        "Quế Sơn",
        "Phú Ninh",
        "Núi Thành",
        "Thăng Bình",
    ]
    for sub in qn_sub:
      if sub.lower() in full_text:
        sub_district = sub
        break
  elif province == "An Giang":
    ag_sub = [
        "Long Xuyên",
        "Châu Đốc",
        "Tân Châu",
        "Chợ Mới",
        "Phú Tân",
        "Thoại Sơn",
        "Tri Tôn",
    ]
    for sub in ag_sub:
      if sub.lower() in full_text:
        sub_district = sub
        break

  if sub_district in ["Chưa rõ", "Khác"]:
    dist_match = re.search(
        r"(Quận\s+\d+|Quận\s+[A-Za-zÀ-ỹ\s]+|Huyện\s+[A-Za-zÀ-ỹ\s]+|Thị"
        r" xã\s+[A-Za-zÀ-ỹ\s]+|TP\.\s*[A-Za-zÀ-ỹ\s]+)",
        clean_address,
        re.I,
    )
    if dist_match:
      sub_district = dist_match.group(1).strip().strip(",")

  sub_district = re.sub(r"\d+", "", sub_district).strip()
  if sub_district.lower() == province.lower() or not sub_district:
    sub_district = "Trung tâm " + province

  return pd.Series([province, sub_district])


@st.cache_data(show_spinner=False)
def load_data():
  if os.path.exists(DB_NAME):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM restaurant_reviews", conn)
    conn.close()
    if df.empty:
      return df
    df["rating_score"] = pd.to_numeric(df["rating_score"], errors="coerce")
    df["overall_rating"] = pd.to_numeric(df["overall_rating"], errors="coerce")
    df["aspect"] = (
        df["aspect"].fillna("Món ăn") if "aspect" in df.columns else "Món ăn"
    )
    df[["Province", "SubDistrict"]] = df.apply(extract_geo_info, axis=1)
    return df
  return pd.DataFrame()


df = load_data()

# ==========================================
# 3. BANNER TIÊU ĐỀ CHÍNH
# ==========================================
st.markdown(
    """
    <div class="main-title-container">
        <h1>📊 BÁO CÁO PHÂN TÍCH ẨM THỰC TRONG BIG DATA</h1>
        <p>Hệ thống phân tích cảm xúc & tích lũy phản hồi ẩm thực thực tế</p>
    </div>
""",
    unsafe_allow_html=True,
)

if df.empty:
  st.warning(
      "Chưa có CSDL `reviews.db` hoặc dữ liệu rỗng. Hãy khởi chạy `main.py`!"
  )
  st.stop()

# ==========================================
# 4. SIDEBAR BỘ LỌC ĐA CẤP
# ==========================================
st.sidebar.markdown("### 🎯 BỘ LỌC DỮ LIỆU")

provinces_list = ["Tất cả Tỉnh/Thành"] + sorted(
    list(df["Province"].unique())
)
sel_province = st.sidebar.selectbox("📌 Tỉnh / Thành phố:", provinces_list)

filtered_df = df.copy()

if sel_province != "Tất cả Tỉnh/Thành":
  filtered_df = filtered_df[filtered_df["Province"] == sel_province]
  subdistricts_list = ["Tất cả Quận/Huyện"] + sorted(
      list(filtered_df["SubDistrict"].unique())
  )
  sel_subdistrict = st.sidebar.selectbox(
      f"📍 Quận/Huyện/Phường thuộc {sel_province}:", subdistricts_list
  )
  if sel_subdistrict != "Tất cả Quận/Huyện":
    filtered_df = filtered_df[filtered_df["SubDistrict"] == sel_subdistrict]

st.sidebar.markdown("---")
min_star = st.sidebar.slider("⭐ Số sao tối thiểu:", 1.0, 5.0, 1.0, 0.5)
filtered_df = filtered_df[filtered_df["rating_score"] >= min_star]

kw = st.sidebar.text_input("🔍 Tìm theo tên quán / từ khóa:")
if kw:
  mask = filtered_df["restaurant_name"].str.contains(
      kw, case=False, na=False
  ) | filtered_df["review_text"].str.contains(kw, case=False, na=False)
  filtered_df = filtered_df[mask]

# ==========================================
# 5. KHU VỰC CÁC TAB CHỨC NĂNG (2-IN-1)
# ==========================================
tab_search, tab_analytics, tab_top, tab_data = st.tabs([
    "🔍 Tra Cứu & Đánh Giá Quán Ăn",
    "📊 Phân Tích Cảm Xúc & Địa Lý",
    "🏆 Top Bảng Xếp Hạng Quán",
    "📥 Dữ Liệu Chi Tiết (CSV)",
])

# ------------------------------------------
# TAB 1: TRA CỨU & BÌNH LUẬN TRỰC TIẾP (TÍCH HỢP FASTAPI/WEB)
# ------------------------------------------
with tab_search:
  st.markdown("#### 🔎 Tra Cứu Bài Đánh Giá & Vị Trí Google Maps")
  search_kw = st.text_input(
      "Nhập tên quán ăn hoặc món ăn để tra cứu bài viết thực tế:",
      value="Huế Thương",
  )

  if search_kw:
    res_df = df[
        df["restaurant_name"].str.contains(search_kw, case=False, na=False)
        | df["review_text"].str.contains(search_kw, case=False, na=False)
    ].copy()

    if res_df.empty:
      st.info(f"Khôn tìm thấy bài đánh giá nào cho từ khóa '{search_kw}'.")
    else:
      first_item = res_df.iloc[0]
      c_info, c_chart = st.columns([1.5, 1])

      with c_info:
        st.markdown(f"### 🏬 {first_item['restaurant_name']}")
        st.write(f"📍 **Địa chỉ:** {first_item.get('address', 'Chưa rõ')}")
        st.write(f"⭐ **Điểm sao trung bình:** {res_df['rating_score'].mean():.2f} / 5.0")
        st.write(f"💬 **Tổng bài review:** {len(res_df)} bài")

        maps_url = str(first_item.get("URL", ""))
        if maps_url and maps_url != "nan" and maps_url != "None":
          st.markdown(
              f"[👉 Xem chỉ đường trên Google Maps]({maps_url})",
              unsafe_allow_html=True,
          )

      with c_chart:
        pos_cnt = (res_df["rating_score"] >= 4).sum()
        neu_cnt = (res_df["rating_score"] == 3).sum()
        neg_cnt = (res_df["rating_score"] <= 2).sum()

        fig_senti = px.pie(
            names=["Tích cực (4-5★)", "Trung tính (3★)", "Tiêu cực (1-2★)"],
            values=[pos_cnt, neu_cnt, neg_cnt],
            hole=0.5,
            title="Tỷ Lệ Cảm Xúc",
            color_discrete_sequence=["#10B981", "#F59E0B", "#EF4444"],
        )
        fig_senti.update_layout(height=220, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_senti, use_container_width=True)

      st.markdown("---")
      st.markdown("##### 💬 Gửi đánh giá/bình luận mới của bạn (Tích lũy Data)")
      with st.form("add_comment_form"):
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
          rev_name = st.text_input("Tên của bạn:", value="Khách hàng")
        with col_c2:
          rev_star = st.selectbox("Số sao:", [5.0, 4.0, 3.0, 2.0, 1.0])
        with col_c3:
          rev_aspect = st.selectbox(
              "Khía cạnh:",
              ["Món ăn", "Thái độ phục vụ", "Giá cả", "Không gian", "Vị trí"],
          )

        rev_content = st.text_area(
            "Nội dung nhận xét thực tế:",
            placeholder="Viết cảm nhận của bạn tại đây...",
        )
        submit_btn = st.form_submit_button("🚀 Gửi Bình Luận Ngay")

        if submit_btn:
          if rev_content.strip():
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                """
                            INSERT INTO restaurant_reviews 
                            (restaurant_name, address, district, reviewer_name, rating_score, review_date, review_text, aspect, platform)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                (
                    first_item["restaurant_name"],
                    first_item.get("address", ""),
                    first_item.get("district", "Khác"),
                    rev_name,
                    rev_star,
                    datetime.now().strftime("%Y-%m-%d"),
                    rev_content,
                    rev_aspect,
                    "Web User",
                ),
            )
            conn.commit()
            conn.close()
            st.success("🎉 Đã gửi bình luận thành công! Vui lòng tải lại trang.")
            st.cache_data.clear()
          else:
            st.warning("Vui lòng nhập nội dung bình luận!")

      st.markdown("---")
      st.markdown("##### 📜 Danh Sách Bài Review Từ Thực Khách")
      for _, r in res_df.iterrows():
        star_val = r["rating_score"]
        badge_color = (
            "🟢" if star_val >= 4 else ("🟡" if star_val == 3 else "🔴")
        )
        st.markdown(
            f"""
            <div class="review-card">
                <b>👤 {r.get('reviewer_name', 'Khách hàng')}</b> · <small>{r.get('review_date', 'Gần đây')}</small> · {badge_color} <b>{star_val} ⭐</b>
                <p style="margin-top: 6px; color: #374151; italic">"{r.get('review_text', 'Không có câu bình luận.')}"</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ------------------------------------------
# TAB 2: BIỂU ĐỒ BÁO CÁO PHÂN TÍCH
# ------------------------------------------
with tab_analytics:
  # Hiển thị thẻ KPI
  k1, k2, k3, k4 = st.columns(4)
  k1.markdown(
      f'<div class="kpi-card"><div'
      f' class="kpi-value">{len(filtered_df):,}</div><div'
      ' class="kpi-label">📦 TỔNG LƯỢT REVIEW</div></div>',
      unsafe_allow_html=True,
  )
  k2.markdown(
      f'<div class="kpi-card"><div'
      f' class="kpi-value">{filtered_df["restaurant_name"].nunique():,}</div><div'
      ' class="kpi-label">🏪 TỔNG SỐ QUÁN ĂN</div></div>',
      unsafe_allow_html=True,
  )
  avg_s = filtered_df["rating_score"].mean()
  k3.markdown(
      f'<div class="kpi-card"><div class="kpi-value"'
      f' style="color:#D97706;">{avg_s:.2f} ⭐</div><div class="kpi-label">⭐ SAO'
      ' TRUNG BÌNH</div></div>',
      unsafe_allow_html=True,
  )
  pos_r = (
      (filtered_df["rating_score"] >= 4).mean() * 100
      if len(filtered_df) > 0
      else 0
  )
  k4.markdown(
      f'<div class="kpi-card"><div class="kpi-value"'
      f' style="color:#059669;">{pos_r:.1f}%</div><div class="kpi-label">👍 TỶ LỆ'
      ' TÍCH CỰC (≥4★)</div></div>',
      unsafe_allow_html=True,
  )

  st.markdown("<br>", unsafe_allow_html=True)

  c_left, c_right = st.columns(2)
  with c_left:
    st.markdown("##### ⚖️ Cảm Xúc Theo 5 Khía Cạnh Dịch Vụ")
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
        labels={
            "aspect": "Khía Cạnh",
            "count": "Số Lượng Review",
            "rating_score": "Mức Sao",
        },
        color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
    )
    fig_aspect.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380
    )
    st.plotly_chart(fig_aspect, use_container_width=True)

  with c_right:
    geo_col, chart_title = (
        ("Province", "Tỷ Lệ Phân Bổ Theo Tỉnh / Thành Phố")
        if sel_province == "Tất cả Tỉnh/Thành"
        else (
            "SubDistrict",
            f"Tỷ Lệ Phân Bổ Theo Quận / Phường ({sel_province})",
        )
    )
    st.markdown(f"##### 🗺️ {chart_title}")
    geo_df = (
        filtered_df.groupby(geo_col)["restaurant_name"]
        .nunique()
        .reset_index(name="so_quan")
    )
    fig_geo = px.pie(
        geo_df,
        names=geo_col,
        values="so_quan",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_geo.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380
    )
    st.plotly_chart(fig_geo, use_container_width=True)

# ------------------------------------------
# TAB 3: BẢNG XẾP HẠNG TOP QUÁN
# ------------------------------------------
with tab_top:
  loc_name = (
      sel_province if sel_province != "Tất cả Tỉnh/Thành" else "Toàn Quốc"
  )
  st.markdown(f"##### 🏆 Top 10 Quán Đạt Chỉ Số Đánh Giá Cao Nhất ({loc_name})")
  top_shops = (
      filtered_df.groupby(["restaurant_name", "Province", "SubDistrict"])
      .agg(sao_tb=("rating_score", "mean"), total=("rating_score", "count"))
      .reset_index()
  )
  top10 = top_shops.sort_values(
      by=["sao_tb", "total"], ascending=[False, False]
  ).head(10)

  fig_top = px.bar(
      top10.iloc[::-1],
      x="sao_tb",
      y="restaurant_name",
      orientation="h",
      text="sao_tb",
      color="SubDistrict" if sel_province != "Tất cả Tỉnh/Thành" else "Province",
      range_x=[1, 5.2],
      labels={"sao_tb": "Sao Trung Bình", "restaurant_name": "Tên Quán"},
      color_discrete_sequence=px.colors.qualitative.Pastel,
  )
  fig_top.update_traces(texttemplate="%{text:.2f} ⭐", textposition="outside")
  fig_top.update_layout(
      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=420
  )
  st.plotly_chart(fig_top, use_container_width=True)

# ------------------------------------------
# TAB 4: XUẤT DỮ LIỆU CSV
# ------------------------------------------
with tab_data:
  st.markdown("##### 📥 Danh Sách Dữ Liệu Đã Trích Xuất")
  st.dataframe(filtered_df, height=350, use_container_width=True)
  csv_data = filtered_df.to_csv(index=False, encoding="utf-8-sig")
  st.download_button(
      label="🚀 Tải xuống File Báo Cáo CSV (.csv)",
      data=csv_data,
      file_name="baocao_danhgia_quanan.csv",
      mime="text/csv",
  )