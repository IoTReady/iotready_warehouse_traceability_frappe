import frappe
import json
from frappe.utils import cstr, create_batch

queue_prefix = "warehouse_doctype_queue_"


def deferred_insert(doc):
    doctype = doc.doctype
    docname = doc.name
    if not (doctype and docname):
        frappe.throw("Doctype and Docname are required")
    redis_key = f"{queue_prefix}{doctype}"
    d = doc.as_dict()
    skip = ["docstatus", "doctype", "idx"]
    for key in list(d.keys()):
        if key.startswith("_"):
            d.pop(key)
        if key in skip:
            d.pop(key)
    frappe.cache().rpush(redis_key, frappe.as_json(d))


def get_key_name(key: str) -> str:
    return cstr(key).split("|")[1]


def clear_queue(doctype):
    redis_key = f"{queue_prefix}{doctype}"
    frappe.cache().delete_keys(redis_key)


def bulk_insert(doctype):
    redis_key = f"{queue_prefix}{doctype}"
    queue_keys = frappe.cache().get_keys(redis_key)
    record_count = 0
    unique_names = set()
    records = []
    for key in queue_keys:
        queue_key = get_key_name(key)
        while frappe.cache().llen(queue_key) > 0:
            record = frappe.cache().lpop(queue_key)
            record = json.loads(record.decode("utf-8"))
            if isinstance(record, dict):
                record_count += 1
                if record["name"] in unique_names:
                    continue
                unique_names.add(record["name"])
                records.append(record)
            else:
                print("Invalid record")
    if records:
        print(f"Inserting {len(records)} records")
        for batch in create_batch(records, 1000):
            fields = list(batch[0].keys())
            values = (tuple(record.values()) for record in batch)
            frappe.db.bulk_insert(doctype, fields, values)
    frappe.db.commit()
    print(f"Inserted {record_count} records")
    return record_count


def bulk_delete(doctype, docnames):
    """
    Delete records in bulk. This is a wrapper around frappe.db.sql
    docnames is a list of names
    """
    if not doctype or not docnames:
        return
    placeholders = ", ".join(["%s"] * len(docnames))
    sql = f"""DELETE FROM `tab{doctype}` WHERE name IN ({placeholders})"""
    frappe.db.sql(sql, values=docnames)
    frappe.db.commit()
    print(f"Deleted {len(docnames)} records")


