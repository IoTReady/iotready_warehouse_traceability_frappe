// Copyright (c) 2022, IoTReady and contributors
// For license information, please see license.txt

const submit_summary = (frm) => {
  frappe.db
    .get_value("WMS Settings", "WMS Settings", "enable_wms_integration")
    .then((r) => {
      const message =
        `<p>WMS integration is currently: ${
          Number(r.message.enable_wms_integration) === 1
            ? "enabled"
            : "disabled"
        }</p>` +
        `<br/>` +
        `<p>Quantities will be submitted as displayed in the table below.</p>`;
      frappe.warn(
        "Please confirm details before submitting.",
        message,
        () => {
          frm.clear_custom_buttons();
          frm.call("submit_summary").then(
            (r) => {
              if (r.exc) {
                console.error("error", r.exc);
                frappe.throw(r.exc);
                frm.refresh();
              } else if (r.message) {
                frappe.msgprint(r.message);
                frm.refresh();
              }
            },
            () => {
              frm.refresh();
            }
          );
          frappe.msgprint("Please wait...");
        },
        () => {}
      );
    });
};

const show_submit_button = (frm) => {
  frm.add_custom_button("Submit Summary", () => {
    submit_summary(frm);
  });
};

const show_refresh_button = (frm) => {
  frm.add_custom_button("Refresh", () => {
    frm.reload_doc();
  });
};

frappe.ui.form.on("Activity Summary", {
  refresh: function (frm) {
    frm.disable_save();
    if (!frm.is_new() && !(frm.doc.status == "Completed")) {
      show_submit_button(frm);
      show_refresh_button(frm);
    }
    if (!frm.is_new()) {
      const el = $('*[data-fieldname="sku_table"]');
      frm.call("get_sku_table").then((r) => {
        if (r.exc) {
          console.error("error", r.exc);
        } else {
          el.html(r.message);
        }
      });
      const el2 = $('*[data-fieldname="crate_table"]');
      frm.call("get_crate_table").then((r) => {
        if (r.exc) {
          console.error("error", r.exc);
        } else {
          el2.html(r.message);
        }
      });
    }
  },
});
