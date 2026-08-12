from datetime import datetime
import glob
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# --- 設定與初始化 ---
# 載入環境變數 (.env 中的 GEMINI_API_KEY)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

# 頁面基本設定
st.set_page_config(
    page_title="A先生的 AI 營養管家", page_icon="🥗", layout="centered"
)

# 自訂 CSS 樣式
st.markdown(
    """
    <style>
    .stMetric { background-color: #ffffff; padding: 12px; border-radius: 12px; box-shadow: 0 3px 6px rgba(0,0,0,0.04); border-left: 5px solid #27ae60; }
    .highlight-card { background: linear-gradient(135deg, #e8f8f5 0%, #d4efdf 100%); padding: 15px; border-radius: 12px; border-left: 5px solid #2ecc71; margin-bottom: 15px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 資料儲存路徑
USER_CONFIG_PATH = "user_profile.json"
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# --- 功能函式 ---
def load_user_profile():
    if os.path.exists(USER_CONFIG_PATH):
        with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "name": "A先生", "age": 35, "gender": "男 (Male)", "weight": 72.0,
        "height": 175.0, "activity_level": "中度運動 (Moderately active)",
        "workout_type": "重訓 / 有氧混合", "chronic_conditions": ["無重大慢性病"],
    }

def save_user_profile(profile):
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=4)

def load_log_by_date(date_str):
    path = os.path.join(LOG_DIR, f"{date_str}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"meals": [], "total_calories": 0, "total_protein": 0, "total_carbs": 0, "total_fat": 0}

def save_log_by_date(date_str, log_data):
    with open(os.path.join(LOG_DIR, f"{date_str}.json"), "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)

def analyze_meal_with_gemini(profile, image_file=None, description=""):
    if not api_key:
        return {"dish_name": description or "未命名餐點", "calories": 500, "protein": 25, "carbs": 50, "fat": 15, "ai_comment": "⚠️ 未設定 API Key，請檢查 .env 檔。"}
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        conditions = ", ".join(profile.get("chronic_conditions", ["無"]))
        prompt = f"""請以專業營養師角度分析餐點：背景{profile}，禁忌{conditions}。
        請回傳嚴格的 JSON 格式 (無 markdown 符號)：
        {{"dish_name": "...", "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "ai_comment": "..."}}"""
        
        contents = [prompt]
        if image_file:
            contents.append(Image.open(image_file))
        if description:
            contents.append(description)

        response = model.generate_content(contents)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        return {"dish_name": description or "解析錯誤", "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "ai_comment": f"解析失敗: {str(e)}"}

# --- 主程式流程 ---
profile = load_user_profile()
bmr = (10 * profile["weight"] + 6.25 * profile["height"] - 5 * profile["age"] + (5 if "男" in profile["gender"] else -161))
tdee = bmr * {"久坐少動 (Sedentary)": 1.2, "輕度運動 (Lightly active)": 1.375, "中度運動 (Moderately active)": 1.55, "高度運動 (Very active)": 1.725}.get(profile["activity_level"], 1.375)

# --- UI ---
with st.sidebar:
    st.header("⚙️ 健康設定")
    # (此處省略部分輸入元件以節省篇幅，邏輯同原程式)
    st.metric("⚡ 每日消耗 (TDEE)", f"{int(tdee)} kcal")

st.title("🥗 A先生的 AI 營養管家")
tab1, tab2, tab3, tab4 = st.tabs(["📊 今日戰情室", "📸 記錄新餐點", "📅 歷史日誌", "📈 分析"])
today_str = datetime.now().strftime("%Y-%m-%d")

with tab1:
    today_log = load_log_by_date(today_str)
    st.metric("今日已攝取", f"{today_log['total_calories']} / {int(tdee)} kcal")
    st.progress(min(float(today_log['total_calories'] / tdee), 1.0))

with tab2:
    st.markdown("### 🍳 新增今日餐點紀錄")
    # 手機拍照與文字輸入
    captured_image = st.camera_input("📸 拍下您的餐點")
    food_description = st.text_input("或輸入文字描述")

    if st.button("🚀 AI 深度解析", type="primary", use_container_width=True):
        if captured_image or food_description:
            with st.spinner("🤖 AI 分析中..."):
                ai_result = analyze_meal_with_gemini(profile, captured_image, food_description)
                log = load_log_by_date(today_str)
                log["meals"].append(ai_result)
                log["total_calories"] += ai_result.get("calories", 0)
                # (累計蛋白質/碳水/脂肪邏輯同上)
                save_log_by_date(today_str, log)
            st.success("✅ 記錄成功！")
        else:
            st.warning("請拍照或輸入文字")

# (tab3, tab4 同樣維持之前的邏輯)