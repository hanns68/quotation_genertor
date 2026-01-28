import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
from datetime import datetime

# --- PDF 產生函數 (輸入完全使用字典) ---
def generate_pdf_buffer(info, items, tax_included, font_size_settings):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 支援 Streamlit Cloud 的中文字體偵測
    font_name = 'Helvetica' 
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", # Linux (Streamlit Cloud)
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

    # 繪製內容
    c.setFont(font_name, font_size_settings['title'])
    c.drawCentredString(width/2, height - 50, info['title'])
    
    c.setFont(font_name, font_size_settings['body'])
    y = height - 100
    for text in [f"報價單位：{info['company']}", f"統一編號：{info['tax_id']}", f"聯絡電話：{info['phone']}", f"報價日期：{info['date']}"]:
        c.drawString(50, y, text)
        y -= 20
    
    # 表格表頭
    y -= 20
    c.line(50, y+15, 540, y+15)
    c.drawString(55, y, "項目名稱")
    c.drawCentredString(255, y, "單價")
    c.drawCentredString(360, y, "數量")
    c.drawRightString(535, y, "小計")
    y -= 10
    c.line(50, y, 540, y)
    
    # 填充品項 (從字典清單讀取)
    subtotal = 0
    for item in items:
        y -= 20
        c.drawString(55, y, item['name'])
        c.drawCentredString(255, y, f"{item['unit_price']:,.0f}")
        c.drawCentredString(360, y, f"{item['quantity']}")
        c.drawRightString(535, y, f"{item['amount']:,.0f}")
        subtotal += item['amount']

    # 稅額計算
    tax = round(subtotal * 0.05 / 1.05) if tax_included else round(subtotal * 0.05)
    total = subtotal if tax_included else subtotal + tax
    
    y -= 40
    c.line(50, y+15, 540, y+15)
    c.drawString(50, y, f"總計金額 (含稅): NT$ {total:,.0f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI 介面 ---
st.set_page_config(page_title="報價單產生器", layout="wide")
st.title("📄 專業報價單產生器")

# 1. 初始化資料 (保證穩定性)
if 'items' not in st.session_state:
    st.session_state.items = []

# 2. 側邊欄設定
with st.sidebar:
    st.header("🏢 單位資訊")
    title = st.text_input("報價單標題", "報價單")
    company = st.text_input("報價公司/人員", "只想創意有限公司")
    tax_id = st.text_input("統一編號", "50992265")
    phone = st.text_input("聯絡電話", "02-26011575")
    email = st.text_input("電子信箱", "hagnotk@gmail.com")
    date = st.date_input("報價日期", datetime.now()).strftime("%Y-%m-%d")
    tax_type = st.radio("金額類型", ["未稅金額", "含稅金額"])

# 3. 品項輸入區
st.subheader("📦 新增項目")
col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
with col1: item_n = st.text_input("品項名稱")
with col2: item_p = st.number_input("單價", min_value=0, step=1)
with col3: item_q = st.number_input("數量", min_value=1, step=1)
with col4:
    st.write("##")
    if st.button("➕ 新增"):
        if item_n:
            # 這裡直接存成 Dictionary，不使用 QuoteItem 類別
            st.session_state.items.append({
                "name": item_n,
                "unit_price": item_p,
                "quantity": item_q,
                "amount": item_p * item_q
            })
            st.rerun()

# 4. 顯示與下載
if st.session_state.items:
    st.write("---")
    st.subheader("📋 項目明細")
    # 顯示表格 (直接讀取字典)
    st.table([
        {"項目": i["name"], "單價": f"{i['unit_price']:,.0f}", "數量": i["quantity"], "金額": f"{i['amount']:,.0f}"} 
        for i in st.session_state.items
    ])
    
    c_btn1, c_btn2 = st.columns([1, 4])
    with c_btn1:
        if st.button("🗑️ 清空清單"):
            st.session_state.items = []
            st.rerun()
    with c_btn2:
        # 準備 PDF 資料
        info_payload = {"title": title, "company": company, "tax_id": tax_id, "phone": phone, "email": email, "date": date}
        pdf_file = generate_pdf_buffer(info_payload, st.session_state.items, tax_type == "含稅金額", {"title": 18, "body": 12})
        
        st.download_button("📥 下載 PDF 報價單", data=pdf_file, file_name=f"Quotation_{date}.pdf", mime="application/pdf")
else:
    st.info("請在上方輸入資料並點擊『新增』來開始建立報價單。")
