from datetime import datetime
import json
import os
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import streamlit as st

# --- 1. 基本設定與路徑 ---
st.set_page_title_page_icon = "🥗"
st.set_page_config(
    page_title="A先生的 AI 營養管家", page_icon="🥗", layout="centered"
)

PROFILE_FILE = "user_profile.json"
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
  os.makedirs(LOG_DIR)


# --- 2. 個人資料管理函式 ---
def load_user_profile():
  if os.path.exists(PROFILE_FILE):
    with open(PROFILE_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return {
      "age": 30,
      "gender": "男",
      "height": 175,
      "weight": 70,
      "activity_level": "中度活動量 (每週運動3-5天)",
      "goal": "維持體重",
      "medical_history": "無",
  }


def save_user_profile(profile_data):
  with open(PROFILE_FILE, "w", encoding="utf-8") as f:
    json.dump(profile_data, f, ensure_ascii=False, indent=4)


profile = load_user_profile()

# --- 3. 計算 BMR、TDEE 與目標熱量 ---
if profile["gender"] == "男":
  bmr = (
      10 * profile["weight"] + 6.25 * profile["height"] - 5 * profile["age"] + 5
  )
else:
  bmr = (
      10 * profile["weight"]
      + 6.25 * profile["height"]
      - 5 * profile["age"]
      - 161
  )

activity_multipliers = {
    "久坐不動 (幾乎不運動)": 1.2,
    "輕度活動量 (每週運動1-3天)": 1.375,
    "中度活動量 (每週運動3-5天)": 1.55,
    "高度活動量 (每週運動6-7天)": 1.725,
}
multiplier = activity_multipliers.get(profile["activity_level"], 1.55)
tdee = bmr * multiplier

if "減脂" in profile["goal"]:
  target_calories = int(tdee - 500)
elif "增肌" in profile["goal"]:
  target_calories = int(tdee + 300)
else:
  target_calories = int(tdee)


# --- 4. 日誌讀寫函式 ---
def get_today_str():
  return datetime.now().strftime("%Y-%m-%d")


def load_daily_log(date_str):
  file_path = os.path.join(LOG_DIR, f"{date_str}.json")
  if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
      return json.load(f)
  return []


def save_daily_log(date_str, logs):
  file_path = os.path.join(LOG_DIR, f"{date_str}.json")
  with open(file_path, "w", encoding="utf-8") as f:
    json.dump(logs, f, ensure_ascii=False, indent=4)


# --- 5. 側邊欄：個人設定表單 ---
with st.sidebar:
  st.subheader("⚙️ 個人身體設定")
  st.caption("輸入一次永久記憶，自動計算專屬熱量")

  with st.form("profile_form"):
    age = st.number_input("年齡", value=profile.get("age", 30))
    gender = st.selectbox(
        "生理性別", ["男", "女"], index=0 if profile.get("gender") == "男" else 1
    )
    height = st.number_input("身高 (cm)", value=profile.get("height", 175))
    weight = st.number_input("體重 (kg)", value=profile.get("weight", 70.0))

    activity_options = [
        "久坐不動 (幾乎不運動)",
        "輕度活動量 (每週運動1-3天)",
        "中度活動量 (每週運動3-5天)",
        "高度活動量 (每週運動6-7天)",
    ]
    current_activity = profile.get("activity_level", activity_options[2])
    activity_idx = (
        activity_options.index(current_activity)
        if current_activity in activity_options
        else 2
    )
    activity_level = st.selectbox(
        "日常活動量", activity_options, index=activity_idx
    )

    goal_options = ["減脂期 (-500 kcal)", "維持體重", "增肌期 (+300 kcal)"]
    current_goal = profile.get("goal", "維持體重")
    goal_idx = (
        goal_options.index(current_goal) if current_goal in goal_options else 1
    )
    goal = st.selectbox("體重管理目標", goal_options, index=goal_idx)

    medical_history = st.text_input(
        "疾病史 / 飲食禁忌 (如: 高血壓、糖尿病)",
        value=profile.get("medical_history", "無"),
    )

    submitted = st.form_submit_button("💾 儲存個人資料")
    if submitted:
      new_profile = {
          "age": age,
          "gender": gender,
          "height": height,
          "weight": weight,
          "activity_level": activity_level,
          "goal": goal,
          "medical_history": medical_history,
      }
      save_user_profile(new_profile)
      st.success("個人資料已更新！")
      st.rerun()

  st.markdown("---")
  st.markdown(f"**🔥 您的基礎代謝率 (BMR):** {int(bmr)} kcal")
  st.markdown(f"**⚡ 每日總消耗 (TDEE):** {int(tdee)} kcal")
  st.markdown(f"**🎯 目標建議熱量:** **{target_calories} kcal**")

# --- 6. 主畫面標題與導航分頁 ---
st.title("🥗 A先生的 AI 營養管家")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 今日戰情室", "📸 記錄新餐點", "📅 歷史日誌", "📈 趨勢分析"]
)

