# Copyright (c) 2022, IoTReady and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from iotready_warehouse_traceability_frappe import utils
from datetime import datetime


class CrateActivity(Document):
    def before_insert(self):
        self.set_capture_mode()
        self.maybe_update_quantities()
        self.maybe_create_activity_summary()

    def on_trash(self):
        assert (
            not self.status == "Completed"
        ), "Activity cannot be deleted after submission."

    def set_capture_mode(self):
        if self.crate_weight:
            self.capture_mode = "Weight"
        else:
            self.capture_mode = "Scan"

    def maybe_create_activity_summary(self):
        if not self.activity in ["Procurement", "Transfer Out", "Transfer In"]:
            return
        filters = {
            "source_warehouse": self.source_warehouse,
            "target_warehouse": self.target_warehouse,
            "activity": self.activity,
            "status": "Draft",
            "vehicle": self.vehicle or ["is", "not set"],
            "supplier_id": self.supplier_id or ["is", "not set"],
            "creation": [">=", datetime.now().date()],
        }
        existing = frappe.get_all(
            "Crate Activity Summary",
            filters=filters,
            fields=["reference_id", "creation"],
        )
        if len(existing) == 0:
            doc = frappe.new_doc("Crate Activity Summary")
            doc.source_warehouse = self.source_warehouse
            doc.target_warehouse = self.target_warehouse
            doc.activity = self.activity
            doc.status = "Draft"
            doc.vehicle = self.vehicle
            doc.supplier_id = self.supplier_id
            doc.save()
            self.reference_id = doc.reference_id
        else:
            self.reference_id = existing[0]["reference_id"]
            # print("using existing reference_id", self.reference_id)

    def maybe_update_quantities(self):
        if self.activity in [
            "Procurement",
            "Crate Splitting",
        ]:
            return
        crate = frappe.get_doc("Crate", self.crate_id)
        self.item_code = crate.item_code
        self.item_name = crate.item_name
        self.supplier_id = crate.supplier_id
        self.supplier_name = crate.supplier_name
        self.stock_uom = crate.stock_uom
        if self.activity in ["Delete"]:
            return
        if not self.source_warehouse and self.activity == "Transfer In":
            self.source_warehouse = crate.last_known_warehouse
        if (
            self.crate_weight
            and crate.stock_uom
            and crate.stock_uom.lower() not in ["nos", "pcs"]
        ):
            enable_cycle_count = frappe.db.get_single_value(
                "IoTReady Traceability Settings", "enable_cycle_count"
            )
            if not enable_cycle_count:
                return
            # Do a cycle count here
            if self.crate_weight < crate.procured_grn_quantity:
                self.actual_loss = crate.procured_grn_quantity - self.crate_weight
                if crate.last_known_weight > crate.procured_grn_quantity:
                    self.moisture_loss = (
                        crate.last_known_weight - crate.procured_grn_quantity
                    )
                else:
                    self.moisture_loss = 0
                self.grn_quantity = self.crate_weight
            elif self.crate_weight < crate.last_known_weight:
                self.moisture_loss = crate.last_known_weight - self.crate_weight
                self.grn_quantity = crate.procured_grn_quantity
            elif self.crate_weight > crate.last_known_weight:
                self.excess_weight = self.crate_weight - crate.last_known_weight
                self.grn_quantity = self.crate_weight
        else:
            self.crate_weight = crate.last_known_weight
        if not self.grn_quantity:
            self.grn_quantity = crate.last_known_grn_quantity
