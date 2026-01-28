import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
from datetime import datetime
import pandas as pd

# --- PDF 產生核心函數 (輸入完全使用字典清單) ---
def generate_pdf_buffer(info, items, tax_included):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 字體設定 (支援 Linux/Streamlit Cloud 環境)
    font_name = 'Helvetica' 
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", # Streamlit Cloud 必備
        "C:\\Windows\\Fonts\\msjh.ttc",                # Windows
        "/System/Library/Fonts/PingFang.ttc"           # macOS
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('CustomFont', path))
                font_name = 'CustomFont'
                break
            except: continue

    # 繪製標題
    c.setFont(font_name, 18)
    c.drawCentredString(width/2, height - 50, info['title'])
    
    # 基本資訊
    c.setFont(font_name, 12)
    y = height - 100
    details = [
        f"報價公司/人員：{info['company']}",
        f"統一編號：{info['tax_id']}",
        f"聯絡電話：{info['phone']}",
        f"E-Mail：{info['email']}",
        f"報價日期：{info['date']}"
    ]
    for detail in details:
        c.drawString(50, y, detail)
        y -= 20
    
    # 繪製表格表頭
    y -= 20
    c.line(50, y+15, 540, y+15)
    c.drawString(55, y, "項目名稱")
    c.drawCentredString(255, y, "單價")
    c.drawCentredString(360, y, "數量")
    c.drawRightString(535, y, "小計")
    y -= 10
    c.line(50, y, 540, y)
    
    # 填充品項 (從字典讀取資料)
    subtotal = 0
    for item in items:
        y -= 20
        c.drawString(55, y, item['name'])
        c.drawCentredString(255, y, f"{item['unit_price']:,.0f}")
        c.drawCentredString(360, y, f"{item['quantity']}")
        c.drawRightString(535, y, f"{item['amount']:,.0f}")
        subtotal += item['amount']

    # 金額總計計算邏輯
    tax = round(subtotal * 0.05 / 1.05) if tax_included else round(subtotal * 0.05)
    total = subtotal if tax_included else subtotal + tax
    
    y -= 40
    c.line(50, y+15, 540, y+15)
    c.setFont(font_name, 14)
    c.drawString(50, y, f"總計金額 (含稅): NT$ {total:,.0f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI 介面 ---
st.set_page_config(page_title="專業報價單產生器", layout="wide")
st.title("📄 專業報價單產生器")

# 1. 初始化資料存儲 (使用內建字典，避開 Class 序列化報錯)
if 'items' not in st.session_state:
    st.session_state.items = []

# 2. 側邊欄：設定
with st.sidebar:
    st.header("🏢 單位資訊設定")
    title = st.text_input("報價單標題", "報價單")
    company = st.text_input("報價公司/人員", "您的公司名稱")
    tax_id = st.text_input("統一編號", "")
    phone = st.text_input("聯絡電話", "")
    email = st.text_input("電子信箱", "")
    date = st.date_input("報價日期", datetime.now()).strftime("%Y-%m-%d")
    tax_type = st.radio("金額類型", ["未稅金額", "含稅金額"])

# 3. 主畫面：新增項目
st.subheader("📦 新增報價項目")
col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
with col1: item_n = st.text_input("項目名稱", placeholder="請輸入品項")
with col2: item_p = st.number_input("單價", min_value=0, step=1)
with col3: item_q = st.number_input("數量", min_value=1, step=1)
with col4:
    st.write("##") # 對齊按鈕
    if st.button("➕ 新增項目"):
        if item_n:
            # 關鍵：直接存入字典 (Dictionary)，保證 session_state 穩定性
            st.session_state.items.append({
                "name": item_n,
                "unit_price": item_p,
                "quantity": item_q,
                "amount": item_p * item_q
            })
            st.rerun()
        else:
            st.error("請輸入名稱")

# 4. 顯示與下載
if st.session_state.items:
    st.write("---")
    st.subheader("📋 報價項目明細")
    
    # 修正：使用 pandas DataFrame 來顯示表格
    table_data = []
    for i in st.session_state.items:
        table_data.append({
            "項目": i["name"],
            "單價": f"NT$ {i['unit_price']:,.0f}",
            "數量": i["quantity"],
            "金額": f"NT$ {i['amount']:,.0f}"
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    c_btn1, c_btn2 = st.columns([1, 4])
    with c_btn1:
        if st.button("🗑️ 清空清單"):
            st.session_state.items = []
            st.rerun()
    with c_btn2:
        # 下載 PDF 按鈕
        info_payload = {
            "title": title, 
            "company": company, 
            "tax_id": tax_id, 
            "phone": phone, 
            "email": email, 
            "date": date
        }
        pdf_file = generate_pdf_buffer(info_payload, st.session_state.items, tax_type == "含稅金額")
        
        st.download_button(
            label="✅ 下載 PDF 報價單",
            data=pdf_file,
            file_name=f"Quotation_{date}.pdf",
            mime="application/pdf"
        )
else:
    st.info("目前清單中尚無項目，請由上方新增項目。")
