frappe.listview_settings["Crate Activity"] = {
  hide_name_column: true,
  onload: function (listview) {
    listview.page.add_actions_menu_item("Release Crates", () => {
      const docnames = cur_list.get_checked_items().map((item) => item.name);
      frappe.call({
        method: "iotready_warehouse_traceability_frappe.utils.release_crates",
        type: "POST",
        args: {
          docnames,
        },
        callback: (r) => {
          console.log(r);
          if (r.exc) {
            frappe.throw(r.exc);
          }
        },
        freeze: true,
        freeze_message: "Please wait...",
        async: true,
      });
    });
  },
};
