import frappe
import json
from datetime import datetime


@frappe.whitelist()
def hello():
    return {"ok": True, "now": datetime.now().isoformat()}


@frappe.whitelist()
def run(**kwargs):
    cmd = kwargs.get('command')
    data = kwargs.get('data')
    if data and isinstance(data, str):
        data = json.loads(data)
    if frappe.get_attr(cmd) in frappe.whitelisted:
        return frappe.get_attr(cmd)(**data)
    else:
        frappe.throw(f"{cmd} is not whitelisted.")