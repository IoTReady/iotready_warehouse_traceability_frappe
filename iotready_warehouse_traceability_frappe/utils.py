import json
import frappe
from datetime import datetime, timedelta
from iotready_warehouse_traceability_frappe.validations import *


def get_user_warehouse_hook():
    return frappe.db.get_single_value(
        "IoTReady Traceability Settings", "get_user_warehouse_hook"
    )


def normal_round(num, ndigits=0):
    """
    Rounds a float to the specified number of decimal places.
    num: the value to round
    ndigits: the number of digits to round to
    From: https://medium.com/thefloatingpoint/pythons-round-function-doesn-t-do-what-you-think-71765cfa86a8
    """
    if ndigits == 0:
        return int(num + 0.5)
    else:
        digit_value = 10**ndigits
        return int(num * digit_value + 0.5) / digit_value


def get_quantity_in_uom(qty, uom):
    if uom.lower() == "gram":
        qty = normal_round(qty / 1000, 3)
    elif uom.lower() == "kg":
        qty = normal_round(qty, 3)
    return qty


def get_display_quantity_in_uom(qty, uom):
    if uom.lower() == "gram":
        qty = normal_round(qty / 1000, 2)
        display_qty = f"{qty} Kg"
    elif uom.lower() == "kg":
        qty = normal_round(qty, 2)
        display_qty = f"{qty} Kg"
    elif uom.lower() in ["nos", "pcs"]:
        display_qty = f"{qty} Pcs"
    return display_qty


def set_crate_availability(crate_id, is_available_for_procurement):
    frappe.db.set_value(
        "Crate", crate_id, "is_available_for_procurement", is_available_for_procurement
    )


def set_crate_available_at(crate_id, available_at):
    frappe.db.set_value("Crate", crate_id, "available_at", available_at)


def release_crate(crate_id, delayed=True):
    set_crate_availability(crate_id, True)
    time_before_crate_release = frappe.db.get_single_value(
        "IoTReady Traceability Settings", "time_before_crate_release"
    )
    now = datetime.now()
    if delayed:
        available_at = now + timedelta(minutes=int(time_before_crate_release or 15))
    else:
        available_at = now
    set_crate_available_at(crate_id, available_at)


def activity_crates(
    source_warehouse, target_warehouse, activity, status, reference_id, distinct=True
):
    filters = {
        "source_warehouse": source_warehouse,
        "target_warehouse": target_warehouse,
        "activity": activity,
        "status": status,
        "reference_id": reference_id,
    }
    crates = frappe.get_all(
        "Crate Activity",
        filters=filters,
        fields=[
            "name",
            "crate_id",
            "supplier_id",
            "supplier_name",
            "item_code",
            "item_name",
            "stock_uom",
            "grn_quantity",
            "crate_weight",
            "moisture_loss",
            "excess_weight",
            "wms_acknowledgement_id",
            "reference_id",
            "source_warehouse",
            "target_warehouse",
            "vehicle",
            "status",
            "creation",
            "owner",
            "capture_mode",
        ],
    )
    response = {}
    for row in crates:
        row["creation"] = row["creation"].strftime("%T %d-%m-%y")
        response[row["crate_id"]] = row
    return list(response.values())


def crates_to_items(crates: dict):
    items = {}
    for row in crates:
        sku = row["item_code"]
        quantity = get_quantity_in_uom(row["grn_quantity"], row["stock_uom"])
        if sku not in items:
            items[sku] = {
                "item_code": sku,
                "qty": quantity,
                "stock_uom": row["stock_uom"],
                "item_name": row["item_name"],
                "moisture_loss": row["moisture_loss"],
                "crate_weight": row["crate_weight"],
                "number_of_crates": 1,
            }
        else:
            items[sku]["qty"] += quantity
            items[sku]["moisture_loss"] += row["moisture_loss"]
            items[sku]["crate_weight"] += row["crate_weight"]
            items[sku]["number_of_crates"] += 1
    for sku in items:
        items[sku]["qty"] = normal_round(items[sku]["qty"], 2)
        items[sku]["moisture_loss"] = normal_round(items[sku]["moisture_loss"], 2)
        items[sku]["crate_weight"] = normal_round(items[sku]["crate_weight"], 2)
    return list(items.values())


def get_sku_table(items, activity):
    total_number_of_crates = sum([row["number_of_crates"] for row in items])
    context = {
        "items": items,
        "activity": activity,
        "total_number_of_crates": total_number_of_crates,
    }
    return frappe.render_template(
        "templates/includes/sku_table.html",
        context,
    )


def get_crate_table(crates, activity, is_editable=True):
    total_crate_weight = sum([row["crate_weight"] for row in crates])
    context = {
        "crates": crates,
        "is_editable": is_editable,
        "activity": activity,
        "total_crate_weight": total_crate_weight,
    }
    return frappe.render_template(
        "templates/includes/crate_table.html",
        context,
    )


