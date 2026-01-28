import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
from datetime import datetime

# --- PDF 產生核心函數 ---
def generate_pdf_buffer(info, items, tax_included, font_size_settings):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 字體設定：在 Streamlit Cloud (Linux) 預設安裝文泉驛正黑體
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
            except:
                continue

    # 1. 繪製標題
    c.setFont(font_name, font_size_settings['title'])
    c.drawCentredString(width/2, height - 50, info['title'])
    
    # 2. 基本資訊
    c.setFont(font_name, font_size_settings['body'])
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
    
    # 3. 繪製表格表頭
    y -= 20
    c.line(50, y+15, 540, y+15)
    c.drawString(55, y, "項目")
    c.drawCentredString(255, y, "單價")
    c.drawCentredString(360, y, "數量")
    c.drawRightString(535, y, "金額")
    y -= 10
    c.line(50, y, 540, y)
    
    # 4. 填充品項 (從字典讀取)
    subtotal = 0
    for item in items:
        y -= 20
        if y < 50: # 簡單的分頁處理
            c.showPage()
            y = height - 50
            c.setFont(font_name, font_size_settings['body'])

        c.drawString(55, y, item['name'])
        c.drawCentredString(255, y, f"{item['unit_price']:,.0f}")
        c.drawCentredString(360, y, f"{item['quantity']}")
        c.drawRightString(535, y, f"{item['amount']:,.0f}")
        subtotal += item['amount']

    # 5. 計算稅額
    if tax_included:
        tax = round(subtotal * 0.05 / 1.05)
        total = subtotal
        tax_text = f"含稅總計: NT$ {total:,.0f} (內含稅額: {tax:,.0f})"
    else:
        tax = round(subtotal * 0.05)
        total = subtotal + tax
        tax_text = f"總計 (未稅: {subtotal:,.0f} + 稅: {tax:,.0f}) = NT$ {total:,.0f}"

    y -= 40
    c.line(50, y+15, 540, y+15)
    c.setFont(font_name, font_size_settings['body'] + 2)
    c.drawString(50, y, tax_text)
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI 介面 ---
st.set_page_config(page_title="報價單產生器", layout="wide")
st.title("📄 專業報價單產生器")

# 使用 Session State 初始化列表
if 'items' not in st.session_state:
    st.session_state.items = []

# 側邊欄：設定
with st.sidebar:
    st.header("🏢 基本資訊")
    title = st.text_input("報價單名稱", "報價單")
    company = st.text_input("報價公司/人員", "您的公司名稱")
    tax_id = st.text_input("統一編號", "")
    phone = st.text_input("聯絡電話", "")
    email = st.text_input("電子信箱", "")
    date = st.date_input("報價日期", datetime.now()).strftime("%Y-%m-%d")
    tax_type = st.radio("金額類型", ["未稅金額", "含稅金額"])
    
    st.header("🎨 樣式設定")
    t_size = st.slider("標題字體大小", 12, 30, 18)
    b_size = st.slider("內文字體大小", 8, 20, 12)

# 主畫面：新增品項
st.subheader("📦 新增報價項目")
c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
with c1: it_name = st.text_input("品項名稱", key="input_name")
with c2: it_price = st.number_input("單價", min_value=0, step=100, key="input_price")
with c3: it_qty = st.number_input("數量", min_value=1, step=1, key="input_qty")
with c4:
    st.write("##") # 對齊按鈕
    if st.button("➕ 新增品項"):
        if it_name:
            # 以字典格式存入，避免 TypeError
            st.session_state.items.append({
                "name": it_name,
                "unit_price": it_price,
                "quantity": it_qty,
                "amount": it_price * it_qty
            })
            st.rerun()
        else:
            st.warning("請輸入品項名稱")

# 顯示目前的品項表格
if st.session_state.items:
    st.write("---")
    st.subheader("📋 項目清單")
    
    # 轉換成可顯示的 DataFrame 格式
    display_data = [
        {"項目": i["name"], "單價": f"{i['unit_price']:,.0f}", "數量": i["quantity"], "金額": f"{i['amount']:,.0f}"} 
        for i in st.session_state.items
    ]
    st.table(display_data)

    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("🗑️ 清空所有項目"):
            st.session_state.items = []
            st.rerun()
    
    with col_btn2:
        # 下載按鈕
        info_data = {"title": title, "company": company, "tax_id": tax_id, "phone": phone, "email": email, "date": date}
        font_data = {"title": t_size, "body": b_size}
        
        pdf_file = generate_pdf_buffer(info_data, st.session_state.items, tax_type == "含稅金額", font_data)
        
        st.download_button(
            label="✅ 下載 PDF 報價單",
            data=pdf_file,
            file_name=f"Quotation_{date}.pdf",
            mime="application/pdf"
        )
else:
    st.info("目前清單中沒有品項，請從上方新增。")
