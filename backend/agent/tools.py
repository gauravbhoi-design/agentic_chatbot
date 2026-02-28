import time
import json
from typing import Optional
from langchain_core.tools import tool
from monday_client import monday_client
from data_cleaner import data_cleaner
from config import DEALS_BOARD_ID, WORKORDERS_BOARD_ID


def _format_currency(value: float) -> str:
    """Format value in Indian currency notation."""
    if value is None:
        return "N/A"
    if value >= 1_00_00_000:
        return f"₹{value / 1_00_00_000:.2f} Cr"
    elif value >= 1_00_000:
        return f"₹{value / 1_00_000:.2f} L"
    else:
        return f"₹{value:,.0f}"


def _filter_records(records: list[dict], filters: dict) -> list[dict]:
    """Apply filters to a list of records."""
    filtered = records
    for key, value in filters.items():
        if value is None:
            continue
        if isinstance(value, list):
            filtered = [r for r in filtered if r.get(key) in value]
        else:
            filtered = [r for r in filtered if r.get(key) == value]
    return filtered


@tool
async def query_deals_board(
    status: Optional[str] = None,
    sector: Optional[str] = None,
    stage: Optional[str] = None,
    owner: Optional[str] = None,
    closure_probability: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Query the Deals board on Monday.com. Use this to get deal pipeline data
    including deal names, values, stages, statuses, sectors, owners, and dates.

    Supports filtering by:
    - status: Won, Dead, Open, On Hold
    - sector: Renewables, Mining, Railways, Powerline, Construction, Others, DSP, Tender, Manufacturing, Aviation, Security and Surveillance
    - stage: A. Lead Generated through O. Not Relevant at all, or Project Completed
    - owner: OWNER_001 through OWNER_007
    - closure_probability: High, Medium, Low
    - date_from/date_to: ISO date strings (YYYY-MM-DD) for filtering by Tentative Close Date
    """
    start_time = time.time()

    # Fetch all items from Monday.com (LIVE query, no cache)
    items, api_ms = await monday_client.get_board_items(DEALS_BOARD_ID)
    records = monday_client.parse_items_to_records(items)

    # Clean data
    cleaned, caveats = data_cleaner.clean_deals(records)
    cleaning_log = data_cleaner.get_cleaning_log()

    # Apply filters
    filters = {}
    if status:
        filters["Deal Status"] = status
    if sector:
        filters["Sector/service"] = sector
    if stage:
        filters["Deal Stage"] = stage
    if owner:
        filters["Owner code"] = owner
    if closure_probability:
        filters["Closure Probability"] = closure_probability

    filtered = _filter_records(cleaned, filters)

    # Apply date filtering
    if date_from or date_to:
        date_filtered = []
        for r in filtered:
            tentative = r.get("Tentative Close Date")
            if not tentative:
                continue
            if date_from and tentative < date_from:
                continue
            if date_to and tentative > date_to:
                continue
            date_filtered.append(r)
        filtered = date_filtered

    # Compute summary stats
    total_value = sum(
        r.get("Masked Deal value") or 0 for r in filtered
        if r.get("Masked Deal value") is not None
    )
    valued_count = sum(
        1 for r in filtered if r.get("Masked Deal value") is not None
    )

    # Build stage breakdown
    stage_breakdown = {}
    for r in filtered:
        s = r.get("Deal Stage") or "Unknown"
        stage_breakdown[s] = stage_breakdown.get(s, 0) + 1

    # Build status breakdown
    status_breakdown = {}
    for r in filtered:
        st = r.get("Deal Status") or "Unknown"
        status_breakdown[st] = status_breakdown.get(st, 0) + 1

    # Build sector breakdown
    sector_breakdown = {}
    for r in filtered:
        sec = r.get("Sector/service") or "Unknown"
        sector_breakdown[sec] = sector_breakdown.get(sec, 0) + 1

    elapsed = round((time.time() - start_time) * 1000)

    # Compute win rate for this filtered set
    won_count = status_breakdown.get("Won", 0)
    dead_count = status_breakdown.get("Dead", 0)
    decided = won_count + dead_count
    win_rate = round(won_count / decided * 100, 1) if decided > 0 else None

    return {
        "total_deals": len(filtered),
        "IMPORTANT_win_rate": f"Won={won_count}, Dead={dead_count}, Win Rate = {won_count}/{decided} = {win_rate}%" if win_rate is not None else "No decided deals in this set",
        "win_rate_pct": win_rate,
        "won_count": won_count,
        "dead_count": dead_count,
        "total_value": total_value,
        "total_value_formatted": _format_currency(total_value),
        "valued_deals_count": valued_count,
        "status_breakdown": status_breakdown,
        "stage_breakdown": stage_breakdown,
        "sector_breakdown": sector_breakdown,
        "deals": [
            {
                "name": r.get("name"),
                "status": r.get("Deal Status"),
                "stage": r.get("Deal Stage"),
                "value": r.get("Masked Deal value"),
                "value_formatted": _format_currency(r.get("Masked Deal value")),
                "sector": r.get("Sector/service"),
                "owner": r.get("Owner code"),
                "probability": r.get("Closure Probability"),
                "tentative_close": r.get("Tentative Close Date"),
                "created": r.get("Created Date"),
            }
            for r in filtered
        ],
        "caveats": caveats,
        "cleaning_steps": cleaning_log,
        "api_time_ms": api_ms,
        "total_time_ms": elapsed,
        "filters_applied": {
            k: v for k, v in {
                "status": status, "sector": sector, "stage": stage,
                "owner": owner, "closure_probability": closure_probability,
                "date_from": date_from, "date_to": date_to,
            }.items() if v is not None
        },
    }


@tool
async def query_workorders_board(
    execution_status: Optional[str] = None,
    sector: Optional[str] = None,
    nature_of_work: Optional[str] = None,
    billing_status: Optional[str] = None,
    wo_status: Optional[str] = None,
    deal_name: Optional[str] = None,
    owner: Optional[str] = None,
) -> dict:
    """Query the Work Orders board on Monday.com. Use this to get work order
    execution, billing, and collection data.

    Supports filtering by:
    - execution_status: Completed, Ongoing, Not Started, Pause/struck, Partial Completed, Executed until current month, Details pending
    - sector: Mining, Renewables, Railways, Powerline, Construction, Others
    - nature_of_work: One time Project, POC, Annual Rate Contract, Monthly Contract
    - billing_status: Billed, Partially Billed, Not Billable, Update Required, Stuck
    - wo_status: Closed, Open
    - deal_name: specific deal name to look up
    - owner: BD/KAM Personnel code (OWNER_001 through OWNER_007)
    """
    start_time = time.time()

    items, api_ms = await monday_client.get_board_items(WORKORDERS_BOARD_ID)
    records = monday_client.parse_items_to_records(items)

    cleaned, caveats = data_cleaner.clean_workorders(records)
    cleaning_log = data_cleaner.get_cleaning_log()

    # Apply filters
    filters = {}
    if execution_status:
        filters["Execution Status"] = execution_status
    if sector:
        filters["Sector"] = sector
    if nature_of_work:
        filters["Nature of Work"] = nature_of_work
    if billing_status:
        filters["Billing Status"] = billing_status
    if wo_status:
        filters["WO Status (billed)"] = wo_status
    if deal_name:
        filters["Deal name masked"] = deal_name
    if owner:
        filters["BD/KAM Personnel code"] = owner

    filtered = _filter_records(cleaned, filters)

    # Financial aggregates
    total_amount = sum(
        r.get("Amount in Rupees (Excl of GST) (Masked)") or 0
        for r in filtered
        if r.get("Amount in Rupees (Excl of GST) (Masked)") is not None
    )
    total_billed = sum(
        r.get("Billed Value in Rupees (Excl of GST.) (Masked)") or 0
        for r in filtered
        if r.get("Billed Value in Rupees (Excl of GST.) (Masked)") is not None
    )
    total_collected = sum(
        r.get("Collected Amount in Rupees (Incl of GST.) (Masked)") or 0
        for r in filtered
        if r.get("Collected Amount in Rupees (Incl of GST.) (Masked)") is not None
    )
    total_receivable = sum(
        r.get("Amount Receivable (Masked)") or 0
        for r in filtered
        if r.get("Amount Receivable (Masked)") is not None
    )
    total_to_bill = sum(
        r.get("Amount to be billed in Rupees (Excl of GST.) (Masked)") or 0
        for r in filtered
        if r.get("Amount to be billed in Rupees (Excl of GST.) (Masked)") is not None
    )

    # Execution status breakdown
    exec_breakdown = {}
    for r in filtered:
        es = r.get("Execution Status") or "Unknown"
        exec_breakdown[es] = exec_breakdown.get(es, 0) + 1

    # Sector breakdown
    sector_breakdown = {}
    for r in filtered:
        sec = r.get("Sector") or "Unknown"
        sector_breakdown[sec] = sector_breakdown.get(sec, 0) + 1

    elapsed = round((time.time() - start_time) * 1000)

    return {
        "total_work_orders": len(filtered),
        "financials": {
            "total_amount": total_amount,
            "total_amount_formatted": _format_currency(total_amount),
            "total_billed": total_billed,
            "total_billed_formatted": _format_currency(total_billed),
            "total_collected": total_collected,
            "total_collected_formatted": _format_currency(total_collected),
            "total_receivable": total_receivable,
            "total_receivable_formatted": _format_currency(total_receivable),
            "total_to_bill": total_to_bill,
            "total_to_bill_formatted": _format_currency(total_to_bill),
        },
        "execution_breakdown": exec_breakdown,
        "sector_breakdown": sector_breakdown,
        "work_orders": [
            {
                "serial": r.get("Serial #"),
                "deal_name": r.get("Deal name masked"),
                "customer": r.get("Customer Name Code"),
                "sector": r.get("Sector"),
                "execution_status": r.get("Execution Status"),
                "nature": r.get("Nature of Work"),
                "type_of_work": r.get("Type of Work"),
                "amount_excl": r.get("Amount in Rupees (Excl of GST) (Masked)"),
                "amount_excl_formatted": _format_currency(
                    r.get("Amount in Rupees (Excl of GST) (Masked)")
                ),
                "billed": r.get("Billed Value in Rupees (Excl of GST.) (Masked)"),
                "collected": r.get("Collected Amount in Rupees (Incl of GST.) (Masked)"),
                "receivable": r.get("Amount Receivable (Masked)"),
                "wo_status": r.get("WO Status (billed)"),
                "billing_status": r.get("Billing Status"),
                "owner": r.get("BD/KAM Personnel code"),
            }
            for r in filtered
        ],
        "caveats": caveats,
        "cleaning_steps": cleaning_log,
        "api_time_ms": api_ms,
        "total_time_ms": elapsed,
        "filters_applied": {
            k: v for k, v in {
                "execution_status": execution_status, "sector": sector,
                "nature_of_work": nature_of_work, "billing_status": billing_status,
                "wo_status": wo_status, "deal_name": deal_name, "owner": owner,
            }.items() if v is not None
        },
    }


@tool
async def cross_board_analysis(
    sector: Optional[str] = None,
    owner: Optional[str] = None,
    deal_name: Optional[str] = None,
) -> dict:
    """Join Deals and Work Orders data by deal name to analyze the full lifecycle:
    deal pipeline → work order execution → billing → collection.

    Use when the question involves BOTH pipeline AND execution/billing data.
    For example: end-to-end sector performance, deal-to-collection tracking,
    or revenue realization analysis.

    Supports filtering by:
    - sector: Mining, Renewables, Railways, Powerline, Construction, Others
    - owner: OWNER_001 through OWNER_007
    - deal_name: specific deal name for detailed lifecycle view
    """
    start_time = time.time()

    # Fetch both boards concurrently
    import asyncio
    deals_task = monday_client.get_board_items(DEALS_BOARD_ID)
    wo_task = monday_client.get_board_items(WORKORDERS_BOARD_ID)

    (deal_items, deals_api_ms), (wo_items, wo_api_ms) = await asyncio.gather(
        deals_task, wo_task
    )

    deal_records = monday_client.parse_items_to_records(deal_items)
    wo_records = monday_client.parse_items_to_records(wo_items)

    # Clean both
    cleaned_deals, deals_caveats = data_cleaner.clean_deals(deal_records)
    deals_log = data_cleaner.get_cleaning_log()
    cleaned_wo, wo_caveats = data_cleaner.clean_workorders(wo_records)
    wo_log = data_cleaner.get_cleaning_log()

    # Apply filters to deals
    if sector:
        cleaned_deals = [
            d for d in cleaned_deals if d.get("Sector/service") == sector
        ]
        cleaned_wo = [w for w in cleaned_wo if w.get("Sector") == sector]
    if owner:
        cleaned_deals = [
            d for d in cleaned_deals if d.get("Owner code") == owner
        ]
        cleaned_wo = [
            w for w in cleaned_wo if w.get("BD/KAM Personnel code") == owner
        ]
    if deal_name:
        cleaned_deals = [d for d in cleaned_deals if d.get("name") == deal_name]
        cleaned_wo = [
            w for w in cleaned_wo if w.get("Deal name masked") == deal_name
        ]

    # Cross-board join on deal name
    deal_names_in_deals = {d.get("name") for d in cleaned_deals if d.get("name")}
    wo_deal_names = {
        w.get("Deal name masked") for w in cleaned_wo if w.get("Deal name masked")
    }
    common_names = deal_names_in_deals & wo_deal_names

    # Build lifecycle view for common deals
    lifecycle = []
    for name in common_names:
        deal = next(
            (d for d in cleaned_deals if d.get("name") == name), None
        )
        wos = [w for w in cleaned_wo if w.get("Deal name masked") == name]

        if deal:
            wo_total_amount = sum(
                w.get("Amount in Rupees (Excl of GST) (Masked)") or 0
                for w in wos
                if w.get("Amount in Rupees (Excl of GST) (Masked)") is not None
            )
            wo_total_billed = sum(
                w.get("Billed Value in Rupees (Excl of GST.) (Masked)") or 0
                for w in wos
                if w.get("Billed Value in Rupees (Excl of GST.) (Masked)") is not None
            )
            wo_total_collected = sum(
                w.get("Collected Amount in Rupees (Incl of GST.) (Masked)") or 0
                for w in wos
                if w.get("Collected Amount in Rupees (Incl of GST.) (Masked)") is not None
            )
            wo_total_receivable = sum(
                w.get("Amount Receivable (Masked)") or 0
                for w in wos
                if w.get("Amount Receivable (Masked)") is not None
            )

            lifecycle.append({
                "deal_name": name,
                "deal_status": deal.get("Deal Status"),
                "deal_stage": deal.get("Deal Stage"),
                "deal_value": deal.get("Masked Deal value"),
                "deal_value_formatted": _format_currency(deal.get("Masked Deal value")),
                "sector": deal.get("Sector/service"),
                "owner": deal.get("Owner code"),
                "work_order_count": len(wos),
                "wo_total_amount": wo_total_amount,
                "wo_total_amount_formatted": _format_currency(wo_total_amount),
                "wo_total_billed": wo_total_billed,
                "wo_total_billed_formatted": _format_currency(wo_total_billed),
                "wo_total_collected": wo_total_collected,
                "wo_total_collected_formatted": _format_currency(wo_total_collected),
                "wo_total_receivable": wo_total_receivable,
                "wo_total_receivable_formatted": _format_currency(wo_total_receivable),
                "wo_statuses": [w.get("Execution Status") for w in wos],
            })

    # Pipeline summary (deals board)
    deals_summary = {
        "total_deals": len(cleaned_deals),
        "status_breakdown": {},
        "total_pipeline_value": sum(
            d.get("Masked Deal value") or 0 for d in cleaned_deals
            if d.get("Masked Deal value") is not None
        ),
    }
    for d in cleaned_deals:
        st = d.get("Deal Status") or "Unknown"
        deals_summary["status_breakdown"][st] = (
            deals_summary["status_breakdown"].get(st, 0) + 1
        )

    # WO summary
    wo_summary = {
        "total_work_orders": len(cleaned_wo),
        "execution_breakdown": {},
        "total_wo_value": sum(
            w.get("Amount in Rupees (Excl of GST) (Masked)") or 0
            for w in cleaned_wo
            if w.get("Amount in Rupees (Excl of GST) (Masked)") is not None
        ),
        "total_billed": sum(
            w.get("Billed Value in Rupees (Excl of GST.) (Masked)") or 0
            for w in cleaned_wo
            if w.get("Billed Value in Rupees (Excl of GST.) (Masked)") is not None
        ),
        "total_collected": sum(
            w.get("Collected Amount in Rupees (Incl of GST.) (Masked)") or 0
            for w in cleaned_wo
            if w.get("Collected Amount in Rupees (Incl of GST.) (Masked)") is not None
        ),
    }
    for w in cleaned_wo:
        es = w.get("Execution Status") or "Unknown"
        wo_summary["execution_breakdown"][es] = (
            wo_summary["execution_breakdown"].get(es, 0) + 1
        )

    elapsed = round((time.time() - start_time) * 1000)

    return {
        "common_deal_count": len(common_names),
        "deals_only_count": len(deal_names_in_deals - wo_deal_names),
        "wo_only_count": len(wo_deal_names - deal_names_in_deals),
        "deals_summary": deals_summary,
        "wo_summary": wo_summary,
        "lifecycle": lifecycle,
        "caveats": deals_caveats + wo_caveats,
        "cleaning_steps": deals_log + wo_log,
        "api_time_ms": deals_api_ms + wo_api_ms,
        "total_time_ms": elapsed,
        "filters_applied": {
            k: v for k, v in {
                "sector": sector, "owner": owner, "deal_name": deal_name,
            }.items() if v is not None
        },
    }


@tool
async def aggregate_metrics(
    board: str,
    metric: str,
    group_by: str,
) -> dict:
    """Calculate aggregate metrics grouped by a dimension.

    Args:
        board: Which board to query — "deals", "workorders", or "both"
        metric: What to calculate — "sum_value", "count", "avg_value", "win_rate", "collection_rate"
        group_by: Dimension to group by — "sector", "owner", "stage", "status", "execution_status", "nature_of_work"

    Examples:
        - Total pipeline value by sector: board="deals", metric="sum_value", group_by="sector"
        - Win rate by owner: board="deals", metric="win_rate", group_by="owner"
        - Collection rate by sector: board="workorders", metric="collection_rate", group_by="sector"
        - Count of deals by stage: board="deals", metric="count", group_by="stage"
    """
    start_time = time.time()
    results = {}
    caveats = []
    cleaning_steps = []
    total_api_ms = 0

    # Column mappings for group_by
    deals_group_map = {
        "sector": "Sector/service",
        "owner": "Owner code",
        "stage": "Deal Stage",
        "status": "Deal Status",
    }
    wo_group_map = {
        "sector": "Sector",
        "owner": "BD/KAM Personnel code",
        "execution_status": "Execution Status",
        "nature_of_work": "Nature of Work",
    }

    if board in ("deals", "both"):
        items, api_ms = await monday_client.get_board_items(DEALS_BOARD_ID)
        total_api_ms += api_ms
        records = monday_client.parse_items_to_records(items)
        cleaned, d_caveats = data_cleaner.clean_deals(records)
        caveats.extend(d_caveats)
        cleaning_steps.extend(data_cleaner.get_cleaning_log())

        group_col = deals_group_map.get(group_by, group_by)
        groups = {}
        for r in cleaned:
            key = r.get(group_col) or "Unknown"
            if key not in groups:
                groups[key] = []
            groups[key].append(r)

        if metric == "count":
            results["deals"] = {k: len(v) for k, v in groups.items()}

        elif metric == "sum_value":
            results["deals"] = {}
            for k, v in groups.items():
                total = sum(
                    r.get("Masked Deal value") or 0 for r in v
                    if r.get("Masked Deal value") is not None
                )
                count = sum(
                    1 for r in v if r.get("Masked Deal value") is not None
                )
                results["deals"][k] = {
                    "total": total,
                    "total_formatted": _format_currency(total),
                    "valued_count": count,
                    "total_count": len(v),
                }

        elif metric == "avg_value":
            results["deals"] = {}
            for k, v in groups.items():
                values = [
                    r.get("Masked Deal value") for r in v
                    if r.get("Masked Deal value") is not None
                ]
                if values:
                    avg = sum(values) / len(values)
                    results["deals"][k] = {
                        "average": avg,
                        "average_formatted": _format_currency(avg),
                        "count": len(values),
                    }

        elif metric == "win_rate":
            results["deals"] = {}
            for k, v in groups.items():
                won = sum(1 for r in v if r.get("Deal Status") == "Won")
                dead = sum(1 for r in v if r.get("Deal Status") == "Dead")
                total_decided = won + dead
                if total_decided > 0:
                    rate = round(won / total_decided * 100, 1)
                else:
                    rate = None
                results["deals"][k] = {
                    "IMPORTANT_calculation": f"Win Rate for {k}: {won}/{total_decided} = {rate}%",
                    "win_rate_pct": rate,
                    "won": won,
                    "dead": dead,
                    "total_decided": total_decided,
                    "open": sum(1 for r in v if r.get("Deal Status") == "Open"),
                    "on_hold": sum(
                        1 for r in v if r.get("Deal Status") == "On Hold"
                    ),
                }

    if board in ("workorders", "both"):
        items, api_ms = await monday_client.get_board_items(WORKORDERS_BOARD_ID)
        total_api_ms += api_ms
        records = monday_client.parse_items_to_records(items)
        cleaned, w_caveats = data_cleaner.clean_workorders(records)
        caveats.extend(w_caveats)
        cleaning_steps.extend(data_cleaner.get_cleaning_log())

        group_col = wo_group_map.get(group_by, group_by)
        groups = {}
        for r in cleaned:
            key = r.get(group_col) or "Unknown"
            if key not in groups:
                groups[key] = []
            groups[key].append(r)

        if metric == "count":
            results["workorders"] = {k: len(v) for k, v in groups.items()}

        elif metric == "sum_value":
            results["workorders"] = {}
            for k, v in groups.items():
                total = sum(
                    r.get("Amount in Rupees (Excl of GST) (Masked)") or 0
                    for r in v
                    if r.get("Amount in Rupees (Excl of GST) (Masked)") is not None
                )
                results["workorders"][k] = {
                    "total": total,
                    "total_formatted": _format_currency(total),
                    "count": len(v),
                }

        elif metric == "collection_rate":
            results["workorders"] = {}
            for k, v in groups.items():
                billed = sum(
                    r.get("Billed Value in Rupees (Excl of GST.) (Masked)") or 0
                    for r in v
                    if r.get("Billed Value in Rupees (Excl of GST.) (Masked)") is not None
                )
                collected = sum(
                    r.get("Collected Amount in Rupees (Incl of GST.) (Masked)") or 0
                    for r in v
                    if r.get("Collected Amount in Rupees (Incl of GST.) (Masked)") is not None
                )
                rate = round(collected / billed * 100, 1) if billed > 0 else None
                results["workorders"][k] = {
                    "collection_rate_pct": rate,
                    "total_billed": billed,
                    "total_billed_formatted": _format_currency(billed),
                    "total_collected": collected,
                    "total_collected_formatted": _format_currency(collected),
                    "count": len(v),
                }

    elapsed = round((time.time() - start_time) * 1000)

    return {
        "board": board,
        "metric": metric,
        "group_by": group_by,
        "results": results,
        "caveats": caveats,
        "cleaning_steps": cleaning_steps,
        "api_time_ms": total_api_ms,
        "total_time_ms": elapsed,
    }


@tool
async def get_data_summary(
    board: str = "both",
) -> dict:
    """Get a high-level summary of Monday.com boards including total counts,
    value distributions, status breakdowns, and data quality metrics.

    Use when the user asks a very broad question, wants an overview, or says
    things like "how's the business doing?" or "give me a summary".

    Args:
        board: Which board(s) to summarize — "deals", "workorders", or "both"
    """
    start_time = time.time()
    summary = {}
    caveats = []
    cleaning_steps = []
    total_api_ms = 0

    if board in ("deals", "both"):
        items, api_ms = await monday_client.get_board_items(DEALS_BOARD_ID)
        total_api_ms += api_ms
        records = monday_client.parse_items_to_records(items)
        cleaned, d_caveats = data_cleaner.clean_deals(records)
        caveats.extend(d_caveats)
        cleaning_steps.extend(data_cleaner.get_cleaning_log())

        # Status breakdown
        status_counts = {}
        for r in cleaned:
            st = r.get("Deal Status") or "Unknown"
            status_counts[st] = status_counts.get(st, 0) + 1

        # Sector breakdown
        sector_counts = {}
        for r in cleaned:
            sec = r.get("Sector/service") or "Unknown"
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

        # Stage breakdown
        stage_counts = {}
        for r in cleaned:
            stg = r.get("Deal Stage") or "Unknown"
            stage_counts[stg] = stage_counts.get(stg, 0) + 1

        # Value stats
        values = [
            r.get("Masked Deal value") for r in cleaned
            if r.get("Masked Deal value") is not None
        ]
        total_value = sum(values) if values else 0
        avg_value = total_value / len(values) if values else 0

        # Win rate
        won = status_counts.get("Won", 0)
        dead = status_counts.get("Dead", 0)
        win_rate = round(won / (won + dead) * 100, 1) if (won + dead) > 0 else None

        # Open pipeline
        open_deals = [r for r in cleaned if r.get("Deal Status") == "Open"]
        open_value = sum(
            r.get("Masked Deal value") or 0 for r in open_deals
            if r.get("Masked Deal value") is not None
        )

        summary["deals"] = {
            "IMPORTANT_win_rate_calculation": f"Won={won}, Dead={dead}, Total Decided={won+dead}, Win Rate = {won}/{won+dead} = {win_rate}% (this is NOT 100%)" if win_rate is not None else "No decided deals",
            "total_count": len(cleaned),
            "status_breakdown": status_counts,
            "sector_breakdown": sector_counts,
            "stage_breakdown": stage_counts,
            "total_value": total_value,
            "total_value_formatted": _format_currency(total_value),
            "average_deal_value": avg_value,
            "average_deal_value_formatted": _format_currency(avg_value),
            "valued_deals": len(values),
            "win_rate_pct": win_rate,
            "won_count": won,
            "dead_count": dead,
            "open_pipeline": {
                "count": len(open_deals),
                "value": open_value,
                "value_formatted": _format_currency(open_value),
            },
            "owner_counts": {},
        }
        for r in cleaned:
            ow = r.get("Owner code") or "Unknown"
            summary["deals"]["owner_counts"][ow] = (
                summary["deals"]["owner_counts"].get(ow, 0) + 1
            )

    if board in ("workorders", "both"):
        items, api_ms = await monday_client.get_board_items(WORKORDERS_BOARD_ID)
        total_api_ms += api_ms
        records = monday_client.parse_items_to_records(items)
        cleaned, w_caveats = data_cleaner.clean_workorders(records)
        caveats.extend(w_caveats)
        cleaning_steps.extend(data_cleaner.get_cleaning_log())

        exec_counts = {}
        for r in cleaned:
            es = r.get("Execution Status") or "Unknown"
            exec_counts[es] = exec_counts.get(es, 0) + 1

        sector_counts = {}
        for r in cleaned:
            sec = r.get("Sector") or "Unknown"
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

        total_amount = sum(
            r.get("Amount in Rupees (Excl of GST) (Masked)") or 0
            for r in cleaned
            if r.get("Amount in Rupees (Excl of GST) (Masked)") is not None
        )
        total_billed = sum(
            r.get("Billed Value in Rupees (Excl of GST.) (Masked)") or 0
            for r in cleaned
            if r.get("Billed Value in Rupees (Excl of GST.) (Masked)") is not None
        )
        total_collected = sum(
            r.get("Collected Amount in Rupees (Incl of GST.) (Masked)") or 0
            for r in cleaned
            if r.get("Collected Amount in Rupees (Incl of GST.) (Masked)") is not None
        )
        total_receivable = sum(
            r.get("Amount Receivable (Masked)") or 0
            for r in cleaned
            if r.get("Amount Receivable (Masked)") is not None
        )

        summary["workorders"] = {
            "total_count": len(cleaned),
            "execution_breakdown": exec_counts,
            "sector_breakdown": sector_counts,
            "financials": {
                "total_amount": total_amount,
                "total_amount_formatted": _format_currency(total_amount),
                "total_billed": total_billed,
                "total_billed_formatted": _format_currency(total_billed),
                "total_collected": total_collected,
                "total_collected_formatted": _format_currency(total_collected),
                "total_receivable": total_receivable,
                "total_receivable_formatted": _format_currency(total_receivable),
                "billing_rate_pct": (
                    round(total_billed / total_amount * 100, 1)
                    if total_amount > 0 else None
                ),
                "collection_rate_pct": (
                    round(total_collected / total_billed * 100, 1)
                    if total_billed > 0 else None
                ),
            },
        }

    elapsed = round((time.time() - start_time) * 1000)

    return {
        "summary": summary,
        "caveats": caveats,
        "cleaning_steps": cleaning_steps,
        "api_time_ms": total_api_ms,
        "total_time_ms": elapsed,
    }


# Export all tools for the agent
ALL_TOOLS = [
    query_deals_board,
    query_workorders_board,
    cross_board_analysis,
    aggregate_metrics,
    get_data_summary,
]
