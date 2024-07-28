frappe.listview_settings["Crate Activity Summary"] = {
  hide_name_column: true,
  onload: function(listview) {
    listview.page.add_actions_menu_item("Merge", () => {
      const docnames = cur_list.get_checked_items().map((item) => item.name);
      frappe.call({
        method: "iotready_warehouse_traceability_frappe.iotready_warehouse_traceability.doctype.crate_activity_summary.crate_activity_summary.merge_duplicate_summaries",
        type: "POST",
        args: {
          docnames,
        },
        callback: (r) => {
          console.log(r);
          if (r.exc) {
            frappe.throw(r.exc);
          } else {
            window.location.reload();
          }
        },
        freeze: true,
        freeze_message: "Please wait...",
        async: true,
      });
    });
  }
};
