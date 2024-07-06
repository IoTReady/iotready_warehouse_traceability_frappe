# Copyright (c) 2022, IoTReady and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from datetime import datetime
from iotready_warehouse_traceability_frappe import utils


@frappe.whitelist(allow_guest=False)
def merge_duplicate_summaries(docnames):
    if isinstance(docnames, str):
        docnames = json.loads(docnames)
    elif not isinstance(docnames, list):
        frappe.throw("Invalid document list received")
    docs = [frappe.get_doc("Crate Activity Summary", docname) for docname in docnames]
    source_warehouses = {doc.source_warehouse for doc in docs if doc.source_warehouse}
    target_warehouses = {doc.target_warehouse for doc in docs if doc.target_warehouse}
    suppliers = {doc.supplier_id for doc in docs if doc.supplier_id}
    dates = {doc.creation.date() for doc in docs}
    statuses = {doc.status for doc in docs}
    activities = {doc.activity for doc in docs}
    if len(activities) > 1:
        frappe.throw("Documents belong to more than 1 activity.")
    if len(source_warehouses) > 1:
        frappe.throw("Documents belong to more than 1 source warehouse.")
    if len(target_warehouses) > 1:
        frappe.throw("Documents belong to more than 1 target warehouse.")
    if len(suppliers) > 1:
        frappe.throw("Documents belong to more than 1 supplier.")
    if len(dates) > 1:
        frappe.throw("Documents belong to more than 1 date.")
    if "Completed" in statuses:
        frappe.throw("Documents cannot be merged once completed.")
    primary = docs[0]
    for doc in docs[1:]:
        crates = json.loads(doc.crates)
        for crate in crates:
            frappe.db.set_value(
                "Crate Activity", crate["name"], "reference_id", primary.reference_id
            )
        frappe.delete_doc(
            "Crate Activity Summary",
            doc.name,
            delete_permanently=False,
            ignore_on_trash=True,
            for_reload=True,
        )
    frappe.db.commit()


class CrateActivitySummary(Document):
    @property
    def number_of_crates(self):
        return len(json.loads(self.crates))

    @property
    def crates(self):
        crates = utils.activity_crates(
            source_warehouse=self.source_warehouse,
            target_warehouse=self.target_warehouse,
            activity=self.activity,
            status=self.status,
            reference_id=self.reference_id,
        )
        return json.dumps(crates)

    @property
    def items(self):
        crates = json.loads(self.crates)
        return json.dumps(utils.crates_to_items(crates))

    @frappe.whitelist()
    def enqueue_submit_summary(self):
        frappe.enqueue(
            self.submit_summary,
            queue="long",
            timeout=300,
        )
        return "This document will be submitted in the background. Please check again in about 5 minutes."

    @frappe.whitelist()
    def submit_summary(self):
        # Create a copy because self.crates is evaluated again as soon as GRN is done.
        # We use this copy to update the GRN in set_crates_grn
        # self.maybe_submit_to_wms()
        crates = self.crates
        prefix = self.activity.lower().replace(" ", "_")
        hook = frappe.db.get_single_value(
            "IoTReady Traceability Settings", f"{prefix}_submit_hook"
        )
        try:
            if hook:
                frappe.get_attr(hook)(self)
            self.set_crates_completed(crates)
            self.reload()
            self.status = "Completed"
            self.error_message = ""
            self.save()
            # frappe.db.commit()
        except Exception as e:
            self.reload()
            self.error_message = str(e)
            self.save()
            # frappe.db.commit()
            return "Error!"
        return "Submitted"

    def before_insert(self):
        self.set_date()
        self.set_reference_id()

    def on_trash(self):
        assert (
            self.status != "Completed"
        ), "Activity Summary cannot be deleted after completion."
        crates = json.loads(self.crates)
        for row in crates:
            if not row["status"] == "Completed":
                frappe.delete_doc_if_exists("Crate Activity", row["name"])

    def set_reference_id(self):
        self.reference_id = frappe.generate_hash()[-10:]

    def set_date(self):
        self.date = datetime.now().date()

    def set_crates_completed(self, crates):
        crates = json.loads(crates)
        for row in crates:
            if self.activity in ["Procurement", "Crate Splitting"]:
                utils.set_crate_availability(row["crate_id"], False)
                utils.set_crate_available_at(row["crate_id"], None)
            # Do a save so that maybe_release_crate is triggered
            crate_activity = frappe.get_doc("Crate Activity", row["name"])
            crate_activity.status = "Completed"
            crate_activity.save()

    @frappe.whitelist()
    def maybe_submit_to_wms(self):
        # Create a copy because self.crates is evaluated again as soon as WMS submission is done is done.
        # We use this copy to update the acknowledgemen_id in set_crates_wms_acknowledgement
        crates = self.crates
        msg = "Done"
        self.set_crates_wms_acknowledgement(crates)
        return msg

    def set_crates_wms_acknowledgement(self, crates):
        crates = json.loads(crates)
        for row in crates:
            frappe.db.set_value(
                "Crate Activity",
                row["name"],
                "wms_acknowledgement_id",
                self.wms_acknowledgement_id,
            )

    @frappe.whitelist()
    def get_sku_table(self):
        hook = frappe.db.get_single_value(
            "IoTReady Traceability Settings", "sku_table_hook"
        )
        if hook:
            return frappe.get_attr(hook)(self)
        else:
            return utils.get_sku_table(
                items=json.loads(self.items), activity=self.activity
            )

    @frappe.whitelist()
    def get_crate_table(self):
        is_editable = self.status == "Draft"
        hook = frappe.db.get_single_value(
            "IoTReady Traceability Settings", "crate_table_hook"
        )
        if hook:
            return frappe.get_attr(hook)(self)
        else:
            return utils.get_crate_table(
                crates=json.loads(self.crates),
                activity=self.activity,
                is_editable=is_editable,
            )

    @frappe.whitelist()
    def delete_crate(self, crate_id):
        return utils.delete_draft_crate_activities(crate_id)
