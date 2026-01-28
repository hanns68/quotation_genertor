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

# --- 字體下載與註冊函數 ---
def register_chinese_font():
    """確保中文字體存在並註冊"""
    font_name = "CustomFont"
    # 定義字體存放路徑
    font_path = "msjh.ttc" 
    
    # 如果本地不存在該字體，從 GitHub 或是 CDN 下載一個開源中文字體 (如：微軟正黑體替代品)
    if not os.path.exists(font_path):
        # 這裡提供一個穩定下載 Noto Sans TC (思源黑體) 的鏈接
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTC/NotoSansCJKtc-Regular.ttc"
        try:
            with st.spinner("首次執行，正在加載中文字體..."):
                r = requests.get(url, allow_redirects=True)
                with open(font_path, 'wb') as f:
                    f.write(r.content)
        except Exception as e:
            st.error(f"字體下載失敗: {e}")
            return "Helvetica" # 失敗則回傳預設

    try:
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        return font_name
    except:
        return "Helvetica"

# --- PDF 產生核心函數 ---
def generate_pdf_buffer(info, item_list, tax_included):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 註冊並獲取字體名稱
    font_name = register_chinese_font()
    
    # 繪製標題
    c.setFont(font_name, 18)
    c.drawCentredString(width/2, height - 50, info['title'])
    
    # 基本資訊
    c.setFont(font_name, 11)
    y = height - 100
    # 將標籤也改回中文，測試顯示
    details = [
        f"報價公司：{info['company']}",
        f"統一編號：{info['tax_id']}",
        f"聯絡電話：{info['phone']}",
        f"電子信箱：{info['email']}",
        f"報價日期：{info['date']}"
    ]
    for detail in details:
        c.drawString(50, y, detail)
        y -= 20
    
    # 繪製表格表頭
    y -= 20
    c.line(50, y+15, 540, y+15)
    c.drawString(55, y, "品項")
    c.drawCentredString(255, y, "單價")
    c.drawCentredString(360, y, "數量")
    c.drawRightString(535, y, "小計")
    y -= 10
    c.line(50, y, 540, y)
    
    # 填充品項
    subtotal = 0
    c.setFont(font_name, 10)
    for item in item_list:
        y -= 20
        c.drawString(55, y, str(item['name']))
        c.drawCentredString(255, y, f"{item['unit_price']:,.0f}")
        c.drawCentredString(360, y, f"{item['quantity']}")
        c.drawRightString(535, y, f"{item['amount']:,.0f}")
        subtotal += item['amount']
    
    # 金額總計
    tax = round(subtotal * 0.05 / 1.05) if tax_included else round(subtotal * 0.05)
    total = subtotal if tax_included else subtotal + tax
    
    y -= 40
    c.line(50, y+15, 540, y+15)
    c.setFont(font_name, 12)
    tax_text = "含稅" if tax_included else "未稅"
    c.drawString(50, y, f"總計金額 ({tax_text}): NT$ {total:,.0f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit 主程式 ---
st.set_page_config(page_title="專業報價單產生器", layout="wide", page_icon="📄")
st.title("📄 專業報價單產生器")

if 'quote_items' not in st.session_state:
    st.session_state.quote_items = []

with st.sidebar:
    st.header("🏢 單位資訊設定")
    title = st.text_input("報價單標題", "報價單")
    company = st.text_input("報價公司/人員", "您的公司名稱")
    tax_id = st.text_input("統一編號", "")
    phone = st.text_input("聯絡電話", "")
    email = st.text_input("電子信箱", "")
    quote_date = st.date_input("報價日期", datetime.now())
    date_str = quote_date.strftime("%Y-%m-%d")
    tax_type = st.radio("金額類型", ["未稅金額", "含稅金額"])

st.subheader("📦 新增報價項目")
col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

with col1:
    item_name = st.text_input("項目名稱", placeholder="請輸入品項")
with col2:
    item_price = st.number_input("單價", min_value=0, step=1)
with col3:
    item_qty = st.number_input("數量", min_value=1, value=1, step=1)
with col4:
    st.write("##")
    if st.button("➕ 新增項目"):
        if item_name and item_name.strip():
            st.session_state.quote_items.append({
                "name": item_name.strip(),
                "unit_price": int(item_price),
                "quantity": int(item_qty),
                "amount": int(item_price * item_qty)
            })
            st.rerun()

if st.session_state.quote_items:
    st.write("---")
    table_data = [{"項目": i["name"], "單價": i["unit_price"], "數量": i["quantity"], "金額": i["amount"]} for i in st.session_state.quote_items]
    df_display = pd.DataFrame(table_data)
    df_display["單價"] = df_display["單價"].apply(lambda x: f"NT$ {x:,}")
    df_display["金額"] = df_display["金額"].apply(lambda x: f"NT$ {x:,}")
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    subtotal = sum(item['amount'] for item in st.session_state.quote_items)
    tax = round(subtotal * 0.05 / 1.05) if tax_type == "含稅金額" else round(subtotal * 0.05)
    total = subtotal if tax_type == "含稅金額" else subtotal + tax
    st.metric("總金額（含稅）", f"NT$ {total:,}")
    
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("🗑️ 清空清單"):
            st.session_state.quote_items = []
            st.rerun()
    with col_btn2:
        info_payload = {"title": title, "company": company, "tax_id": tax_id, "phone": phone, "email": email, "date": date_str}
        pdf_buffer = generate_pdf_buffer(info_payload, st.session_state.quote_items, tax_type == "含稅金額")
        st.download_button("✅ 下載 PDF 報價單", data=pdf_buffer, file_name=f"Quotation_{date_str}.pdf", mime="application/pdf")
