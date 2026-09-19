# 🧾 SwiftBill AI - Kodnexus AI Build Battle Submission

An AI-powered invoice automation tool that converts unstructured customer requirements into professional, verified invoices in seconds.

## 🚀 Core Features (Mapping to Challenge Criteria)
1. **Structured AI Extraction:** Built with Gemini 2.0 Flash and Pydantic for flawless JSON extraction.
2. **Anti-Hallucination Pricing Logic:** Extracted items are cross-referenced against a secure internal catalog. Unrecognized items are flagged for human review.
3. **Approval Dashboard:** Built in Streamlit for reviewing items and calculating taxes.
4. **Creative Bonuses:** Instant PDF generation (ReportLab) and 1-click WhatsApp share links.

## 💻 How to Run Locally
1. `pip install -r requirements.txt`
2. Add your Gemini API key inside the app sidebar.
3. `streamlit run app.py`