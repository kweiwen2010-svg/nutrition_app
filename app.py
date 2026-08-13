import streamlit as st
import json
import os
from datetime import datetime
import google.generativeai as genai

# --- 頁面配置 ---
st.set_page_config(page_title="AI 營養管家", layout="centered")

# --- 輔助函式：確保讀取的數值為 float ---
def load_user_profile():
    filename = "nutrition_app_data/user_profile.json"
    default_profile = {
        "name": "Vincent",
        "age": 30.0,
        "height": 175.0,
        "weight": 70.0,
        "activity": "中度運動 (每週3-5天)",
        "medical": "無",
        "tdee": 2182.0,
        "target_calories": 2182.0
    }
    if not os.path.exists(filename):
        return default_profile
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["age"] = float(data.get("age", 30.0))
            data["height"] = float(data.get("height", 175.0))
            data["weight"] = float(data.get("weight", 70.0))
            data["tdee"] = float(data.get("tdee", 2182.0))
            data["target_calories"] = float(data.get("target_calories", 2182.0))
            return data
    except:
        return default_profile

def save_user_profile(profile_data):
    os.makedirs("nutrition_app_data", exist_ok=True)
    filename = "nutrition_app_data/user_profile.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=4)

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

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

# --- 側欄：個人身體數據 ---
st.sidebar.title("⚙️ 個人身體數據")
profile = load_user_profile()

user_name = st.sidebar.text_input("您的名字", value=profile.get("name", "Vincent"))
age = st.sidebar.number_input("年齡", min_value=10.0, max_value=120.0, value=float(profile.get("age", 30.0)))
height = st.sidebar.number_input("身高 (cm)", min_value=100.0, max_value=250.0, value=float(profile.get("height", 175.0)))
weight = st.sidebar.number_input("體重 (kg)", min_value=30.0, max_value=200.0, value=float(profile.get("weight", 70.0)))

activity_options = ["久坐 (幾乎無運動)", "輕度運動 (每週1-3天)", "中度運動 (每週3-5天)", "高度運動 (每週6-7天)"]
current_activity = profile.get("activity", "中度運動 (每週3-5天)")
activity_idx = activity_options.index(current_activity) if current_activity in activity_options else 2
activity = st.sidebar.selectbox("活動狀態", activity_options, index=activity_idx)

medical = st.sidebar.text_area("特殊病史 / 飲食禁忌", value=profile.get("medical", "無"))

# 計算 BMR 與 TDEE
bmr = 10.0 * weight + 6.25 * height - 5.0 * age + 5.0
activity_multipliers = {
    "久坐 (幾乎無運動)": 1.2,
    "輕度運動 (每週1-3天)": 1.375,
    "中度運動 (每週3-5天)": 1.55,
    "高度運動 (每週6-7天)": 1.725
}
tdee = float(bmr * activity_multipliers.get(activity, 1.55))
target_calories = st.sidebar.number_input("每日目標熱量 (kcal)", min_value=500.0, max_value=5000.0, value=float(profile.get("target_calories", tdee)))

if st.sidebar.button("儲存並更新設定"):
    new_profile = {
        "name": user_name,
        "age": age,
        "height": height,
        "weight": weight,
        "activity": activity,
        "medical": medical,
        "tdee": tdee,
        "target_calories": target_calories
    }
    save_user_profile(new_profile)
    st.sidebar.success("設定已更新！")

# --- 主畫面標題 ---
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
        st.metric(label="今日目標", value=f"{int(target_calories)} kcal", delta=f"TDEE: {int(tdee)}")
    with col2:
        st.metric(label="已攝取", value=f"{int(total_eaten)} kcal", delta=f"剩餘: {int(target_calories - total_eaten)} kcal")
    
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

# --- 分頁 2: 記錄新餐點 (含 AI 辨識) ---
with tab2:
    st.subheader("📸 拍攝或上傳餐點照片")
    uploaded_file = st.file_uploader("選擇餐點圖片", type=["jpg", "jpeg", "png"])
    
    ai_food_name = "健康餐點"
    ai_food_cals = 500
    
    # 智慧抓取 API Key
api_key = None
try:
    # 直接強制讀取頂層的 GEMINI_API_KEY
    api_key = st.secrets.get("GEMINI_API_KEY")
except:
    pass

    if uploaded_file is not None:
        st.image(uploaded_file, caption="上傳的餐點")
        
        if api_key:
            genai.configure(api_key=api_key)
            if st.button("🤖 請 AI 分析餐點熱量"):
                with st.spinner("AI 正在辨識您的餐點內容與熱量..."):
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        bytes_data = uploaded_file.getvalue()
                        image_part = {"mime_type": uploaded_file.type, "data": bytes_data}
                        prompt = "請辨識這張圖片中的食物名稱，並估算它的總熱量（大卡）。請嚴格依照以下 JSON 格式回傳，不要有其他廢話：\n{\"name\": \"食物名稱\", \"calories\": 數字}"
                        
                        response = model.generate_content([image_part, prompt])
                        result_text = response.text.strip()
                        if result_text.startswith("```json"):
                            result_text = result_text[7:]
                        if result_text.endswith("```"):
                            result_text = result_text[:-3]
                        
                        parsed = json.loads(result_text.strip())
                        ai_food_name = parsed.get("name", "健康餐點")
                        ai_food_cals = int(parsed.get("calories", 500))
                        st.success(f"AI 分析完成！辨識為：{ai_food_name}，約 {ai_food_cals} 大卡")
                    except Exception as e:
                        st.warning(f"AI 分析時發生小狀況（{e}），請直接手動修改名稱與熱量。")
        else:
            st.info("提示：若要啟用 AI 自動辨識，請在 Streamlit Secrets 設定 GEMINI_API_KEY。")

    food_name = st.text_input("餐點名稱", value=ai_food_name)
    food_cals = st.number_input("估算熱量 (kcal)", min_value=0, value=ai_food_cals)
    
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
# --- 簡易 API 連線測試 ---
st.write("---")
st.subheader("🧪 API 快速連線測試")

test_key = st.secrets.get("GEMINI_API_KEY", "")

if st.button("點擊測試 API 是否正常"):
    if not test_key:
        st.error("❌ 失敗：抓不到 st.secrets 裡面的 GEMINI_API_KEY，值是空的！")
    else:
        try:
            genai.configure(api_key=test_key)
            test_model = genai.GenerativeModel('gemini-1.5-flash')
            test_response = test_model.generate_content("請回覆：OK")
            st.success(f"✅ 成功！API 回應正常：{test_response.text}")
        except Exception as e:
            st.error(f"❌ 錯誤：API 連線失敗，原因：{e}")