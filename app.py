import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
from datetime import datetime
import pandas as pd

# --- PDF 產生核心函數 ---
def generate_pdf_buffer(info, item_list, tax_included):
    """生成 PDF 報價單"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 字體設定
    font_name = 'Helvetica'
    
    try:
        font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('CustomFont', font_path))
            font_name = 'CustomFont'
    except:
        pass
    
    # 繪製標題
    c.setFont(font_name, 18)
    c.drawCentredString(width/2, height - 50, info['title'])
    
    # 基本資訊
    c.setFont(font_name, 12)
    y = height - 100
    details = [
        f"Company: {info['company']}",
        f"Tax ID: {info['tax_id']}",
        f"Phone: {info['phone']}",
        f"E-Mail: {info['email']}",
        f"Date: {info['date']}"
    ]
    for detail in details:
        c.drawString(50, y, detail)
        y -= 20
    
    # 繪製表格表頭
    y -= 20
    c.line(50, y+15, 540, y+15)
    c.drawString(55, y, "Item")
    c.drawCentredString(255, y, "Unit Price")
    c.drawCentredString(360, y, "Qty")
    c.drawRightString(535, y, "Amount")
    y -= 10
    c.line(50, y, 540, y)
    
    # 填充品項
    subtotal = 0
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
    c.setFont(font_name, 14)
    c.drawString(50, y, f"Total (Tax Included): NT$ {total:,.0f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit 主程式 ---
st.set_page_config(page_title="專業報價單產生器", layout="wide", page_icon="📄")
st.title("📄 專業報價單產生器")

# 初始化 session state - 改用 quote_items 避免命名衝突
if 'quote_items' not in st.session_state:
    st.session_state.quote_items = []

# 側邊欄設定
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

# 新增項目區域
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
        else:
            st.error("請輸入名稱")

# 顯示項目清單
if st.session_state.quote_items:
    st.write("---")
    st.subheader("📋 報價項目明細")
    
    # 建立表格資料
    table_data = []
    for idx, item in enumerate(st.session_state.quote_items):
        row = {
            "編號": idx + 1,
            "項目": item["name"],
            "單價": item["unit_price"],
            "數量": item["quantity"],
            "金額": item["amount"]
        }
        table_data.append(row)
    
    # 轉換為 DataFrame
    df = pd.DataFrame(table_data)
    
    # 格式化顯示
    df_display = df.copy()
    df_display["單價"] = df_display["單價"].apply(lambda x: f"NT$ {x:,}")
    df_display["金額"] = df_display["金額"].apply(lambda x: f"NT$ {x:,}")
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # 計算總額
    subtotal = sum(item['amount'] for item in st.session_state.quote_items)
    tax = round(subtotal * 0.05 / 1.05) if tax_type == "含稅金額" else round(subtotal * 0.05)
    total = subtotal if tax_type == "含稅金額" else subtotal + tax
    
    st.metric("總金額（含稅）", f"NT$ {total:,}")
    
    # 按鈕區
    col_btn1, col_btn2 = st.columns([1, 4])
    
    with col_btn1:
        if st.button("🗑️ 清空清單"):
            st.session_state.quote_items = []
            st.rerun()
    
    with col_btn2:
        try:
            info_payload = {
                "title": title,
                "company": company,
                "tax_id": tax_id,
                "phone": phone,
                "email": email,
                "date": date_str
            }
            pdf_buffer = generate_pdf_buffer(
                info_payload,
                st.session_state.quote_items,
                tax_type == "含稅金額"
            )
            
            st.download_button(
                label="✅ 下載 PDF 報價單",
                data=pdf_buffer,
                file_name=f"Quotation_{date_str}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF 生成失敗：{str(e)}")
else:
    st.info("目前清單中尚無項目，請由上方新增項目。")
