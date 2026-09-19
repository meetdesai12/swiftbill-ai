import streamlit as st
import pandas as pd
import urllib.parse
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from google import genai
from google.genai import types
from pydantic import BaseModel

st.set_page_config(page_title="SwiftBill AI", layout="wide", page_icon="🧾")

# --- 1. Define the Structured Output Schema for Gemini ---
class LineItem(BaseModel):
    service_name: str
    quantity: int
    item_notes: str

class InvoiceData(BaseModel):
    customer_name: str
    customer_email: str
    notes: str
    items: list[LineItem]

# --- 2. Price Catalog (Simulating a Database) ---
@st.cache_data
def load_catalog():
    data = {
        "service_name": [
            "Full-Stack Web Development",
            "Cloud Server Deployment",
            "UI/UX Design Audit",
            "Database Optimization",
            "SEO Consultation",
            "API Integration"
        ],
        "unit_price": [85.0, 350.0, 120.0, 200.0, 95.0, 150.0],
    }
    return pd.DataFrame(data)

catalog_df = load_catalog()

# --- 3. PDF Generator Function ---
def generate_pdf(customer_name, customer_email, notes, line_items, subtotal, tax, total):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1E3A8A'))
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 15))

    meta_text = f"<b>Billed To:</b> {customer_name}<br/><b>Email:</b> {customer_email}<br/><b>Notes:</b> {notes}"
    elements.append(Paragraph(meta_text, styles['Normal']))
    elements.append(Spacer(1, 15))

    table_data = [["Service Description", "Qty", "Unit Price", "Subtotal"]]
    for item in line_items:
        table_data.append([item["service_name"], str(item["quantity"]), f"${item['unit_price']:.2f}", f"${item['total']:.2f}"])
    
    table_data.append(["", "", "Subtotal:", f"${subtotal:.2f}"])
    table_data.append(["", "", "Tax:", f"${tax:.2f}"])
    table_data.append(["", "", "Total Due:", f"${total:.2f}"])

    t = Table(table_data, colWidths=[240, 60, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -4), 0.5, colors.HexColor('#E2E8F0')),
        ('LINEABOVE', (2, -3), (-1, -1), 1, colors.HexColor('#0F172A')),
        ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- 4. Streamlit UI Layout ---
st.title("🧾 SwiftBill AI - Invoice Automation")
st.caption("Kodnexus AI Build Battle Submission")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password")
    tax_rate = st.slider("Tax Rate (%)", min_value=0, max_value=25, value=10) / 100.0
    st.markdown("---")
    st.subheader("📋 Active Price Catalog")
    st.dataframe(catalog_df, hide_index=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Customer Requirement Input")
    raw_input = st.text_area(
        "Enter raw customer request / email:",
        height=180,
        value="Hey team, please bill Acme Corp (contact@acme.com) for 10 hours of Full-Stack Web Development, 1 Cloud Server Deployment, and 1 Custom AI Bot (need estimate). Payment within 14 days."
    )
    process_btn = st.button("Extract & Validate via AI", type="primary")

# --- 5. AI Processing Logic ---
if process_btn:
    # Fallback to the secure Streamlit secret if the sidebar is empty
    if not api_key:
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass

    if not api_key:
        st.error("Please supply your Gemini API key in the sidebar or Streamlit Secrets.")
    else:
        # Use the variable here, NEVER a hardcoded string
        client = genai.Client(api_key=api_key)
        
        system_instruction = """
        Extract billing entities from the text. 
        DO NOT invent prices. Just extract customer details and requested services with quantities.
        """
        
        with st.spinner("Analyzing message with Gemini..."):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash", # <-- Update this line
                    contents=raw_input,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=InvoiceData,
                    )
                )
                
                if response.parsed:
                    parsed_data = response.parsed
                    if isinstance(parsed_data, BaseModel):
                        st.session_state["extracted_data"] = parsed_data.model_dump()
                    elif isinstance(parsed_data, dict):
                        st.session_state["extracted_data"] = parsed_data
                    else:
                        st.error("Model returned an unexpected response format.")
                else:
                    st.error("Model did not return valid JSON.")
                
            except Exception as e:
                st.error(f"Error communicating with Gemini: {e}")
# --- 6. Review & Export Dashboard ---
if "extracted_data" in st.session_state:
    data = st.session_state["extracted_data"]
    
    with col2:
        st.subheader("2. Review & Approval")
        cust_name = st.text_input("Customer Name", value=data.get("customer_name", ""))
        cust_email = st.text_input("Customer Email", value=data.get("customer_email", ""))
        notes = st.text_area("Invoice Notes", value=data.get("notes", ""))

        st.markdown("#### Validated Line Items")
        processed_items = []
        subtotal = 0.0
        missing_flag = False

        for item in data.get("items", []):
            name = item.get("service_name", "")
            qty = float(item.get("quantity", 1))

            # Database Price Lookup
            match = catalog_df[catalog_df["service_name"].str.lower() == name.lower()]
            if not match.empty:
                price = float(match.iloc[0]["unit_price"])
                status = "✅ Verified"
            else:
                price = 0.0
                status = "⚠️ Missing in Catalog"
                missing_flag = True

            line_total = price * qty
            subtotal += line_total
            processed_items.append({"service_name": name, "quantity": qty, "unit_price": price, "total": line_total})

            c1, c2, c3, c4 = st.columns([3, 1, 1, 2])
            c1.text(f"{name}")
            c2.text(f"Qty: {qty}")
            c3.text(f"${price:.2f}")
            c4.caption(status)

        if missing_flag:
            st.warning("⚠️ One or more extracted services are not in the database catalog. Prices set to $0.00 to prevent AI hallucination.")

        tax_amount = subtotal * tax_rate
        grand_total = subtotal + tax_amount

        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Subtotal", f"${subtotal:.2f}")
        m2.metric("Tax", f"${tax_amount:.2f}")
        m3.metric("Total Due", f"${grand_total:.2f}")

        # PDF Export
        pdf_bytes = generate_pdf(cust_name, cust_email, notes, processed_items, subtotal, tax_amount, grand_total)

        st.download_button(
            label="📥 Download Approved PDF Invoice",
            data=pdf_bytes,
            file_name=f"Invoice_{(cust_name or 'Customer').replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary"
        )

        # WhatsApp Share
        wa_text = f"Hello {cust_name}, your invoice for ${grand_total:.2f} is ready."
        wa_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"
        st.link_button("📲 Share via WhatsApp", wa_url)