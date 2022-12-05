from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in iotready_warehouse_traceability_frappe/__init__.py
from iotready_warehouse_traceability_frappe import __version__ as version

setup(
	name="iotready_warehouse_traceability_frappe",
	version=version,
	description="IoTReady Warehouse Traceability",
	author="IoTReady",
	author_email="hello@iotready.co",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
