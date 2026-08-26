from datetime import datetime
import os
from google import genai
import pandas as pd
import psycopg2
import streamlit as st
from PIL import Image

# ==========================================
# 1. 頁面與 UI 樣式設定
# ==========================================
st.set_page_config(page_title="AI 智慧營養管家", page_icon="🥗", layout="centered")

st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 28px !important; }
    .stApp { background-color: #f5f7f9; }
    div[data-testid="stVerticalBlock"] { 
        background-color: white; 
        border-radius: 20px; 
        padding: 25px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
    }
    .stTabs [data-baseweb="tab"] p { font-size: 32px !important; font-weight: bold !important; }
    h1 { font-size: 48px !important; }
    h2 { font-size: 38px !important; }
    h3 { font-size: 32px !important; }
    .stButton>button { 
        width: 100%; border-radius: 25px; background-color: #2ecc71; 
        color: white; font-weight: bold; font-size: 28px !important; padding: 18px; 
    }
    input, select, textarea, div[data-baseweb="select"] span { font-size: 28px !important; }
    div[data-baseweb="popover"] div { font-size: 28px !important; }
    .streamlit-expanderHeader p { font-size: 28px !important; font-weight: bold !important; }
    [data-testid="stSidebar"] { background-color: #eef2f5; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 系統統一載入 API 與資料庫初始化
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 系統尚未設定 GEMINI_API_KEY，請在 Secrets 中設定。")
    st.stop()

client = genai.Client(api_key=api_key)

def get_db_connection():
    database_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        st.error("❌ 找不到 DATABASE_URL 連線資訊！")
        st.stop()
    return psycopg2.connect(database_url)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            height REAL, weight REAL, age INTEGER, activity TEXT, medical TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            date TEXT, meal_type TEXT, content TEXT, weight REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_summaries (
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            date TEXT, summary TEXT, PRIMARY KEY (user_id, date)
        )
    """)
    
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username) VALUES (%s) RETURNING id", ("預設使用者",))
        default_id = c.fetchone()[0]
        c.execute(
            "INSERT INTO user_profile (user_id, height, weight, age, activity, medical) VALUES (%s, 175.0, 70.0, 30, '中度運動', '無')",
            (default_id,)
        )
    conn.commit()
    c.close()
    conn.close()

init_db()

# ==========================================
# 3. 資料庫獨立查詢與操作
# ==========================================
def get_all_users():
    conn = get_db_connection()
    df = pd.read_sql("SELECT id, username FROM users ORDER BY id ASC", conn)
    conn.close()
    return df

def create_user(username):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username) VALUES (%s) RETURNING id", (username,))
        new_id = c.fetchone()[0]
        c.execute(
            "INSERT INTO user_profile (user_id, height, weight, age, activity, medical) VALUES (%s, 170.0, 65.0, 30, '中度運動', '無')",
            (new_id,)
        )
        conn.commit()
        return new_id
    except psycopg2.IntegrityError:
        conn.rollback()
        st.sidebar.error("❌ 使用者名稱已存在！")
        return None
    finally:
        c.close()
        conn.close()

def get_user_profile(user_id):
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM user_profile WHERE user_id=%s", conn, params=(user_id,))
    conn.close()
    if df.empty:
        return {"height": 170.0, "weight": 65.0, "age": 30, "activity": "中度運動", "medical": "無"}
    return df.iloc[0].to_dict()

def update_user_profile(user_id, data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """UPDATE user_profile 
           SET height=%s, weight=%s, age=%s, activity=%s, medical=%s 
           WHERE user_id=%s""",
        (data["height"], data["weight"], data["age"], data["activity"], data["medical"], user_id)
    )
    conn.commit()
    c.close()
    conn.close()

# ==========================================
# 4. 側邊欄：身份切換 (不需輸入 API Key)
# ==========================================
st.sidebar.title("👤 使用者帳號")

users_df = get_all_users()
user_list = users_df["username"].tolist()

selected_username = st.sidebar.selectbox("選擇您的帳號", user_list)
current_user_id = int(users_df[users_df["username"] == selected_username]["id"].values[0])

st.sidebar.markdown("---")
st.sidebar.subheader("➕ 新增親友帳號")
new_user_input = st.sidebar.text_input("新使用者姓名")
if st.sidebar.button("建立帳號"):
    if new_user_input.strip():
        new_id = create_user(new_user_input.strip())
        if new_id:
            st.sidebar.success(f"✅ 已建立：{new_user_input}")
            st.rerun()

# ==========================================
# 5. 主介面
# ==========================================
st.title(f"🥗 AI 智慧營養管家 ({selected_username})")
tab1, tab2, tab3, tab4 = st.tabs(["📸 記錄", "📖 日誌", "🤖 當日總結", "⚙️ 設定"])

# ------------------------------------------
# TAB 1: 拍照與記錄
# ------------------------------------------
with tab1:
    st.subheader("📸 餐點分析")
    meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心"])
    uploaded_file = st.file_uploader("上傳餐點照片", type=["jpg", "jpeg", "png"])
    user_note = st.text_input("💡 補充說明 (例如：吃了一半、加了一匙糖)")

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="已上傳餐點", use_container_width=True)

        if st.button("✨ AI 深度評估"):
            with st.spinner("AI 正在結合您的個人資料進行分析..."):
                try:
                    p = get_user_profile(current_user_id)
                    prompt = f"""
                    你是一位專業營養師。請根據以下用戶個人資料分析照片中的餐點：
                    - 用戶身型：{p['age']}歲, {p['height']}cm, {p['weight']}kg
                    - 運動狀態：{p['activity']}
                    - 健康備註/過敏源：{p['medical']}
                    - 用戶補充說明：{user_note}
                    
                    請評估：
                    1. 這份餐點大致包含哪些食物與營養成分？
                    2. 這份餐點是否適合該用戶目前的身體狀態與運動習慣？
                    3. 有無營養過剩、不足或需要注意的健康風險？
                    """
                    response = client.models.generate_content(
                        model="gemini-3.6-flash", contents=[prompt, image]
                    )
                    st.session_state.last_analysis = response.text
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"❌ 分析失敗：{e}")

    if "last_analysis" in st.session_state and st.button("➕ 加入我的日誌"):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO food_logs (user_id, date, meal_type, content, weight) VALUES (%s, %s, %s, %s, %s)",
            (
                current_user_id,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                meal_type,
                st.session_state.last_analysis,
                get_user_profile(current_user_id)["weight"],
            ),
        )
        conn.commit()
        c.close()
        conn.close()
        st.success("✅ 已存入您的個人日誌！")
        del st.session_state.last_analysis

# ------------------------------------------
# TAB 2: 個人飲食日誌
# ------------------------------------------
with tab2:
    st.subheader(f"📖 {selected_username} 的飲食日誌")
    conn = get_db_connection()
    df = pd.read_sql(
        "SELECT * FROM food_logs WHERE user_id = %s ORDER BY date DESC",
        conn,
        params=(current_user_id,)
    )
    conn.close()
    
    if df.empty:
        st.info("目前尚無您的飲食紀錄。")
    else:
        for _, row in df.iterrows():
            with st.expander(f"⏰ {row['date']} - 【{row['meal_type']}】"):
                st.write(row["content"])

# ------------------------------------------
# TAB 3: 個人當日總結
# ------------------------------------------
with tab3:
    st.subheader("⊙ 飲食總結報告")

    selected_date = st.date_input("選擇查詢日期", value=datetime.now().date())
    target_date_str = selected_date.strftime("%Y-%m-%d")

    df_sum = pd.DataFrame()
    try:
        conn = get_db_connection()
        df_sum = pd.read_sql(
            "SELECT summary FROM daily_summaries WHERE user_id = %s AND date = %s",
            conn,
            params=(current_user_id, target_date_str),
        )
        conn.close()
    except Exception:
        df_sum = pd.DataFrame()

    if not df_sum.empty:
        st.success(f"📌 {target_date_str} 營養總結報告：")
        st.markdown(df_sum.iloc[0]["summary"])
    else:
        st.info(f"📅 尚無 {target_date_str} 的保存總結。")

        conn = get_db_connection()
        df_today = pd.read_sql(
            "SELECT meal_type, content FROM food_logs WHERE user_id = %s AND date LIKE %s",
            conn,
            params=(current_user_id, f"{target_date_str}%"),
        )
        conn.close()

        if not df_today.empty:
            if st.button(f"📊 產出並永久保存 {target_date_str} 總結報告"):
                with st.spinner(f"AI 正在綜整 {target_date_str} 的飲食紀錄..."):
                    try:
                        p = get_user_profile(current_user_id)
                        today_logs = [
                            f"【{row['meal_type']}】\n{row['content']}"
                            for _, row in df_today.iterrows()
                        ]
                        prompt = f"""
                        請扮演專業營養師，根據用戶資料 {p} 與以下【{target_date_str}】的所有飲食紀錄：
                        {today_logs}
                        
                        請給予：
                        1. 當日總熱量與三大營養素（蛋白質、脂肪、碳水化合物）的粗估加總。
                        2. 當日飲食的整體優缺點（是否有營養過剩或不足）。
                        3. 針對接下來的飲食調整建議。
                        """
                        response = client.models.generate_content(
                            model="gemini-3.6-flash", contents=prompt
                        )
                        summary_text = response.text

                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute(
                            """INSERT INTO daily_summaries (user_id, date, summary) 
                               VALUES (%s, %s, %s)
                               ON CONFLICT (user_id, date) DO UPDATE SET summary = EXCLUDED.summary""",
                            (current_user_id, target_date_str, summary_text),
                        )
                        conn.commit()
                        c.close()
                        conn.close()

                        st.success(f"✅ {target_date_str} 總結報告已成功儲存！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 產生失敗：{e}")

    st.markdown("---")
    st.markdown("### 📚 歷史總結目錄總覽")
    try:
        conn = get_db_connection()
        df_all_sums = pd.read_sql(
            "SELECT date, summary FROM daily_summaries WHERE user_id = %s ORDER BY date DESC",
            conn,
            params=(current_user_id,)
        )
        conn.close()

        if df_all_sums.empty:
            st.info("目前尚無任何歷史總結紀錄。")
        else:
            for _, row in df_all_sums.iterrows():
                with st.expander(f"📂 營養總結報告：{row['date']} (點擊展開)"):
                    st.markdown(row["summary"])
    except Exception:
        st.info("目前尚無歷史總結目錄資料。")

# ------------------------------------------
# TAB 4: 個人設定
# ------------------------------------------
with tab4:
    st.subheader(f"⚙️ {selected_username} 的個人檔案設定")
    p = get_user_profile(current_user_id)

    with st.form("profile_form"):
        h_val = st.number_input("身高 (cm)", value=float(p["height"]))
        w_val = st.number_input("體重 (kg)", value=float(p["weight"]))
        a_val = st.number_input("年齡", value=int(p["age"]))

        activities = ["久坐不動", "輕度運動", "中度運動", "高度運動"]
        act_idx = activities.index(p["activity"]) if p["activity"] in activities else 2
        act_val = st.selectbox("運動狀態", activities, index=act_idx)

        med_val = st.text_area("健康備註/過敏源", value=str(p["medical"]))

        submitted = st.form_submit_button("💾 儲存個人資料")
        if submitted:
            new_p = {
                "height": h_val,
                "weight": w_val,
                "age": a_val,
                "activity": act_val,
                "medical": med_val,
            }
            update_user_profile(current_user_id, new_p)
            st.success("✅ 個人資料已更新！")