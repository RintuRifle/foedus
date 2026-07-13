import markdown
from weasyprint import HTML

md_content = """
# NexaSolar Energy Solutions
**Corporate Brochure 2026**

## About Us
NexaSolar Energy Solutions is a leading renewable energy contractor based in Patna, Bihar, specializing in the supply, installation, and maintenance of commercial and industrial solar power plants. With over 8 years of experience, we have successfully deployed over 50MW of solar capacity across India.

## Key Information
- **Company Name:** NexaSolar Energy Solutions Pvt. Ltd.
- **Year of Incorporation:** 2018
- **Annual Turnover:** ₹45.5 Crores (FY 2024-2025)
- **GSTIN:** 10AAZCN1234E1Z9
- **PAN:** AAZCN1234E
- **Headquarters:** Frazer Road, Patna, Bihar
- **Sectors:** Renewable Energy, Solar Power, Electrical Infrastructure

## Certifications
- ISO 9001:2015 (Quality Management System)
- ISO 14001:2015 (Environmental Management System)
- MNRE Approved Channel Partner

## Past Projects (Experience)
- **Project Alpha:** 500kW Rooftop Solar Installation at Bihar State Secretariat (Value: ₹2.5 Cr)
- **Project Beta:** 1MW Ground Mounted Solar Plant for IOCL Refinery, Barauni (Value: ₹4.8 Cr)
- **Project Gamma:** 50kW Off-grid Solar Systems across 20 Rural Healthcare Centers in Bihar (Value: ₹1.2 Cr)
- **Total Completed Projects:** 45+

## Equipment & Capabilities
- We manufacture our own Tier-1 equivalent solar mounting structures.
- In-house fleet of electrical testing equipment.
- Authorized distributors for Vikram Solar and Waaree Energies.
"""

html_content = f"<html><body>{markdown.markdown(md_content)}</body></html>"
HTML(string=html_content).write_pdf("sample_brochure_nexasolar.pdf")
print("PDF generated: sample_brochure_nexasolar.pdf")
