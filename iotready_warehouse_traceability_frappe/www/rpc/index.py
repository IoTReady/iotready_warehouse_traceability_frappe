import frappe

def get_context():
    if "System Manager" not in frappe.get_roles():
        frappe.throw("You are not permitted to run remote procedure calls")