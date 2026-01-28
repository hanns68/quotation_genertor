import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
from datetime import datetime

# --- PDF 產生函數 (輸入改為字典清單) ---
def generate_pdf_buffer(info, items, tax_included, font_size_settings):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 字體設定：適應不同的作業系統環境
    font_name = 'Helvetica' 
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", # Streamlit Cloud (Linux)
        "C:\\Windows\\Fonts\\msjh.ttc",                # Windows
        "/System/Library/Fonts/PingFang.ttc"           # macOS
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('CustomFont', path))
                font_name = 'CustomFont'
                break
            except:
                continue

    # 繪製內容
    c.setFont(font_name, font_size_settings['title'])
    c.drawCentredString(width/2, height - 50, info['title'])
    
    c.setFont(font_name, font_size_settings['body'])
    y = height - 100
    for text in [f"報價公司：{info['company']}", f"統編：{info['tax_id']}", f"電話：{info['phone']}", f"日期：{info['date']}"]:
        c.drawString(50, y, text)
        y -= 20
    
    # 表格
    y -= 20
    c.line(50, y+15, 540, y+15)
    c.drawString(55, y, "項目")
    c.drawRightString(535, y, "金額")
    y -= 10
    c.line(50, y, 540, y)
    
    total_amount = 0
    for item in items:
        y -= 20
        c.drawString(55, y, item['name'])
        c.drawRightString(535, y, f"{item['amount']:,.0f}")
        total_amount += item['amount']

    y -= 40
    c.drawString(50, y, f"總計: NT$ {total_amount:,.0f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI ---
st.set_page_config(page_title="報價單產生器", layout="wide")
st.title("📋 報價單產生器")

# 1. 初始化 session_state (使用字典清單)
if 'items' not in st.session_state:
    st.session_state.items = []

# 2. 側邊欄設定
with st.sidebar:
    st.header("基本資訊")
    title = st.text_input("報價單名稱", "報價單")
    company = st.text_input("公司名稱", "")
    tax_id = st.text_input("統一編號", "")
    phone = st.text_input("電話", "")
    date = st.date_input("日期", datetime.now()).strftime("%Y-%m-%d")
    tax_included = st.checkbox("已含稅", value=True)

# 3. 輸入區域
st.subheader("新增項目")
col1, col2, col3 = st.columns([3, 1, 1])
with col1: name = st.text_input("項目名稱")
with col2: price = st.number_input("單價", min_value=0)
with col3: qty = st.number_input("數量", min_value=1)

if st.button("➕ 加入清單"):
    if name:
        # 關鍵：直接存成 Dictionary
        st.session_state.items.append({
            "name": name,
            "unit_price": price,
            "quantity": qty,
            "amount": price * qty
        })
        st.rerun()

# 4. 顯示清單與下載
if st.session_state.items:
    # 這裡的 i 現在是 Dictionary，所以用 i["name"] 存取，絕對不會出錯
    display_list = [
        {"項目": i["name"], "單價": i["unit_price"], "數量": i["quantity"], "小計": i["amount"]} 
        for i in st.session_state.items
    ]
    st.table(display_list)
    
    if st.button("🗑️ 清空清單"):
        st.session_state.items = []
        st.rerun()

    pdf_data = generate_pdf_buffer(
        {"title": title, "company": company, "tax_id": tax_id, "phone": phone, "date": date},
        st.session_state.items,
        tax_included,
        {"title": 18, "body": 12}
    )
    
    st.download_button("📥 下載 PDF", data=pdf_data, file_name="quote.pdf", mime="application/pdf")