@frappe.whitelist()
def delete_draft_crate_activities(crate_id):
    try:
        filters = {
            "crate_id": crate_id,
            "status": "Draft",
        }
        # We use get_all here to ignore get_list permissions and cause an exception
        # if a draft crate activity exists for this crate in another warehouse
        last = frappe.db.get_all(
            "Crate Activity", filters=filters, fields=["name", "activity"]
        )
        if len(last) > 0:
            for ref in last:
                frappe.delete_doc_if_exists("Crate Activity", ref["name"])
            frappe.db.commit()
            return f"Deleted {last[0]['activity']} for {crate_id}."
    except Exception as e:
        print(str(e))


def maybe_update_activity_fields(crate, doc):
    doc.grn_quantity = crate.get("quantity")
    doc.crate_weight = crate.get("weight")
    return doc


# TODO: Move to customer specific app via hook
def get_crate_details(crate_id: str):
    """
    Given a batch, return all events from procurement to stock entries.
    """
    crate_doc = frappe.get_doc("Crate", crate_id)
    item_code = crate_doc.item_code
    item = frappe.get_doc("Item", item_code)
    supplier_id = crate_doc.supplier_id
    payload = {
        "item": {
            "item_code": item_code,
            "item_name": item.item_name,
            "stock_uom": item.stock_uom,
            "uom_quantity": item.uom_quantity,
            "standard_crate_quantity": item.tertiary_package_quantity or 0,
        },
        "batch_quantity": crate_doc.last_known_weight,
        "grn_quantity": crate_doc.last_known_grn_quantity,
        "displayed_parent_quantity": get_display_quantity_in_uom(
            crate_doc.last_known_grn_quantity, item.stock_uom
        ),
    }
    if supplier_id:
        supplier = frappe.get_doc("Supplier", supplier_id)
        payload["supplier"] = {
            "supplier_id": supplier_id,
            "supplier_name": supplier.supplier_name,
            "phone_number": supplier.phone_number,
        }
    return payload


def create_procurement_activity(
    crate_id,
    activity,
    supplier,
    item_code,
    stock_uom,
    grn_quantity,
    crate_weight,
    source_warehouse,
):
    delete_draft_crate_activities(crate_id)
    doc = frappe.new_doc("Crate Activity")
    doc.crate_id = crate_id
    doc.activity = activity
    doc.supplier_id = supplier
    doc.item_code = item_code
    doc.stock_uom = stock_uom
    doc.grn_quantity = grn_quantity
    doc.crate_weight = crate_weight
    doc.source_warehouse = source_warehouse
    doc.target_warehouse = source_warehouse
    doc.save()
    frappe.db.commit()


def create_transfer_out_activity(
    crate_id, activity, source_warehouse, target_warehouse, vehicle, crate
):
    delete_draft_crate_activities(crate_id)
    doc = frappe.new_doc("Crate Activity")
    doc.crate_id = crate_id
    doc.activity = activity
    doc.source_warehouse = source_warehouse
    doc.target_warehouse = target_warehouse
    doc.vehicle = vehicle
    # These could be None
    doc = maybe_update_activity_fields(crate, doc)
    doc.save()
    frappe.db.commit()


def create_transfer_in_activity(crate_id, activity, target_warehouse, crate):
    delete_draft_crate_activities(crate_id)
    doc = frappe.new_doc("Crate Activity")
    doc.crate_id = crate_id
    doc.activity = activity
    doc.target_warehouse = target_warehouse
    # These could be None
    doc = maybe_update_activity_fields(crate, doc)
    print("create_transfer_in_activity", doc.as_dict())
    doc.save()
    frappe.db.commit()


def create_delete_activity(crate_id, activity, source_warehouse):
    doc = frappe.new_doc("Crate Activity")
    doc.crate_id = crate_id
    doc.activity = activity
    doc.source_warehouse = source_warehouse
    doc.reference_id = frappe.generate_hash()[-10:]
    doc.status = "Completed"
    doc.save()
    frappe.db.commit()


def create_cycle_count_activity(crate_id, activity, source_warehouse, crate):
    delete_draft_crate_activities(crate_id)
    doc = frappe.new_doc("Crate Activity")
    doc.crate_id = crate_id
    doc.activity = activity
    doc.source_warehouse = source_warehouse
    doc.reference_id = frappe.generate_hash()[-10:]
    # These could be None
    doc = maybe_update_activity_fields(crate, doc)
    doc.status = "Completed"
    doc.save()
    frappe.db.commit()
    return doc


