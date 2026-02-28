import re
from datetime import datetime
from typing import Optional


class DataCleaner:
    """Data resilience layer handling all known data quality issues.

    Handles:
    1. Duplicate header rows in Deals board
    2. Mixed date types in Close Date (A)
    3. Typo "BIlled" in Work Orders Billing Status
    4. Inconsistent quantity formats ("5360 HA")
    5. Deal Stage without prefix ("Project Completed")
    6. Massive null rates with caveat generation
    7. Sector name normalization
    """

    def __init__(self):
        self.cleaning_log: list[str] = []

    def clean_deals(self, records: list[dict]) -> tuple[list[dict], list[str]]:
        """Clean deals data. Returns (cleaned_records, caveats)."""
        self.cleaning_log = []
        cleaned = []
        header_rows_removed = 0

        for record in records:
            # 1. Filter duplicate header rows
            if self._is_header_row(record):
                header_rows_removed += 1
                continue

            # 2. Normalize deal values (string → float)
            deal_value = record.get("Masked Deal value")
            if deal_value:
                record["Masked Deal value"] = self._parse_number(deal_value)

            # 3. Parse dates safely for all date fields
            for date_field in ["Close Date (A)", "Tentative Close Date", "Created Date"]:
                val = record.get(date_field)
                if val and isinstance(val, str):
                    record[date_field] = self._parse_date(val)

            # 4. Normalize sector names (trim whitespace, consistent casing)
            sector = record.get("Sector/service")
            if sector and isinstance(sector, str):
                record["Sector/service"] = sector.strip()

            # 5. Normalize Deal Stage
            stage = record.get("Deal Stage")
            if stage and isinstance(stage, str):
                record["Deal Stage"] = stage.strip()

            # 6. Normalize Deal Status
            status = record.get("Deal Status")
            if status and isinstance(status, str):
                record["Deal Status"] = status.strip()

            # 7. Normalize Owner code
            owner = record.get("Owner code")
            if owner and isinstance(owner, str):
                record["Owner code"] = owner.strip()

            cleaned.append(record)

        if header_rows_removed > 0:
            self.cleaning_log.append(
                f"Removed {header_rows_removed} duplicate header row(s) from data"
            )

        caveats = self._generate_deals_caveats(cleaned)
        return cleaned, caveats

    def clean_workorders(self, records: list[dict]) -> tuple[list[dict], list[str]]:
        """Clean work orders data. Returns (cleaned_records, caveats)."""
        self.cleaning_log = []
        cleaned = []
        typo_fixes = 0

        for record in records:
            # 1. Fix "BIlled" typo
            billing_status = record.get("Billing Status")
            if billing_status and billing_status == "BIlled":
                record["Billing Status"] = "Billed"
                typo_fixes += 1

            # 2. Clean quantity formats ("5360 HA" → 5360)
            for qty_field in [
                "Quantities as per PO",
                "Quantity by Ops",
                "Balance in quantity",
            ]:
                val = record.get(qty_field)
                if val and isinstance(val, str):
                    record[qty_field] = self._parse_quantity(val)

            # 3. Parse financial values
            financial_fields = [
                "Amount in Rupees (Excl of GST) (Masked)",
                "Amount in Rupees (Incl of GST) (Masked)",
                "Billed Value in Rupees (Excl of GST.) (Masked)",
                "Billed Value in Rupees (Incl of GST.) (Masked)",
                "Collected Amount in Rupees (Incl of GST.) (Masked)",
                "Amount to be billed in Rupees (Excl of GST.) (Masked)",
                "Amount to be billed in Rupees (Incl of GST.) (Masked)",
                "Amount Receivable (Masked)",
            ]
            for field in financial_fields:
                val = record.get(field)
                if val:
                    record[field] = self._parse_number(val)

            # 4. Normalize execution status
            exec_status = record.get("Execution Status")
            if exec_status and isinstance(exec_status, str):
                record["Execution Status"] = exec_status.strip()

            # 5. Normalize sector
            sector = record.get("Sector")
            if sector and isinstance(sector, str):
                record["Sector"] = sector.strip()

            cleaned.append(record)

        if typo_fixes > 0:
            self.cleaning_log.append(
                f"Fixed {typo_fixes} typo(s): 'BIlled' → 'Billed'"
            )

        caveats = self._generate_wo_caveats(cleaned)
        return cleaned, caveats

    def _is_header_row(self, record: dict) -> bool:
        """Detect rows where values equal column names (duplicate headers)."""
        suspicious_matches = 0
        checks = [
            ("Deal Status", "Deal Status"),
            ("Deal Stage", "Deal Stage"),
            ("Sector/service", "Sector/service"),
            ("Owner code", "Owner code"),
        ]
        for field, expected_header in checks:
            val = record.get(field)
            if val and str(val).strip() == expected_header:
                suspicious_matches += 1
        return suspicious_matches >= 2

    def _parse_number(self, value) -> Optional[float]:
        """Parse a value to float, handling commas and non-numeric text."""
        if value is None:
            return None
        try:
            cleaned = str(value).replace(",", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _parse_date(self, value: str) -> Optional[str]:
        """Parse date string to ISO format, handling mixed formats."""
        if not value or not isinstance(value, str):
            return None

        # Skip values that are clearly not dates
        if any(c.isalpha() for c in value) and not value.startswith("20"):
            return None

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def _parse_quantity(self, value: str) -> Optional[float]:
        """Extract numeric part from quantity strings like '5360 HA'."""
        if not value:
            return None
        numeric = re.sub(r"[^\d.]", "", str(value))
        try:
            return float(numeric) if numeric else None
        except ValueError:
            return None

    def _generate_deals_caveats(self, records: list[dict]) -> list[str]:
        """Auto-generate data quality warnings for deals data."""
        if not records:
            return ["No deal records returned from the query."]

        total = len(records)
        caveats = []

        # Check null deal values
        null_values = sum(
            1 for r in records if r.get("Masked Deal value") is None
        )
        if null_values > 0:
            pct = round(null_values / total * 100, 1)
            valued = total - null_values
            caveats.append(
                f"{null_values}/{total} deals ({pct}%) have no deal value. "
                f"Monetary totals are based on {valued} valued deals only."
            )

        # Check null close dates
        null_close = sum(
            1 for r in records if not r.get("Close Date (A)")
        )
        if null_close > total * 0.5:
            pct = round(null_close / total * 100, 1)
            caveats.append(
                f"{null_close}/{total} deals ({pct}%) have no actual close date."
            )

        # Check null probability
        null_prob = sum(
            1 for r in records if not r.get("Closure Probability")
        )
        if null_prob > total * 0.5:
            pct = round(null_prob / total * 100, 1)
            caveats.append(
                f"{null_prob}/{total} deals ({pct}%) have no closure probability assigned."
            )

        # Check null tentative close dates
        null_tentative = sum(
            1 for r in records if not r.get("Tentative Close Date")
        )
        if null_tentative > total * 0.1:
            pct = round(null_tentative / total * 100, 1)
            caveats.append(
                f"{null_tentative}/{total} deals ({pct}%) have no tentative close date."
            )

        return caveats

    def _generate_wo_caveats(self, records: list[dict]) -> list[str]:
        """Auto-generate data quality warnings for work orders data."""
        if not records:
            return ["No work order records returned from the query."]

        total = len(records)
        caveats = []

        # Check null collected amounts
        null_collected = sum(
            1
            for r in records
            if r.get("Collected Amount in Rupees (Incl of GST.) (Masked)") is None
        )
        if null_collected > 0:
            pct = round(null_collected / total * 100, 1)
            caveats.append(
                f"{null_collected}/{total} work orders ({pct}%) have no collection data recorded."
            )

        # Check null billed values
        null_billed = sum(
            1
            for r in records
            if r.get("Billed Value in Rupees (Excl of GST.) (Masked)") is None
        )
        if null_billed > 0:
            pct = round(null_billed / total * 100, 1)
            caveats.append(
                f"{null_billed}/{total} work orders ({pct}%) have no billed value recorded."
            )

        # Check null billing status
        null_billing = sum(
            1 for r in records if not r.get("Billing Status")
        )
        if null_billing > total * 0.5:
            pct = round(null_billing / total * 100, 1)
            caveats.append(
                f"{null_billing}/{total} work orders ({pct}%) have no billing status."
            )

        return caveats

    def get_cleaning_log(self) -> list[str]:
        """Return the log of all cleaning operations performed."""
        return self.cleaning_log.copy()


# Singleton instance
data_cleaner = DataCleaner()
