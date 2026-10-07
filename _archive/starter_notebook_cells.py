# EDGAR API — Starter Notebook Cells

# CELL 1 — REQUIRED CONFIGURATION
import edgar

edgar.configure(
    name="Your Name",
    email="your_email@uw.edu"
)

print("EDGAR configured:", edgar.is_configured())


# CELL 2 — TICKER TO CIK
ticker = "AAPL"

cik = edgar.ticker_to_cik(ticker)

print("Ticker:", ticker)
print("CIK:", cik)


# CELL 3 — RAW SUBMISSIONS RESPONSE
submissions = edgar.get_submissions(ticker)

print(type(submissions))
print(submissions.keys())


# CELL 4 — EXPLORE THE NESTED STRUCTURE
print(submissions["filings"].keys())

recent = submissions["filings"]["recent"]

print(type(recent))
print(recent.keys())


# CELL 5 — CONVERT RECENT FILINGS TO A DATAFRAME
import pandas as pd

filings = pd.DataFrame(recent)

filings.head()


# CELL 6 — WHAT TYPES OF FORMS DOES THIS COMPANY FILE?
filings["form"].value_counts()


# CELL 7 — USE THE CONVENIENCE FUNCTION AFTER UNDERSTANDING THE STRUCTURE
filings_fast = edgar.get_filings(ticker)

filings_fast.head()


# CELL 8 — COMPANY FACTS: RAW XBRL RESPONSE
facts = edgar.get_company_facts(ticker)

print(type(facts))
print(facts.keys())


# CELL 9 — EXPLORE THE TAXONOMY
print(facts["facts"].keys())

us_gaap = facts["facts"]["us-gaap"]

print(type(us_gaap))
print(list(us_gaap.keys())[:20])


# CELL 10 — NOW USE THE MODULE TO LIST CONCEPTS
concepts = edgar.list_facts(ticker)

concepts.head()
