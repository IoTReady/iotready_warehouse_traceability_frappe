import frappe
from datetime import datetime


def validate_mandatory_fields(crate, activity):
    fields = {
        "Procurement": ["crate_id", "item_code", "supplier", "quantity", "weight"],
        "Transfer Out": ["crate_id", "target_warehouse", "vehicle"],
        "Transfer In": ["crate_id"],
        "Cycle Count": ["crate_id", "weight"],
        "Crate Splitting": ["crate_id", "quantity", "weight", "parent_crate_id"],
        "Identify": ["crate_id"],
        "Delete": ["crate_id"],
    }
    for field in fields[activity]:
        assert field in crate, f"{field} missing from request"


# def validate_crate(crate_id):
#     assert frappe.db.exists("Crate", crate_id), f"Crate {crate_id} does not exist."
