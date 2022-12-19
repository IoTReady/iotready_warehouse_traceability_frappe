import os
import frappe
from pyqrcode import create as qrcreate
from io import BytesIO


def qrcode_as_png(qr_content, doctype=None, docname=None, is_private=True):
    qrcode = qrcreate(qr_content)
    fp = BytesIO()
    qrcode.png(fp, scale=8, module_color=[0, 0, 0, 180], background=[0xFF, 0xFF, 0xFF])
    folder = create_barcode_folder()
    attachment = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": "{}.png".format(docname or frappe.generate_hash(length=10)),
            "content": fp.getvalue(),
            "is_private": is_private,
            "decode": False,
            "folder": folder,
        }
    )
    if docname and doctype:
        attachment.attached_to_name = docname
        attachment.attached_to_doctype = doctype
    attachment.save()
    frappe.db.commit()
    return attachment.file_url


def create_barcode_folder():
    """Get Barcodes folder."""
    folder_name = "Barcodes"
    folder = frappe.db.exists("File", {"file_name": folder_name})
    if folder:
        return folder
    folder = frappe.get_doc(
        {"doctype": "File", "file_name": folder_name, "is_folder": 1, "folder": "Home"}
    )
    folder.insert(ignore_permissions=True)
    return folder.name
