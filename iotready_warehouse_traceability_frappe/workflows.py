import frappe
import json
from datetime import datetime, timedelta
from iotready_warehouse_traceability_frappe import db

SCAN_CHAR = "d3edcb21-d7aa-4731-bad8-946651538501"
WEIGHT_CHAR = "d3edcb21-d7aa-4731-bad8-946651538502"
DISPLAY_CHAR = "d3edcb21-d7aa-4731-bad8-946651538512"
LED_CHAR = "d3edcb21-d7aa-4731-bad8-946651538514"


def get_new_activity_session(activity: str):
    session_id = frappe.generate_hash(length=10)
    context = {
        "activity": activity,
        "user": frappe.session.user,
        "session_id": session_id,
    }
    frappe.cache().set(f"activity_session:{session_id}", json.dumps(context), ex=86400)
    return session_id 


def get_activity_session(session_id: str):
    context = frappe.cache().get(f"activity_session:{session_id}")
    if not context:
        return None
    context = json.loads(context)
    if context.get("user") != frappe.session.user:
        return None
    frappe.cache().set(f"activity_session:{session_id}", json.dumps(context), ex=86400)
    return context


def update_activity_session(session_id: str, new_context: dict | str):
    if not new_context:
        return None
    context = get_activity_session(session_id)
    if not context:
        return None
    if isinstance(new_context, str):
        new_context = json.loads(new_context)
    for key, value in new_context.items():
        context[key] = value
    frappe.cache().set(
        f"activity_session:{session_id}", frappe.as_json(context), ex=86400
    )
    return context

def log_ingress(crates, activity, result, creation=None):
    try:
        log = frappe.new_doc("Ingress Log")
        log.name = frappe.generate_hash(length=10)
        if creation:
            log.creation = creation
        else:
            log.creation = datetime.now() + timedelta(hours=5, minutes=30)
        log.modified = datetime.now() + timedelta(hours=5, minutes=30)
        log.owner = frappe.session.user
        log.modified_by = frappe.session.user
        log.activity = activity
        # log.crate = json.dumps(crate)
        log.result = json.dumps(result)
        if len(crates) > 0:
            log.crate_id = crates[0].get("crate_id")
        log.raw_payload = json.dumps({"crates": crates, "activity": activity})
        db.deferred_insert(log)
    except Exception as e:
        print("Log Ingress", str(e))