def create_crate_splitting_activity(
    crate_id,
    activity,
    supplier,
    item_code,
    grn_quantity,
    crate_weight,
    source_warehouse,
):
    delete_draft_crate_activities(crate_id)
    doc = frappe.new_doc("Crate Activity")
    doc.crate_id = crate_id
    doc.activity = activity
    doc.supplier_id = supplier
    doc.item_code = item_code
    doc.grn_quantity = grn_quantity
    doc.crate_weight = crate_weight
    doc.source_warehouse = source_warehouse
    doc.status = "Completed"
    doc.save()
    frappe.db.commit()


# TODO: Move to customer specific app via hook
def get_configuration():
    """
    Called by app user to retrieve warehouse configuration.
    """
    get_configuration_hook = frappe.db.get_single_value(
        "IoTReady Traceability Settings", "get_configuration_hook"
    )
    return frappe.get_attr(get_configuration_hook)()


def procurement(crate: dict, activity: str):
    """
    Dispatcher for Procurement called by api.record_events
    Validates crate and adds to Purchase Receipt
    """
    source_warehouse = frappe.get_attr(get_user_warehouse_hook())()
    crate["crate_id"] = crate["crate_id"].strip()
    crate_id = crate["crate_id"]
    item_code = crate["item_code"]
    stock_uom = crate["stock_uom"]
    quantity = crate["quantity"]
    supplier = crate["supplier"]
    crate_weight = crate["weight"]
    grn_quantity = quantity
    create_procurement_activity(
        crate_id=crate_id,
        activity=activity,
        supplier=supplier,
        item_code=item_code,
        stock_uom=stock_uom,
        grn_quantity=grn_quantity,
        crate_weight=crate_weight,
        source_warehouse=source_warehouse,
    )
    return {"success": True, "message": "Crate Added"}


def transfer_out(crate: dict, activity: str):
    """
    For each crate process the stock transfer out request.
    """
    crate["crate_id"] = crate["crate_id"].strip()
    crate_id = crate["crate_id"]
    source_warehouse = (frappe.get_attr(get_user_warehouse_hook()))()
    target_warehouse = crate["target_warehouse"]
    vehicle = crate["vehicle"]
    create_transfer_out_activity(
        crate_id=crate_id,
        activity=activity,
        source_warehouse=source_warehouse,
        target_warehouse=target_warehouse,
        vehicle=vehicle,
        crate=crate,
    )
    return {"success": True, "message": "Transferred out."}


def transfer_in(crate: dict, activity: str):
    """
    For each crate process the stock transfer in request.
    """
    crate["crate_id"] = crate["crate_id"].strip()
    crate_id = crate["crate_id"]
    target_warehouse = frappe.get_attr(get_user_warehouse_hook())()
    create_transfer_in_activity(
        crate_id=crate_id,
        activity=activity,
        target_warehouse=target_warehouse,
        crate=crate,
    )
    return {
        "success": True,
        "message": "Transferred In.",
    }


@frappe.whitelist()
def delete_crate(crate: dict, activity: str):
    """
    Deletes crates from draft purchase receipts
    """
    if isinstance(crate, str):
        crate = json.loads(crate)
    crate["crate_id"] = crate["crate_id"].strip()
    crate_id = crate["crate_id"]
    source_warehouse = frappe.get_attr(get_user_warehouse_hook())()
    delete_draft_crate_activities(crate_id)
    create_delete_activity(
        crate_id=crate_id, activity=activity, source_warehouse=source_warehouse
    )
    return {
        "success": True,
        "message": "Crate deleted.",
    }


# def cycle_count(crate: dict, activity: str):
#     """
#     Updates and tracks crate weight and moisture loss.
#     """
#     crate["crate_id"] = crate["crate_id"].strip()
#     crate_id = crate["crate_id"]
#     validate_crate(crate_id)
#     validate_crate_in_use(crate_id)
#     source_warehouse = frappe.get_attr(get_user_warehouse_hook())()
#     validate_source_warehouse(crate_id, source_warehouse)
#     doc = create_cycle_count_activity(
#         crate_id=crate_id,
#         activity=activity,
#         source_warehouse=source_warehouse,
#         crate=crate,
#     )
#     if doc.actual_loss and doc.actual_loss > 0:
#         raise Exception(
#             f"Actual loss of {normal_round(doc.actual_loss,2)} kg and moisture loss of {normal_round(doc.moisture_loss,2)} kg recorded."
#         )
#     elif doc.moisture_loss and doc.moisture_loss > 0:
#         raise Exception(
#             f"Moisture loss of {normal_round(doc.moisture_loss,2)} kg recorded."
#         )
#     elif doc.excess_weight and doc.excess_weight > 0:
#         raise Exception(f"Weight increased by {normal_round(doc.excess_weight,2)} kg.")
#     return {
#         "success": True,
#         "message": "No change in weight.",
#     }


