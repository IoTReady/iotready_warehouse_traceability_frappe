// Copyright (c) 2022, IoTReady and contributors
// For license information, please see license.txt

const generate_qrcode_image = (frm) => {
  frm.call("generate_qrcode_image", { save: true }).then((r) => {
    if (r.message) {
      console.log(r.message);
      if (r.message) {
        frm.reload_doc();
      }
      // frappe.msgprint(r.message);
    }
  });
};

frappe.ui.form.on("Crate", {
  refresh: function (frm) {
    frm.add_custom_button("Generate QRCode Image", () => {
      generate_qrcode_image(frm);
      if (frappe.user_roles.includes("System Manager")) {
        frm.toggle_enable(['is_available_for_procurement', 'available_at'], 1);
      }
    });
  },
});
