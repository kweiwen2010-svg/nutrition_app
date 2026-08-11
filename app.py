import glob
import json
import os
from datetime import datetime
import pandas as pd
import streamlit as st

# 頁面基本設定 (手機版排版優化)
st.set_page_config(
    page_title="A先生的 AI 營養管家", page_icon="🥗", layout="centered"
)

# 自訂 CSS 樣式 (卡片與現代感排版)
st.markdown(
    """
    <style>
    .stMetric {
        background-color: #ffffff;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 3px 6px rgba(0,0,0,0.04);
        border-left: 5px solid #27ae60;
    }
    .highlight-card {
        background: linear-gradient(135deg, #e8f8f5 0%, #d4efdf 100%);
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #2ecc71;
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 資料儲存路徑
USER_CONFIG_PATH = "user_profile.json"
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


# 1. 個人檔案管理（含慢性病與運動狀況）
def load_user_profile():
  if os.path.exists(USER_CONFIG_PATH):
    with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
      return json.load(f)
  return {
      "name": "A先生",
      "age": 35,
      "gender": "男 (Male)",
      "weight": 72.0,
      "height": 175.0,
      "activity_level": "中度運動 (Moderately active)",
      "workout_type": "重訓 / 有氧混合",
      "chronic_conditions": ["無重大慢性病"],
  }


def save_user_profile(profile):
  with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
    json.dump(profile, f, ensure_ascii=False, indent=4)


def get_log_path(date_str):
  return os.path.join(LOG_DIR, f"{date_str}.json")


def load_log_by_date(date_str):
  path = get_log_path(date_str)
  if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
      return json.load(f)
  return {
      "meals": [],
      "total_calories": 0,
      "total_protein": 0,
      "total_carbs": 0,
      "total_fat": 0,
  }


def save_log_by_date(date_str, log_data):
  path = get_log_path(date_str)
  with open(path, "w", encoding="utf-8") as f:
    json.dump(log_data, f, ensure_ascii=False, indent=4)


# --- 載入個人資料與計算 TDEE ---
profile = load_user_profile()

if "男" in profile["gender"]:
  bmr = (
      10 * profile["weight"]
      + 6.25 * profile["height"]
      - 5 * profile["age"]
      + 5
  )
else:
  bmr = (
      10 * profile["weight"]
      + 6.25 * profile["height"]
      - 5 * profile["age"]
      - 161
  )

activity_multipliers = {
    "久坐少動 (Sedentary)": 1.2,
    "輕度運動 (Lightly active)": 1.375,
    "中度運動 (Moderately active)": 1.55,
    "高度運動 (Very active)": 1.725,
}
tdee = bmr * activity_multipliers.get(profile["activity_level"], 1.375)

# --- 側邊欄：個人設定 ---
with st.sidebar:
  st.header("⚙️ A先生的身體與健康設定")

  new_weight = st.number_input(
      "目前體重 (kg)",
      value=float(profile["weight"]),
      min_value=30.0,
      max_value=200.0,
  )
  new_activity = st.selectbox(
      "日常活動量",
      list(activity_multipliers.keys()),
      index=list(activity_multipliers.keys()).index(
          profile.get("activity_level", "中度運動 (Moderately active)")
      ),
  )

  new_workout = st.selectbox(
      "主要運動型態",
      ["完全休息/無特別運動", "重訓/肌力訓練為主", "有氧耐力為主", "重訓+有氧混合"],
      index=["完全休息/無特別運動", "重訓/肌力訓練為主", "有氧耐力為主", "重訓+有氧混合"].index(
          profile.get("workout_type", "重訓+有氧混合")
      ),
  )

  condition_options = [
      "無重大慢性病",
      "高血壓 (需控鈉)",
      "糖尿病/高血糖 (需控醣)",
      "高血脂/痛風",
  ]
  current_conditions = profile.get("chronic_conditions", ["無重大慢性病"])
  new_conditions = st.multiselect(
      "慢性病史與飲食禁忌",
      condition_options,
      default=[c for c in current_conditions if c in condition_options],
  )

  if st.button("更新健康與身體設定", type="primary"):
    profile["weight"] = new_weight
    profile["activity_level"] = new_activity
    profile["workout_type"] = new_workout
    profile["chronic_conditions"] = (
        new_conditions if new_conditions else ["無重大慢性病"]
    )
    save_user_profile(profile)
    st.success("✅ 設定更新成功！")
    st.rerun()

  st.markdown("---")
  st.metric("🔥 基礎代謝 (BMR)", f"{int(bmr)} kcal")
  st.metric("⚡ 每日消耗 (TDEE)", f"{int(tdee)} kcal")

# --- 主畫面 ---
st.title("🥗 A先生的 AI 營養管家")
st.write("結合智慧圖表分析與健康防護的次世代個人營養管理系統。")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 今日戰情室", "📸 記錄新餐點", "📅 歷史日誌", "📈 趨勢與圖表分析"]
)

today_str = datetime.now().strftime("%Y-%m-%d")

with tab1:
  st.markdown(f"### 🎯 今日戰情室 ({today_str})")
  today_log = load_log_by_date(today_str)
  current_cal = today_log["total_calories"]
  target_cal = int(tdee)
  remaining_cal = target_cal - current_cal

  col1, col2, col3 = st.columns(3)
  col1.metric("已攝取", f"{current_cal}")
  col2.metric("目標 TDEE", f"{target_cal}")
  col3.metric(
      "剩餘額度",
      f"{remaining_cal}",
      delta=f"{-current_cal} kcal",
      delta_color="inverse",
  )

  progress_val = min(float(current_cal / target_cal), 1.0) if target_cal > 0 else 0
  st.progress(progress_val)

  if current_cal > target_cal:
    st.error("⚠️ 注意：今日熱量已超標！")
  else:
    st.info(f"👍 還可以安心享用大約 {remaining_cal} kcal 的美食。")

  st.markdown("---")
  st.markdown("### 🥗 今日三大營養素分佈")
  p_g = today_log.get("total_protein", 0)
  c_g = today_log.get("total_carbs", 0)
  f_g = today_log.get("total_fat", 0)

  m_col1, m_col2, m_col3 = st.columns(3)
  m_col1.metric("🥩 蛋白質", f"{p_g} g")
  m_col2.metric("🍚 碳水化合物", f"{c_g} g")
  m_col3.metric("🥑 脂肪", f"{f_g} g")

  st.markdown("---")
  st.markdown("### 📝 今日已記錄清單")
  if today_log["meals"]:
    for i, meal in enumerate(today_log["meals"], 1):
      with st.expander(
          f"#{i} {meal['dish_name']} — 🔥 {meal['calories']} kcal"
      ):
        st.write(
            f"🥩 蛋白質: {meal['protein']}g | 🍚 碳水: {meal['carbs']}g |"
             f" 🥑 脂肪: {meal['fat']}g"
        )
        st.info(f"💡 {meal['ai_comment']}")
  else:
    st.info("🧘‍♂️ 今天還沒記錄任何餐點，快切換到分頁新增第一餐吧！")

with tab2:
  st.markdown("### 🍳 新增今日餐點紀錄")
  uploaded_file = st.file_uploader(
      "拍照上傳餐點 📷", type=["jpg", "jpeg", "png"]
  )
  if uploaded_file:
    st.image(uploaded_file, caption="準備送出解析的照片", use_container_width=True)

  food_description = st.text_input(
      "或者直接輸入文字描述 ✍️",
      placeholder="例如：一份牛肉麵加小菜...",
  )

  if st.button(
      "🚀 AI 深度解析並寫入今日日誌", type="primary", use_container_width=True
  ):
    if uploaded_file is not None or food_description:
      with st.spinner(
          f"🤖 AI 正在結合您的健康狀況（{', '.join(profile.get('chronic_conditions', ['無']))}）進行深度解析..."
      ):
        # 模擬 AI 解析結果
        mock_result = {
            "dish_name": food_description if food_description else "手機隨手拍餐點",
            "calories": 520,
            "protein": 30,
            "carbs": 60,
            "fat": 15,
            "ai_comment": (
                f"營養師短評（已結合您的身體狀況）：熱量在目標範圍內。但因您有"
                f" {profile.get('chronic_conditions', ['無'])[0]}，這餐建議少喝湯、多補充水分以代謝鈉離子。"
            ),
        }

        # 寫入當日日誌並累計三大營養素
        current_log = load_log_by_date(today_str)
        current_log["meals"].append(mock_result)
        current_log["total_calories"] += mock_result["calories"]
        current_log["total_protein"] = (
            current_log.get("total_protein", 0) + mock_result["protein"]
        )
        current_log["total_carbs"] = (
            current_log.get("total_carbs", 0) + mock_result["carbs"]
        )
        current_log["total_fat"] = (
            current_log.get("total_fat", 0) + mock_result["fat"]
        )
        save_log_by_date(today_str, current_log)

      st.balloons()
      st.success("✅ 記錄成功！已自動更新到今日戰情室與圖表！")

      st.markdown(
          f"""
            <div class="highlight-card">
                <h4>🍱 解析與健康提示</h4>
                <p>🔥 <b>熱量：</b> {mock_result['calories']} kcal</p>
                <p>🥩 <b>蛋白質：</b> {mock_result['protein']}g | 🍚 <b>碳水：</b> {mock_result['carbs']}g | 🥑 <b>脂肪：</b> {mock_result['fat']}g</p>
                <p>💡 <b>{mock_result['ai_comment']}</b></p>
            </div>
            """,
          unsafe_allow_html=True,
      )
    else:
      st.warning("⚠️ 請至少上傳照片或輸入文字描述喔！")

with tab3:
  st.markdown("### 📅 歷史日誌與長期紀錄查詢")
  log_files = glob.glob(os.path.join(LOG_DIR, "*.json"))
  available_dates = sorted(
      [os.path.basename(f).replace(".json", "") for f in log_files], reverse=True
  )

  if available_dates:
    selected_date = st.selectbox("選擇要查看的日期", available_dates)
    history_log = load_log_by_date(selected_date)

    st.markdown(f"#### 📜 {selected_date} 結算報告")
    col_h1, col_h2, col_h3 = st.columns(3)
    col_h1.metric("總攝取熱量", f"{history_log['total_calories']} kcal")
    col_h2.metric("蛋白質", f"{history_log.get('total_protein', 0)} g")
    col_h3.metric("碳水/脂肪", f"{history_log.get('total_carbs', 0)}g / {history_log.get('total_fat', 0)}g")

    st.markdown("##### 當日餐點清單：")
    if history_log["meals"]:
      for idx, meal in enumerate(history_log["meals"], 1):
        with st.expander(
            f"#{idx} {meal['dish_name']} (⚡ {meal['calories']} kcal)"
        ):
          st.write(
              f"🥩 蛋白質: {meal['protein']}g | 🍚 碳水: {meal['carbs']}g |"
               f" 🥑 脂肪: {meal['fat']}g"
          )
          st.info(f"💡 {meal['ai_comment']}")
    else:
      st.info("該日沒有記錄到任何餐點。")
  else:
    st.info("目前尚無任何歷史紀錄檔案。")

with tab4:
  st.markdown("### 📈 長期熱量趨勢與營養分析儀表板")
  st.write("追蹤您過去多日的熱量波動與 TDEE 目標比較：")

  log_files = glob.glob(os.path.join(LOG_DIR, "*.json"))
  if log_files:
    chart_data = []
    for f_path in sorted(log_files):
      d_str = os.path.basename(f_path).replace(".json", "")
      d_log = load_log_by_date(d_str)
      chart_data.append({
          "日期": d_str,
          "攝取熱量 (kcal)": d_log["total_calories"],
          "TDEE 目標線": int(tdee),
          "蛋白質 (g)": d_log.get("total_protein", 0),
          "碳水化合物 (g)": d_log.get("total_carbs", 0),
          "脂肪 (g)": d_log.get("total_fat", 0),
      })

    df = pd.DataFrame(chart_data)
    df = df.set_index("日期")

    st.markdown("#### 🔥 每日熱量攝取 vs TDEE 目標趨勢")
    st.line_chart(df[["攝取熱量 (kcal)", "TDEE 目標線"]])

    st.markdown("#### 🥗 三大營養素（蛋白質 / 碳水 / 脂肪）累積趨勢")
    st.bar_chart(df[["蛋白質 (g)", "碳水化合物 (g)", "脂肪 (g)"]])
  else:
    st.info("📊 累積幾天的飲食記錄後，這裡將會自動解鎖精美的趨勢圖表！")