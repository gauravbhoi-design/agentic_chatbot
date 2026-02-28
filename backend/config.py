import os
from dotenv import load_dotenv

load_dotenv()

MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_API_URL = "https://api.monday.com/v2"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEALS_BOARD_ID = os.getenv("DEALS_BOARD_ID")
WORKORDERS_BOARD_ID = os.getenv("WORKORDERS_BOARD_ID")

# Board column mappings for reference
DEALS_COLUMNS = {
    "name": "Deal Name",
    "owner": "Owner code",
    "client": "Client Code",
    "status": "Deal Status",
    "close_date": "Close Date (A)",
    "probability": "Closure Probability",
    "value": "Masked Deal value",
    "tentative_close": "Tentative Close Date",
    "stage": "Deal Stage",
    "product": "Product deal",
    "sector": "Sector/service",
    "created": "Created Date",
}

WORKORDERS_COLUMNS = {
    "deal_name": "Deal name masked",
    "customer": "Customer Name Code",
    "serial": "Serial #",
    "nature": "Nature of Work",
    "execution_status": "Execution Status",
    "sector": "Sector",
    "type_of_work": "Type of Work",
    "document_type": "Document Type",
    "owner": "BD/KAM Personnel code",
    "amount_excl": "Amount in Rupees (Excl of GST) (Masked)",
    "amount_incl": "Amount in Rupees (Incl of GST) (Masked)",
    "billed_excl": "Billed Value in Rupees (Excl of GST.) (Masked)",
    "billed_incl": "Billed Value in Rupees (Incl of GST.) (Masked)",
    "collected": "Collected Amount in Rupees (Incl of GST.) (Masked)",
    "to_bill_excl": "Amount to be billed in Rupees (Excl of GST.) (Masked)",
    "to_bill_incl": "Amount to be billed in Rupees (Incl of GST.) (Masked)",
    "receivable": "Amount Receivable (Masked)",
    "wo_status": "WO Status (billed)",
    "billing_status": "Billing Status",
    "invoice_status": "Invoice Status",
}

# Valid filter values
DEAL_STATUSES = ["Won", "Dead", "Open", "On Hold"]
DEAL_STAGES = [
    "A. Lead Generated",
    "B. Sales Qualified Leads",
    "C. Demo Done",
    "D. Feasibility",
    "E. Proposal/Commercials Sent",
    "F. Negotiations",
    "G. Project Won",
    "H. Work Order Received",
    "I. POC",
    "J. Invoice sent",
    "K. Amount Accrued",
    "L. Project Lost",
    "M. Projects On Hold",
    "N. Not relevant at the moment",
    "O. Not Relevant at all",
    "Project Completed",
]
DEAL_SECTORS = [
    "Renewables", "Mining", "Railways", "Others", "Powerline",
    "Construction", "DSP", "Tender", "Manufacturing", "Aviation",
    "Security and Surveillance",
]
EXECUTION_STATUSES = [
    "Completed", "Ongoing", "Executed until current month",
    "Not Started", "Pause/struck", "Partial Completed", "Details pending",
]
NATURE_OF_WORK = [
    "One time Project", "POC", "Annual Rate Contract", "Monthly Contract",
]
OWNER_CODES = [
    "OWNER_001", "OWNER_002", "OWNER_003", "OWNER_004",
    "OWNER_005", "OWNER_006", "OWNER_007",
]