# 取得今日資料
today_str = get_today_str()
today_logs = load_daily_log(today_str)
total_eaten = sum([item.get("calories", 0) for item in today_logs if isinstance(item, dict)])
# --- 分頁 1：今日戰情室 ---
with tab1:
  st.subheader("🔥 今日熱量戰情室")

  col1, col2 = st.columns(2)
  with col1:
    st.metric(
        label="今日目標",
        value=f"{target_calories} kcal",
        delta=f"TDEE: {int(tdee)}",
    )
  with col2:
    st.metric(
        label="已攝取",
        value=f"{total_eaten} kcal",
        delta=f"剩餘: {target_calories - total_eaten} kcal",
        delta_color="inverse",
    )

  # 進度條
  progress = min(float(total_eaten / target_calories), 1.0) if target_calories > 0 else 0
  st.progress(progress)

  st.markdown("### 📝 今日已記錄餐點")
  if not today_logs:
    st.info("今天還沒有記錄任何餐點，快去「記錄新餐點」拍照吧！")
  else:
    for idx, item in enumerate(today_logs):
      with st.expander(
          f"🍽️ {item.get('name', '餐點')} - {item.get('calories', 0)} kcal"
      ):
        st.write(f"**蛋白質:** {item.get('protein', 0)} g")
        st.write(f"**碳水化合物:** {item.get('carbs', 0)} g")
        st.write(f"**脂肪:** {item.get('fat', 0)} g")
        st.write(f"**營養師建議:** {item.get('advice', '無')}")

# --- 分頁 2：記錄新餐點 ---
with tab2:
  st.subheader("🍳 新增今日餐點記錄")

  # 支援手機直接拍照或上傳
  captured_image = st.camera_input("📸 拍下您的餐點")
  user_memo = st.text_input("或輸入文字描述（例如：一碗牛肉麵、少油少鹽）")

  if st.button("🚀 AI 深度解析", type="primary"):
    if captured_image is not None or user_memo:
      with st.spinner("🤖 AI 營養師正在分析熱量與疾病禁忌..."):
        try:
          # 初始化 Gemini API
          api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
          genai.configure(api_key=api_key)
          model = genai.GenerativeModel("gemini-2.5-flash")

          prompt = f"""
                    你是一個專業的臨床營養師。
                    使用者個人身體背景：
                    - 年齡：{profile['age']} 歲
                    - 身體狀況/疾病史：{profile['medical_history']}
                    - 目標：{profile['goal']}

                    請分析這張餐點照片或文字描述（文字備註: {user_memo}）。
                    請嚴格回傳一個 JSON 格式（不要包覆在 markdown 語法中），包含以下欄位：
                    {{
                        "name": "餐點名稱",
                        "calories": 估算熱量數字(整數),
                        "protein": 蛋白質克數(數字),
                        "carbs": 碳水化合物克數(數字),
                        "fat": 脂肪克數(數字),
                        "advice": "針對使用者疾病史({profile['medical_history']})給予的營養建議或紅黃燈警告"
                    }}
                    """

          if captured_image is not None:
            bytes_data = captured_image.getvalue()
            image_part = {
                "mime_type": "image/jpeg",
                "data": bytes_data,
            }
            response = model.generate_content([image_part, prompt])
          else:
            response = model.generate_content([prompt])

          # 解析 AI 回傳的 JSON
          res_text = (
              response.text.replace("```json", "")
              .replace("```", "")
              .strip()
          )
          meal_data = json.loads(res_text)

          # 存入今日日誌
          today_logs.append(meal_data)
          save_daily_log(today_str, today_logs)

          st.success("✅ 記錄成功！")
          st.json(meal_data)

        except Exception as e:
          st.error(f"解析失敗，請重試。錯誤訊息: {e}")
    else:
      st.warning("請先拍照或輸入餐點文字描述！")

# --- 分頁 3：歷史日誌 ---
with tab3:
  st.subheader("📅 歷史飲食日誌查詢")

  # 尋找所有歷史紀錄檔
  log_files = [
      f.replace(".json", "")
      for f in os.listdir(LOG_DIR)
      if f.endswith(".json")
  ]
  log_files.sort(reverse=True)

  if not log_files:
    st.info("目前尚無任何歷史記錄檔案。")
  else:
    selected_date = st.selectbox("選擇要查看的日期", log_files)
    selected_logs = load_daily_log(selected_date)
    day_total = sum([item.get("calories", 0) for item in selected_logs])

    st.markdown(f"### 📊 {selected_date} 總攝取熱量: **{day_total} kcal**")

    for item in selected_logs:
      with st.expander(
          f"🍽️ {item.get('name', '餐點')} - {item.get('calories', 0)} kcal"
      ):
        st.write(
            f"蛋白質: {item.get('protein', 0)}g | 碳水: {item.get('carbs', 0)}g"
            f" | 脂肪: {item.get('fat', 0)}g"
        )
        st.write(f"建議: {item.get('advice', '無')}")

# --- 分頁 4：趨勢分析 (Plotly 圖表) ---
with tab4:
  st.subheader("📈 長期營養與熱量趨勢分析")

  log_files = [
      f.replace(".json", "")
      for f in os.listdir(LOG_DIR)
      if f.endswith(".json")
  ]
  log_files.sort()

  if not log_files:
    st.info("累積幾天餐點記錄後，這裡將會自動生成視覺化趨勢圖表！")
  else:
    chart_data = []
    for d in log_files:
      logs = load_daily_log(d)
      cal_sum = sum([item.get("calories", 0) for item in logs])
      chart_data.append({"日期": d, "攝取熱量": cal_sum, "目標熱量": target_calories})

    df = pd.DataFrame(chart_data)

    # 繪製熱量趨勢折線圖
    fig = px.line(
        df,
        x="日期",
        y=["攝取熱量", "目標熱量"],
        markers=True,
        title="每日熱量攝取 vs 目標對比圖",
        labels={"value": "熱量 (kcal)", "variable": "指標"},
    )
    st.plotly_chart(fig, use_container_width=True)
