import streamlit as st
import json
import os
from datetime import datetime

# --- 輔助函式 ---
def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def load_user_profile():
    filename = "nutrition_app_data/user_profile.json"
    if not os.path.exists(filename):
        return {"name": "使用者", "target_calories": 2182, "tdee": 2182}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {"name": "使用者", "target_calories": 2182, "tdee": 2182}
    except:
        return {"name": "使用者", "target_calories": 2182, "tdee": 2182}

def save_user_profile(profile_data):
    os.makedirs("nutrition_app_data", exist_ok=True)
    filename = "nutrition_app_data/user_profile.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=4)

def load_daily_log(date_str):
    filename = "nutrition_app_data/daily_log.json"
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

def save_daily_log(date_str, new_item):
    os.makedirs("nutrition_app_data", exist_ok=True)
    filename = "nutrition_app_data/daily_log.json"
    data = load_daily_log(date_str)
    data.append(new_item)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 頁面配置 ---
st.set_page_config(page_title="AI 營養管家", layout="centered")

# --- 側欄設定 ---
st.sidebar.title("⚙️ 個人設定")
current_profile = load_user_profile()

user_name = st.sidebar.text_input("您的名字", value=current_profile.get("name", "使用者"))
target_calories = st.sidebar.number_input("每日目標熱量 (kcal)", min_value=500, max_value=5000, value=current_profile.get("target_calories", 2182))
tdee = st.sidebar.number_input("TDEE (kcal)", min_value=500, max_value=5000, value=current_profile.get("tdee", 2182))

if st.sidebar.button("儲存設定"):
    new_profile = {"name": user_name, "target_calories": target_calories, "tdee": tdee}
    save_user_profile(new_profile)
    st.sidebar.success("設定已儲存！")

# --- 主畫面標題（直接使用側欄輸入的名字） ---
st.title(f"🥗 {user_name} 的 AI 營養管家")

# --- 分頁介面 ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 今日戰情室", "📸 記錄新餐點", "📅 歷史日誌", "📈 趨勢分析"])

today_str = get_today_str()
today_logs = load_daily_log(today_str)
total_eaten = sum([item.get("calories", 0) for item in today_logs if isinstance(item, dict)])

# --- 分頁 1: 今日戰情室 ---
with tab1:
    st.subheader("🔥 今日熱量戰情室")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="今日目標", value=f"{target_calories} kcal", delta=f"TDEE: {int(tdee)}")
    with col2:
        st.metric(label="已攝取", value=f"{total_eaten} kcal", delta=f"剩餘: {target_calories - total_eaten} kcal")
    
    st.write("---")
    st.subheader("📝 今日已記錄餐點")
    if not today_logs:
        st.info("今天尚未記錄任何餐點。")
    else:
        for item in today_logs:
            if isinstance(item, dict):
                name = item.get('name', '未知餐點')
                cals = item.get('calories', 0)
                st.write(f"🍽️ {name} - {cals} kcal")

# --- 分頁 2: 記錄新餐點 ---
with tab2:
    st.subheader("📸 拍攝或上傳餐點照片")
    uploaded_file = st.file_uploader("選擇餐點圖片", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="上傳的餐點", use_column_width=True)
        food_name = st.text_input("餐點名稱", value="健康餐點")
        food_cals = st.number_input("估算熱量 (kcal)", min_value=0, value=500)
        
        if st.button("確認記錄"):
            new_entry = {"name": food_name, "calories": food_cals, "time": datetime.now().strftime("%H:%M")}
            save_daily_log(today_str, new_entry)
            st.success("成功記錄新餐點！請切換回「今日戰情室」查看。")

# --- 分頁 3: 歷史日誌 ---
with tab3:
    st.subheader("📅 歷史日誌紀錄")
    filename = "nutrition_app_data/daily_log.json"
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                all_data = json.load(f)
                st.json(all_data)
            except:
                st.write("目前尚無有效的歷史紀錄格式。")
    else:
        st.info("尚無歷史紀錄檔案。")

# --- 分頁 4: 趨勢分析 ---
with tab4:
    st.subheader("📈 熱量攝取趨勢分析")
    st.info("這裡將會顯示您的長期熱量變化圖表。")