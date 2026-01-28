import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from datetime import datetime
import io
import os

# --- 核心邏輯層 ---
class QuoteItem:
    def __init__(self, name="", unit_price=0, quantity=0):
        self.name = name
        self.unit_price = unit_price
        self.quantity = quantity
    
    def get_amount(self):
        return self.unit_price * self.quantity

# --- PDF 產生邏輯 ---
def generate_pdf_buffer(info, items, tax_included, font_size_settings):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 字體處理 (在 Streamlit Cloud 建議載入自備的 .ttf 檔案)
    # 這裡先用系統預設，若部署後中文亂碼，請參考下方部署說明
    font_name = 'Helvetica' 
    try:
        # 嘗試尋找 Linux 常用中文字體路徑 (Streamlit Cloud 是 Linux)
        font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
            font_name = 'ChineseFont'
    except:
        pass

    # 標題
    c.setFont(font_name, font_size_settings['title'])
    c.drawCentredString(width/2, height - 50, info['title'])
    
    # 基本資訊
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
    
    # 表格繪製與金額計算邏輯 (簡化版)
    y -= 20
    c.line(50, y, 540, y)
    y -= 20
    c.drawString(55, y, "項目")
    c.drawCentredString(255, y, "單價")
    c.drawCentredString(360, y, "數量")
    c.drawRightString(535, y, "金額")
    y -= 10
    c.line(50, y, 540, y)
    
    subtotal = 0
    for item in items:
        y -= 20
        c.drawString(55, y, item.name)
        c.drawCentredString(255, y, f"{item.unit_price:,.0f}")
        c.drawCentredString(360, y, f"{item.quantity}")
        c.drawRightString(535, y, f"{item.get_amount():,.0f}")
        subtotal += item.get_amount()

    # 計算稅務
    tax = round(subtotal * 0.05 / 1.05) if tax_included else round(subtotal * 0.05)
    total = subtotal if tax_included else subtotal + tax

    y -= 40
    c.line(50, y+10, 540, y+10)
    c.drawString(50, y, f"總計 (含稅): NT$ {total:,.0f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI 層 ---
st.set_page_config(page_title="報價單產生器", layout="wide")
st.title("📄 專業報價單產生器")

with st.sidebar:
    st.header("基本資訊")
    title = st.text_input("報價單名稱", "新北市原住民族教育資源中心 - 報價單")
    company = st.text_input("報價公司/人員", "只想創意有限公司")
    tax_id = st.text_input("統一編號", "50992265")
    phone = st.text_input("聯絡電話", "02-26011575")
    email = st.text_input("電子信箱", "hagnotk@gmail.com")
    date = st.date_input("報價日期", datetime.now()).strftime("%Y-%m-%d")
    tax_type = st.radio("金額類型", ["未稅金額", "含稅金額"])
    
    st.header("字型設定")
    t_size = st.slider("標題大小", 12, 30, 18)
    b_size = st.slider("內文大小", 8, 20, 12)

# 品項管理
if 'items' not in st.session_state:
    st.session_state.items = []

col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
with col1: item_n = st.text_input("品項名稱")
with col2: item_p = st.number_input("單價", min_value=0)
with col3: item_q = st.number_input("數量", min_value=1)
with col4: 
    st.write("##")
    if st.button("新增"):
        st.session_state.items.append(QuoteItem(item_n, item_p, item_q))

# 顯示列表
if st.session_state.items:
    st.table([{"品項": i.name, "單價": i.unit_price, "數量": i.quantity, "小計": i.get_amount()} for i in st.session_state.items])
    if st.button("清空列表"):
        st.session_state.items = []
        st.rerun()

    # 下載按鈕
    info_dict = {"title": title, "company": company, "tax_id": tax_id, "phone": phone, "email": email, "date": date}
    font_dict = {"title": t_size, "body": b_size}
    
    pdf_fp = generate_pdf_buffer(info_dict, st.session_state.items, tax_type == "含稅金額", font_dict)
    
    st.download_button(
        label="Download PDF 報價單",
        data=pdf_fp,
        file_name=f"quote_{date}.pdf",
        mime="application/pdf"
    )