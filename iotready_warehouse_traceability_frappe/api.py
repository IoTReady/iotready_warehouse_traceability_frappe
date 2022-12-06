import frappe
from iotready_warehouse_traceability_frappe import utils


@frappe.whitelist(allow_guest=False)
def get_configuration():
    """
    Called by app user to retrieve warehouse configuration.
    """
    return utils.get_configuration()


@frappe.whitelist(allow_guest=False)
def record_events(crate: dict, activity: str):
    """
    Called by app user to upload crate events.
    """
    return utils.record_events(crate, activity)
