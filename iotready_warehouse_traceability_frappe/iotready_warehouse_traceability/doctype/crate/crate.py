# Copyright (c) 2022, IoTReady and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from iotready_warehouse_traceability_frappe.qrcode import qrcode_as_png


class Crate(Document):
    # def before_insert(self):
    # self.generate_qrcode_image()

    @frappe.whitelist()
    def generate_qrcode_image(self, save=False):
        self.qrcode = qrcode_as_png(self.id, self.doctype, self.name)
        if save:
            self.save()
            frappe.db.commit()
        return True

    @property
    def last_procurement(self):
        if self.is_available_for_procurement:
            return None
        filters = {
            "crate_id": self.name,
            "activity": ["in", ["Procurement", "Crate Splitting"]],
        }
        last = frappe.db.get_all(
            "Crate Activity", filters=filters, fields=["name"], limit=1
        )
        if len(last) > 0:
            return last[0]["name"]

    @property
    def last_activity(self):
        if self.is_available_for_procurement:
            return None
        filters = {"crate_id": self.name, "status": "Completed"}
        last = frappe.db.get_all(
            "Crate Activity", filters=filters, fields=["name"], limit=1
        )
        if len(last) > 0:
            return last[0]["name"]

    @property
    def last_activity_type(self):
        if not self.last_activity:
            return None
        return frappe.db.get_value("Crate Activity", self.last_activity, "activity")

    @property
    def last_activity_timestamp(self):
        if not self.last_activity:
            return None
        return frappe.db.get_value("Crate Activity", self.last_activity, "creation")

    @property
    def purchase_receipt(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value(
            "Crate Activity", self.last_procurement, "reference_id"
        )

    @property
    def procured_grn_quantity(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value(
            "Crate Activity", self.last_procurement, "grn_quantity"
        )

    @property
    def procured_grn_quantity(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value(
            "Crate Activity", self.last_procurement, "grn_quantity"
        )

    @property
    def last_known_grn_quantity(self):
        if not self.last_activity:
            return None
        return frappe.db.get_value("Crate Activity", self.last_activity, "grn_quantity")

    @property
    def last_known_weight(self):
        if not self.last_activity:
            return None
        return frappe.db.get_value("Crate Activity", self.last_activity, "crate_weight")

    @property
    def last_known_warehouse(self):
        if not self.last_activity:
            return None
        if self.last_activity_type == "Transfer In":
            return frappe.db.get_value(
                "Crate Activity", self.last_activity, "target_warehouse"
            )
        else:
            return frappe.db.get_value(
                "Crate Activity", self.last_activity, "source_warehouse"
            )

    @property
    def item_code(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value("Crate Activity", self.last_procurement, "item_code")

    @property
    def item_name(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value("Crate Activity", self.last_procurement, "item_name")

    @property
    def stock_uom(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value("Crate Activity", self.last_procurement, "stock_uom")

    @property
    def supplier_id(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value(
            "Crate Activity", self.last_procurement, "supplier_id"
        )

    @property
    def supplier_name(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value(
            "Crate Activity", self.last_procurement, "supplier_name"
        )

    @property
    def procurement_timestamp(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value("Crate Activity", self.last_procurement, "creation")

    @property
    def procurement_warehouse_id(self):
        if not self.last_procurement:
            return None
        return frappe.db.get_value(
            "Crate Activity", self.last_procurement, "source_warehouse"
        )