# def identify(crate: dict, activity: str):
#     crate["crate_id"] = crate["crate_id"].strip()
#     crate_id = crate["crate_id"]
#     validate_crate(crate_id)
#     validate_crate_in_use(crate_id)
#     source_warehouse = frappe.get_attr(get_user_warehouse_hook())()
#     validate_source_warehouse(crate_id, source_warehouse)
#     create_cycle_count_activity(
#         crate_id=crate_id,
#         activity=activity,
#         source_warehouse=source_warehouse,
#         crate=crate,
#     )
#     payload = {"success": True}
#     payload.update(get_crate_details(crate_id))
#     return payload


# def crate_splitting(crate: dict, activity: str):
#     crate["crate_id"] = crate["crate_id"].strip()
#     child_crate_id = crate["crate_id"]
#     parent_crate_id = crate["parent_crate_id"]
#     validate_crate(parent_crate_id)
#     validate_crate_in_use(parent_crate_id)
#     validate_crate_not_in_use(child_crate_id)
#     source_warehouse = frappe.get_attr(get_user_warehouse_hook())()
#     validate_source_warehouse(parent_crate_id, source_warehouse)
#     maybe_create_crate(child_crate_id)
#     set_crate_availability(child_crate_id, is_available_for_procurement=False)
#     parent_crate = frappe.get_doc("Crate", parent_crate_id)
#     item_code = parent_crate.item_code
#     stock_uom = parent_crate.stock_uom
#     parent_grn_quantity = parent_crate.last_known_grn_quantity
#     parent_weight = parent_crate.last_known_weight
#     supplier_id = parent_crate.supplier_id
#     child_weight = crate["weight"]
#     child_grn_quantity = crate["quantity"]
#     if stock_uom.lower() in ["nos", "pcs"]:
#         child_grn_quantity = child_weight
#     assert parent_grn_quantity >= child_grn_quantity, "Insufficient Quantity Remaining."
#     remaining_parent_quantity = parent_grn_quantity - child_grn_quantity
#     if remaining_parent_quantity < 0:
#         remaining_parent_quantity = 0
#     remaining_parent_weight = parent_weight - child_weight
#     if remaining_parent_weight < 0:
#         remaining_parent_weight = 0
#     create_crate_splitting_activity(
#         crate_id=child_crate_id,
#         activity=activity,
#         supplier=supplier_id,
#         item_code=item_code,
#         grn_quantity=child_grn_quantity,
#         crate_weight=child_weight,
#         source_warehouse=source_warehouse,
#     )
#     create_crate_splitting_activity(
#         crate_id=parent_crate_id,
#         activity=activity,
#         supplier=supplier_id,
#         item_code=item_code,
#         grn_quantity=remaining_parent_quantity,
#         crate_weight=remaining_parent_weight,
#         source_warehouse=source_warehouse,
#     )
#     displayed_quantity = get_display_quantity_in_uom(child_grn_quantity, stock_uom)
#     displayed_parent_quantity = get_display_quantity_in_uom(
#         remaining_parent_quantity, stock_uom
#     )
#     return {
#         "success": True,
#         "message": f"Child crate created with quantity: {displayed_quantity}",
#         "displayed_quantity": displayed_quantity,
#         "remaining_parent_quantity": normal_round(remaining_parent_quantity, 2),
#         "displayed_parent_quantity": displayed_parent_quantity,
#         "remaining_parent_weight": normal_round(remaining_parent_weight, 2),
#     }


def new_crate():
    crate = frappe.new_doc("Crate")
    crate.id = frappe.generate_hash()[-10:]
    crate.is_available_for_procurement = True
    crate.save()
    frappe.db.commit()
    return {"success": True, "message": crate.name}


allowed_activities = {
    "Procurement": procurement,
    "Transfer Out": transfer_out,
    "Transfer In": transfer_in,
    "Delete": delete_crate,
    # "Cycle Count": cycle_count,
    # "Identify": identify,
    # "Crate Splitting": crate_splitting,
}


def record_events(crate, activity):
    try:
        validate_mandatory_fields(crate, activity)
        prefix = activity.lower().replace(" ", "_")
        hook = frappe.db.get_single_value(
            "IoTReady Traceability Settings", f"{prefix}_event_hook"
        )
        hook_result = None
        if hook:
            crate, hook_result = frappe.get_attr(hook)(crate, activity)
        result = allowed_activities[activity](crate, activity)
        if hook_result:
            result.update(hook_result)
    except Exception as e:
        result = {"success": False, "message": str(e)}
    try:
        print(crate, activity)
        log = frappe.new_doc("Ingress Log")
        log.activity = activity
        log.crate = json.dumps(crate)
        log.result = json.dumps(result)
        log.raw_payload = json.dumps({"crate": crate, "activity": activity})
        log.save()
    except Exception as e:
        print(str(e))
    return result
