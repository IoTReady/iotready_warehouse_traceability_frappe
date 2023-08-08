# Copyright (c) 2022, IoTReady and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from datetime import datetime
from iotready_warehouse_traceability_frappe import utils


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
        self.maybe_submit_to_wms()
        crates = self.crates
        self.set_crates_completed(crates)
        self.status = "Completed"
        prefix = self.activity.lower().replace(" ", "_")
        hook = frappe.db.get_single_value(
            "IoTReady Traceability Settings", f"{prefix}_submit_hook"
        )
        if hook:
            frappe.get_attr(hook)(self)
        self.save()
        frappe.db.commit()
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
