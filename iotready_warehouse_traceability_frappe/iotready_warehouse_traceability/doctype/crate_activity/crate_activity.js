// Copyright (c) 2022, IoTReady and contributors
// For license information, please see license.txt

frappe.ui.form.on("Crate Activity", {
  refresh: function (frm) {
    frm.disable_save();
  },
});
