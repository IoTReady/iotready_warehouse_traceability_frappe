import json
import requests
from joblib import Parallel, delayed

usr = "cc@iotready.co"
pwd = "iotready"
# usr = "tej@iotready.co"
# pwd = "godesi2702"

base_url = "http://localhost:8000"
# base_url = "https://godesi-dev.frappe.cloud"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

batch_prefix = "GP22-IO-TR-A"

session = requests.Session()


def login():
    url = f"{base_url}/api/method/login"
    payload = json.dumps({"usr": usr, "pwd": pwd})
    response = session.post(url, headers=headers, data=payload)
    print(response.text)


def generate_crates(count=1000):
    crates = []
    for i in range(0, count):
        crates.append(f"{batch_prefix}{str(i).zfill(4)}")
    return crates


def get_configuration():
    url = f"{base_url}/api/method/iotready_warehouse_traceability_frappe.api.get_configuration"
    response = session.get(url, headers=headers)
    print(response.text)


def record_events(crate: dict, activity: str):
    url = f"{base_url}/api/method/iotready_warehouse_traceability_frappe.api.record_events"
    payload = json.dumps({"crate": crate, "activity": activity})
    response = session.post(url, headers=headers, data=payload)
    print(response.text)


def procure_crate(crate_id):
    print(crate_id)
    crate = {
        "crate_id": crate_id,
        "item_code": "Imli Pop 1",
        "stock_uom": "PCS",
        "quantity": 20,
        "weight": 10,
        "isFinal": True,
        "supplier": "SIRA 1",
    }
    record_events(crate, "Procurement")


def transfer_out_crate(crate_id):
    print(crate_id)
    crate = {
        "crate_id": crate_id,
        "target_warehouse": "Goods In Transit - GD",
        "vehicle": "DUMMY",
        "weight": 19.5,
    }
    record_events(crate, "Transfer Out")


def transfer_in_crate(crate_id):
    crate = {
        "crate_id": crate_id,
    }
    record_events(crate, "Transfer In")


def delete_crate(crate_id):
    crate = {
        "crate_id": crate_id,
    }
    record_events(crate, "Delete")


def cycle_count_crate(crate_id):
    crate = {"crate_id": crate_id, "weight": 22}
    record_events(crate, "Cycle Count")


def identify_crate(crate_id):
    crate = {"crate_id": crate_id, "weight": 18}
    record_events(crate, "Identify")


def split_crate(crate_id):
    crate = {
        "crate_id": crate_id,
        "quantity": 2.0,
        "weight": 2.0,
        "parent_crate_id": "GP22-IO-TR-D0024",
    }
    record_events(crate, "Crate Splitting")


if __name__ == "__main__":
    login()
    get_configuration()
    crates = generate_crates(count=1)
    # print(crates)
    # Procure crates
    for crate_id in crates:
        print(crate_id)
        # procure_crate(crate_id)
        # transfer_out_crate(crate_id)
        # transfer_in_crate(crate_id)
        delete_crate(crate_id)
    # cycle_count_crate(crate_id)
    # identify_crate(crate_id)
    # split_crate(crate_id)
    # Parallel(n_jobs=8)(delayed(procure_crate)(crate) for crate in crates)
