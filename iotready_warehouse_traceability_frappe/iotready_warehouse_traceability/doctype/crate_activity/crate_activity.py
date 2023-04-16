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
            self.procured_grn_quantity = self.grn_quantity
            self.procured_crate_weight = self.crate_weight
            self.procurement_warehouse = self.source_warehouse
            return
        crate = frappe.get_doc("Crate", self.crate_id)
        self.procurement_warehouse = crate.procurement_warehouse_id
        self.procurement_warehouse_name = crate.procurement_warehouse_name
        self.procured_grn_quantity = crate.procured_grn_quantity
        self.procured_crate_weight = crate.procured_crate_weight
        self.last_known_grn_quantity = crate.last_known_grn_quantity
        self.last_known_crate_weight = crate.last_known_weight
        self.item_code = crate.item_code
        self.item_name = crate.item_name
        self.supplier_id = crate.supplier_id
        self.supplier_name = crate.supplier_name
        self.stock_uom = crate.stock_uom
        if self.activity in ["Delete"]:
            return
        if not self.source_warehouse and self.activity == "Transfer In":
            self.source_warehouse = crate.last_known_warehouse
        enable_cycle_count = frappe.db.get_single_value(
            "IoTReady Traceability Settings", "enable_cycle_count"
        )
        if not enable_cycle_count:
            self.grn_quantity = crate.last_known_grn_quantity
            if not self.crate_weight:
                self.crate_weight = crate.last_known_weight
            return
        enable_cycle_count_for_pieces = frappe.db.get_single_value(
            "IoTReady Traceability Settings", "enable_cycle_count_for_pieces"
        )
        if (
            not enable_cycle_count_for_pieces
            and crate.stock_uom
            and crate.stock_uom.lower() in ["nos", "pcs"]
        ):
            # use the last known values
            self.grn_quantity = crate.last_known_grn_quantity
            if not self.crate_weight:
                self.crate_weight = crate.last_known_weight
            return
        if not self.crate_weight:
            # scan based TO/TI
            # use the last known values
            self.grn_quantity = crate.last_known_grn_quantity
            self.crate_weight = crate.last_known_weight
            return
        # Incoming should always be >= outgoing (at aggregate level)
        # Accounting should be based on either GRN quantity or crate weight - not a mix n match
        # https://docs.google.com/spreadsheets/d/1Oy1RXQb8nzCwtrbiRE5-vdQiVBGw8M3ZDZAzKEP3ZdA/edit?usp=sharing

        enable_moisture_loss_calculation = frappe.db.get_single_value(
            "IoTReady Traceability Settings", "enable_moisture_loss_calculation"
        )
        if enable_moisture_loss_calculation:
            moisture_loss_allocation = (
                crate.procured_crate_weight - crate.procured_grn_quantity
            )
        else:
            moisture_loss_allocation = 0
        if self.crate_weight < crate.last_known_weight:
            loss = crate.last_known_weight - self.crate_weight
            if self.crate_weight > crate.procured_crate_weight:
                self.grn_quantity = utils.normal_round(
                    max(
                        self.crate_weight - moisture_loss_allocation,
                        crate.procured_grn_quantity,
                    ),
                    3,
                )
                if enable_moisture_loss_calculation:
                    self.moisture_loss = utils.normal_round(loss, 3)
                    self.actual_loss = 0
                else:
                    self.moisture_loss = 0
                    self.actual_loss = utils.normal_round(loss, 3)
            else:
                self.grn_quantity = utils.normal_round(self.crate_weight, 3)
                if loss > moisture_loss_allocation:
                    self.actual_loss = utils.normal_round(
                        loss - moisture_loss_allocation, 3
                    )
                    self.moisture_loss = utils.normal_round(moisture_loss_allocation, 3)
                else:
                    if enable_moisture_loss_calculation:
                        self.moisture_loss = utils.normal_round(loss, 3)
                        self.actual_loss = 0
                    else:
                        self.moisture_loss = 0
                        self.actual_loss = utils.normal_round(loss, 3)
        else:
            excess = self.crate_weight - crate.last_known_weight
            self.grn_quantity = utils.normal_round(
                max(
                    self.crate_weight - moisture_loss_allocation,
                    crate.procured_grn_quantity,
                ),
                3,
            )
            self.excess_weight = utils.normal_round(excess, 3)
            self.moisture_loss = 0
            self.actual_loss = 0

        # Fallback defaults
        # use the last known values
        if not self.crate_weight:
            self.crate_weight = crate.last_known_weight
        if not self.grn_quantity:
            self.grn_quantity = crate.last_known_grn_quantity
        return
