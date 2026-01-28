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
    font_name = "NotoSansTC"
    font_filename = "NotoSansTC-Regular.ttf"
    if not os.path.exists(font_filename):
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/Variable/TTF/NotoSansCJKtc-VF.ttf"
        try:
            with st.spinner("正在載入中文字體..."):
                r = requests.get(url, allow_redirects=True)
                with open(font_filename, 'wb') as f:
                    f.write(r.content)
        except Exception as e:
            return "Helvetica"
    try:
        pdfmetrics.registerFont(TTFont(font_name, font_filename))
        return font_name
    except:
        return "Helvetica"

# --- PDF 產生函數 (修正金額顯示邏輯) ---
def generate_pdf_buffer(info, item_list, tax_included):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font_name = register_font()
    
    # 1. 標題與基本資訊
    c.setFont(font_name, 18)
    c.drawCentredString(width/2, height - 50, info['title'])
    c.setFont(font_name, 11)
    y = height - 100
    details = [f"報價單位：{info['company']}", f"統一編號：{info['tax_id']}", 
               f"聯絡電話：{info['phone']}", f"電子信箱：{info['email']}", f"報價日期：{info['date']}"]
    for detail in details:
        c.drawString(50, y, detail)
        y -= 20
    
    # 2. 表格表頭
    y -= 20
    c.setLineWidth(1)
    c.line(50, y+15, 540, y+15)
    c.drawString(55, y, "報價項目名稱")
    c.drawCentredString(255, y, "單價")
    c.drawCentredString(360, y, "數量")
    c.drawRightString(535, y, "金額")
    y -= 10
    c.line(50, y, 540, y)
    
    # 3. 品項內容
    item_total_sum = 0 # 原始項目的加總
    c.setFont(font_name, 10)
    for item in item_list:
        y -= 20
        c.drawString(55, y, str(item['name']))
        c.drawCentredString(255, y, f"{item['unit_price']:,.0f}")
        c.drawCentredString(360, y, f"{item['quantity']}")
        c.drawRightString(535, y, f"{item['amount']:,.0f}")
        item_total_sum += item['amount']
        c.setDash(1, 2)
        c.line(50, y-5, 540, y-5)
        c.setDash()

    # 4. 金額計算與稅金明細 (參考上傳檔案之邏輯 )
    # 如果輸入是「含稅」，則從小計中反推稅額；如果是「未稅」，則外加稅額 
    if tax_included:
        total = item_total_sum
        tax = round(total * 0.05 / 1.05)
        subtotal = total - tax
    else:
        subtotal = item_total_sum
        tax = round(subtotal * 0.05)
        total = subtotal + tax

    # 5. 繪製金額明細欄位
    y -= 30
    c.line(50, y+15, 540, y+15) # 明細頂線
    c.setFont(font_name, 11)
    
    # 小計 (未稅)
    c.drawString(400, y, "銷售額(未稅)：")
    c.drawRightString(535, y, f"NT$ {subtotal:,.0f}")
    
    # 稅額
    y -= 20
    c.drawString(400, y, "營業稅(5%)：")
    c.drawRightString(535, y, f"NT$ {tax:,.0f}")
    
    # 總計
    y -= 25
    c.setFont(font_name, 13)
    c.setFillColorRGB(0.8, 0, 0) # 設定為紅色強調
    c.drawString(50, y, f"總計金額 ({'含稅' if tax_included else '加稅後'}):")
    c.drawRightString(535, y, f"NT$ {total:,.0f} 元整")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI (保持原有穩定運作方法) ---
st.set_page_config(page_title="報價單產生器", layout="wide", page_icon="📄")
st.title("📄 報價單產生器")

if 'quote_items' not in st.session_state:
    st.session_state.quote_items = []

with st.sidebar:
    st.header("🏢 基本資訊")
    title = st.text_input("報價單標題", "報價單")
    company = st.text_input("公司/人員名稱", "您的公司名稱")
    tax_id = st.text_input("統一編號", "")
    phone = st.text_input("聯絡電話", "")
    email = st.text_input("電子信箱", "")
    quote_date = st.date_input("日期", datetime.now())
    tax_type = st.radio("您輸入的項目單價是：", ["未稅金額", "含稅金額"])

st.subheader("📦 新增項目")
c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
with c1: item_n = st.text_input("項目名稱")
with c2: item_p = st.number_input("單價", min_value=0, step=1)
with c3: item_q = st.number_input("數量", min_value=1, value=1, step=1)
with c4:
    st.write("##")
    if st.button("➕ 新增"):
        if item_n:
            st.session_state.quote_items.append({
                "name": item_n, "unit_price": item_p,
                "quantity": item_q, "amount": item_p * item_q
            })
            st.rerun()

if st.session_state.quote_items:
    st.write("---")
    df = pd.DataFrame(st.session_state.quote_items)
    st.dataframe(df.assign(
        單價=df["unit_price"].map("NT$ {:,.0f}".format),
        金額=df["amount"].map("NT$ {:,.0f}".format)
    )[["name", "單價", "quantity", "金額"]], width='stretch', hide_index=True)

    b1, b2 = st.columns([1, 4])
    with b1:
        if st.button("🗑️ 清空"):
            st.session_state.quote_items = []
            st.rerun()
    with b2:
        payload = {"title": title, "company": company, "tax_id": tax_id, 
                   "phone": phone, "email": email, "date": quote_date.strftime("%Y-%m-%d")}
        pdf = generate_pdf_buffer(payload, st.session_state.quote_items, tax_type == "含稅金額")
        st.download_button("✅ 下載 PDF 報價單", data=pdf, file_name=f"Quotation_{payload['date']}.pdf")

