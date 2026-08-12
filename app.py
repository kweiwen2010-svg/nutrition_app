import streamlit as st
import json
import os
from datetime import datetime

# --- 輔助函式 ---
def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def load_daily_log(date_str):
    filename = f"nutrition_app_data/daily_log.json"
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

# --- 頁面配置 ---
st.set_page_config(page_title="AI 營養管家", layout="centered")
st.title("🥗 A先生的 AI 營養管家")

# 模擬資料，您之後可替換為真實設定
target_calories = 2182
tdee = 2182

# --- 分頁介面 ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 今日戰情室", "📸 記錄新餐點", "📅 歷史日誌", "📈 趨勢分析"])

# --- 處理今日資料 ---
today_str = get_today_str()
today_logs = load_daily_log(today_str)

# 使用防呆機制計算今日熱量
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
    
    # 這裡加上了防呆機制，確保只有字典格式才會被顯示
    if not today_logs:
        st.info("今天尚未記錄任何餐點。")
    else:
        for item in today_logs:
            if isinstance(item, dict):
                name = item.get('name', '未知餐點')
                cals = item.get('calories', 0)
                st.write(f"🍽️ {name} - {cals} kcal")

# (其他 tab2, tab3, tab4 的內容請保持您原本的程式碼即可)