import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import requests
from datetime import datetime
import pandas as pd

# --- 自動下載並註冊中文字體 ---
def register_font():
    """下載並註冊中文字體 (Noto Sans TC)"""
    font_name = "NotoSansTC"
    font_filename = "NotoSansTC-Regular.ttf"
    
    # 如果字體不存在，則從 Google Fonts GitHub 下載 (思源黑體)
    if not os.path.exists(font_filename):
        # 這是思源黑體的穩定下載連結
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/Variable/TTF/NotoSansCJKtc-VF.ttf"
        try:
            with st.spinner("首次產生 PDF，正在載入中文字體，請稍候..."):
                r = requests.get(url, allow_redirects=True)
                with open(font_filename, 'wb') as f:
                    f.write(r.content)
        except Exception as e:
            st.error(f"字體下載失敗，將使用預設字體：{e}")
            return "Helvetica"

    try:
        pdfmetrics.registerFont(TTFont(font_name, font_filename))
        return font_name
    except:
        return "Helvetica"

# --- PDF 產生函數 (已加入表格線條優化) ---
def generate_pdf_buffer(info, item_list, tax_included):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 註冊字體
    font_name = register_font()
    
    # 1. 繪製標題
    c.setFont(font_name, 18)
    c.drawCentredString(width/2, height - 50, info['title'])
    
    # 2. 基本資訊 (中文標籤)
    c.setFont(font_name, 11)
    y = height - 100
    details = [
        f"報價單位：{info['company']}",
        f"統一編號：{info['tax_id']}",
        f"聯絡電話：{info['phone']}",
        f"電子信箱：{info['email']}",
        f"報價日期：{info['date']}"
    ]
    for detail in details:
        c.drawString(50, y, detail)
        y -= 20
    
    # 3. 繪製表格表頭與線條
    y -= 20
    c.setLineWidth(1)
    c.line(50, y+15, 540, y+15) # 表頭頂線
    c.drawString(55, y, "報價項目名稱")
    c.drawCentredString(255, y, "單價")
    c.drawCentredString(360, y, "數量")
    c.drawRightString(535, y, "小計")
    y -= 10
    c.line(50, y, 540, y) # 表頭底線
    
    # 4. 填充品項 (支援中文名稱)
    subtotal = 0
    c.setFont(font_name, 10)
    for item in item_list:
        y -= 20
        # 如果 y 太低，應處理分頁，此處暫不擴充
        c.drawString(55, y, str(item['name']))
        c.drawCentredString(255, y, f"NT$ {item['unit_price']:,.0f}")
        c.drawCentredString(360, y, f"{item['quantity']}")
        c.drawRightString(535, y, f"NT$ {item['amount']:,.0f}")
        subtotal += item['amount']
        # 畫底線
        c.setDash(1, 2) # 虛線
        c.line(50, y-5, 540, y-5)
        c.setDash() # 恢復實線
    
    # 5. 金額總計計算
    tax = round(subtotal * 0.05 / 1.05) if tax_included else round(subtotal * 0.05)
    total = subtotal if tax_included else subtotal + tax
    
    y -= 40
    c.line(50, y+15, 540, y+15) # 總計頂線
    c.setFont(font_name, 12)
    tax_status = "含稅" if tax_included else "未稅"
    c.drawString(50, y, f"總計金額 ({tax_status}): NT$ {total:,.0f} 元整")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI ---
st.set_page_config(page_title="專業報價單產生器", layout="wide", page_icon="📄")
st.title("📄 專業報價單產生器")

# 初始化存儲 (使用 quote_items)
if 'quote_items' not in st.session_state:
    st.session_state.quote_items = []

# 側邊欄設定
with st.sidebar:
    st.header("🏢 基本資訊")
    title = st.text_input("報價單標題", "報價單")
    company = st.text_input("公司/人員", "您的公司名稱")
    tax_id = st.text_input("統一編號", "")
    phone = st.text_input("聯絡電話", "")
    email = st.text_input("電子信箱", "")
    quote_date = st.date_input("日期", datetime.now())
    tax_type = st.radio("金額類型", ["未稅金額", "含稅金額"])

# 新增項目
st.subheader("📦 新增項目")
c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
with c1: item_n = st.text_input("項目名稱")
with c2: item_p = st.number_input("單價", min_value=0, step=1)
with c3: item_q = st.number_input("數量", min_value=1, value=1, step=1)
with c4:
    st.write("##")
    if st.button("➕ 新增"):
        if item_n:
            # 存入字典，避開 Class 報錯問題 
            st.session_state.quote_items.append({
                "name": item_n,
                "unit_price": item_p,
                "quantity": item_q,
                "amount": item_p * item_q
            })
            st.rerun()

# 顯示清單
if st.session_state.quote_items:
    st.write("---")
    df = pd.DataFrame(st.session_state.quote_items)
    # 使用 width='stretch' 取代棄用的使用方式 
    st.dataframe(df.assign(
        單價=df["unit_price"].map("NT$ {:,.0f}".format),
        金額=df["amount"].map("NT$ {:,.0f}".format)
    )[["name", "單價", "quantity", "金額"]], width='stretch', hide_index=True)

    # 按鈕區
    b1, b2 = st.columns([1, 4])
    with b1:
        if st.button("🗑️ 清空"):
            st.session_state.quote_items = []
            st.rerun()
    with b2:
        payload = {
            "title": title, "company": company, "tax_id": tax_id, 
            "phone": phone, "email": email, "date": quote_date.strftime("%Y-%m-%d")
        }
        pdf = generate_pdf_buffer(payload, st.session_state.quote_items, tax_type == "含稅金額")
        st.download_button("✅ 下載 PDF 報價單", data=pdf, file_name=f"Quotation_{payload['date']}.pdf")
else:
    st.info("請新增項目以開始。")
