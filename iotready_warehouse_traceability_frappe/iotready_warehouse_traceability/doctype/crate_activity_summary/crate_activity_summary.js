const submit_summary = (frm) => {
  frappe.warn(
    "Please confirm details before submitting.",
    "",
    () => {
      frm.clear_custom_buttons();
      frm.call("enqueue_submit_summary").then(
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

frappe.ui.form.on("Crate Activity Summary", {
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
