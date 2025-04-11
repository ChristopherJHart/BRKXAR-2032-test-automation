"""
Verify OSPF IPv4 Neighbors IP Addresses Test Job
-----------------------------------------------
This job file verifies that all OSPF IPv4 neighbors on the device
have the expected IP addresses.

Can run in two modes:
- learning: Learn current OSPF neighbor IP addresses and save to parameters JSON file
- testing: Verify OSPF neighbor IP addresses against saved parameters
"""

import logging

from pyats import aetest
from utils.adapters import TestbedAdapter
from utils.connectivity import (
    connect_to_testbed_devices,
    disconnect_from_testbed_devices,
    run_command_on_devices,
    verify_testbed_device_connectivity,
)
from utils.parameters import (
    load_parameters_from_file,
    save_parameters_to_file,
    validate_parameters_directory_exists,
)
from utils.reports import generate_job_report
from utils.types import ResultStatus, RunningMode

logger = logging.getLogger(__name__)

DESCRIPTION = (
    "The purpose of this test case is to validate the IP addresses of "
    "IPv4 OSPF neighbors on one or more IOS-XE devices. "
    "{% if parameters.keys()|list %}"
    "    The test will verify OSPF neighbor IP addresses on the following devices: "
    "{{ parameters.keys()|list|join(', ') }}. "
    "{% endif %}"
    "This verification ensures that each OSPF neighbor relationship is established with the expected "
    "IP address, which is critical for proper network operation.\n\n"
    "OSPF (Open Shortest Path First) is a link-state routing protocol that uses neighbor IP addresses "
    "to establish and maintain neighbor relationships. "
    "Verifying the OSPF neighbor IP addresses is important for ensuring network stability and "
    "security. Incorrect or unexpected IP addresses could indicate configuration errors, "
    "network topology changes, or potential security issues such as spoofing attacks. "
    "This test helps identify any discrepancies that could impact network performance or security."
)

SETUP = (
    "**Test Setup:**\n\n"
    "* All devices are connected as per the network topology.\n"
    "* All devices are powered up and operational.\n"
    "* SSH connectivity to the devices is established.\n"
    "* Authentication against the devices is successful.\n\n"
    "**Devices Under Test:**\n"
    "{% if parameters.keys() %}"
    "Connect to the following devices:\n"
    "{% for device in parameters.keys() %}"
    "* {{ device }}\n"
    "{% endfor %}"
    "{% else %}"
    "* All devices in the testbed\n"
    "{% endif %}\n\n"
    "**OSPF Neighbor IP Addresses to Verify:**\n"
    "{% for device, interfaces in parameters.items() %}"
    "* Device: {{ device }}\n"
    "{% for interface, interface_data in interfaces.items() %}"
    "  * Interface: {{ interface }}\n"
    "{% for neighbor_id, neighbor_data in interface_data.get('neighbors', {}).items() %}"
    "    * Neighbor Router ID: {{ neighbor_id }}\n"
    "    * Expected IP Address: {{ neighbor_data.get('address') }}\n"
    "{% endfor %}"
    "{% endfor %}"
    "{% endfor %}"
)

PROCEDURE = (
    "**Test Procedure:**\n\n"
    "1. Establish connections to all target devices:\n"
    "{% for device in parameters.keys() %}"
    "   * Connect to {{ device }}\n"
    "{% endfor %}\n"
    "2. Verify device connectivity to ensure all devices are accessible\n"
    "3. Execute 'show ip ospf neighbor' command on each device\n"
    "4. Parse the command output to extract the following information:\n"
    "   * Interface names with active OSPF adjacencies\n"
    "   * Neighbor Router IDs\n"
    "   * Neighbor IP Addresses\n"
    "5. For each device, compare the current OSPF neighbor IP addresses against expected parameters:\n"
    "{% for device, interfaces in parameters.items() %}"
    "   * Device {{ device }}:\n"
    "{% for interface, interface_data in interfaces.items() %}"
    "     * Interface {{ interface }}:\n"
    "{% for neighbor_id, neighbor_data in interface_data.get('neighbors', {}).items() %}"
    "       * Verify neighbor {{ neighbor_id }} has IP address \"{{ neighbor_data.get('address') }}\"\n"
    "{% endfor %}"
    "{% endfor %}"
    "{% endfor %}"
    "6. Record pass/fail results for each verification point\n"
    "7. Generate a comprehensive report of the verification results"
)

PASS_FAIL_CRITERIA = (
    "**Pass/Fail Criteria:**\n\n"
    "**This test passes when all of the following conditions are met:**\n"
    "1. SSH connectivity to each device is successful\n"
    "2. Authentication against each device is successful\n"
    "3. All expected OSPF interfaces are present on each device\n"
    "4. All expected OSPF neighbors are present on each interface\n"
    "5. Each OSPF neighbor has the correct IP address\n\n"
    "**This test fails if any of the following criteria are met:**\n"
    "1. One or more devices are unreachable over the network\n"
    "2. One or more devices are not responsive to SSH connections\n"
    "3. Authentication against one or more devices is unsuccessful\n"
    "4. An expected OSPF interface is missing on a device\n"
    "5. An expected OSPF neighbor is missing on an interface\n"
    "6. An OSPF neighbor has an incorrect IP address\n\n"
    "**Specific Verification Points:**\n"
    "{% for device, interfaces in parameters.items() %}"
    "* Device {{ device }}:\n"
    "{% for interface, interface_data in interfaces.items() %}"
    "  * Interface {{ interface }} must be present and running OSPF\n"
    "{% for neighbor_id, neighbor_data in interface_data.get('neighbors', {}).items() %}"
    "    * Neighbor {{ neighbor_id }} must be present\n"
    "    * Neighbor {{ neighbor_id }} must have IP address \"{{ neighbor_data.get('address') }}\"\n"
    "{% endfor %}"
    "{% endfor %}"
    "{% endfor %}"
)


class CommonSetup(aetest.CommonSetup):
    """Setup for script."""

    @aetest.subsection
    def connect_to_devices(self, testbed_adapter: TestbedAdapter):
        """Connect to all devices in the testbed."""
        connect_to_testbed_devices(testbed_adapter)

    @aetest.subsection
    def verify_connected(self, testbed_adapter: TestbedAdapter):
        """Verify that all devices are connected."""
        verify_testbed_device_connectivity(testbed_adapter, self.failed)

    @aetest.subsection
    def ensure_parameters_directory_exists(self):
        """Create parameters directory if it doesn't exist."""
        validate_parameters_directory_exists(self.failed)


class VerifyOSPFNeighborsIPAddresses(aetest.Testcase):
    """
    Verify OSPF IPv4 Neighbors IP Addresses
    """

    @aetest.setup
    def setup(self, mode: RunningMode):
        """
        Set test mode: learning or testing
        """
        self.mode = mode
        logger.info(f"Running in {self.mode} mode")

    def gather_current_state(self, testbed_adapter: TestbedAdapter) -> dict:
        """Gather the current state of each device."""
        all_devices_data = {}

        # Collect OSPF data from all devices using 'show ip ospf neighbor'
        parsed_data = run_command_on_devices(
            command="show ip ospf neighbor",
            testbed=testbed_adapter,
        )

        # Collect OSPF data from all devices
        for device in testbed_adapter.devices.values():
            execution_result = parsed_data.get(device.name)
            if execution_result is None:
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.FAILED,
                    message=f"No OSPF data found for device {device.name}",
                )
                self.failed(f"No OSPF data found for device {device.name}")
                continue

            data = execution_result.data

            # Check if there are any OSPF interfaces and neighbors
            if "interfaces" not in data or not data["interfaces"]:
                logger.warning(f"No OSPF interfaces found on {device.name}")
                all_devices_data[device.name] = {}
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.INFO,
                    message=f"No OSPF interfaces found on {device.name}",
                )
                continue

            # Process OSPF neighbors
            device_ospf_data = {}
            for interface_name, interface_data in data["interfaces"].items():
                if "neighbors" not in interface_data or not interface_data["neighbors"]:
                    continue

                if interface_name not in device_ospf_data:
                    device_ospf_data[interface_name] = {"neighbors": {}}

                # Process each neighbor
                for neighbor_id, neighbor_data in interface_data["neighbors"].items():
                    device_ospf_data[interface_name]["neighbors"][neighbor_id] = {
                        "address": neighbor_data.get("address", ""),
                    }
                    testbed_adapter.result_collector.add_result(
                        status=ResultStatus.INFO,
                        message=f"Found neighbor {neighbor_id} with IP {neighbor_data.get('address', '')}",
                    )

            all_devices_data[device.name] = device_ospf_data
            testbed_adapter.result_collector.add_result(
                status=ResultStatus.PASSED,
                message=f"Successfully gathered OSPF data from {device.name}",
            )

        return all_devices_data

    def compare_expected_parameters_to_current_state(
        self,
        current_state: dict,
        expected_parameters: dict,
        testbed_adapter: TestbedAdapter,
    ) -> None:
        """Compare the current state of each device to the expected parameters for each device."""
        logger.info("Validating current state of devices against expected parameters")
        for expected_device_name, expected_device_data in expected_parameters.items():
            logger.info("Checking current state of device %s", expected_device_name)
            if expected_device_name not in current_state:
                msg = (
                    f"Expected device {expected_device_name} not found in current state"
                )
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.FAILED, message=msg
                )
                self.failed(msg)
                continue

            logger.info(
                f"Found expected device {expected_device_name} in current state"
            )
            testbed_adapter.result_collector.add_result(
                status=ResultStatus.PASSED,
                message=f"Found expected device {expected_device_name} in current state",
            )

            # Compare each interface and neighbor
            for interface_name, interface_data in expected_device_data.items():
                logger.info(
                    "Checking current state of interface %s on device %s",
                    interface_name,
                    expected_device_name,
                )
                if interface_name not in current_state[expected_device_name]:
                    msg = (
                        f"Interface {interface_name} not found in current state for device "
                        f"{expected_device_name}"
                    )
                    testbed_adapter.result_collector.add_result(
                        status=ResultStatus.FAILED, message=msg
                    )
                    self.failed(msg)
                    continue

                logger.info(
                    f"Found expected interface {interface_name} in current state for device "
                    f"{expected_device_name}"
                )
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.PASSED,
                    message=f"Found expected interface {interface_name}",
                )

                expected_neighbors = interface_data.get("neighbors", {})
                actual_neighbors = current_state[expected_device_name][
                    interface_name
                ].get("neighbors", {})

                logger.info(
                    "Comparing %d expected neighbors against %d current neighbors for interface "
                    "%s on device %s",
                    len(expected_neighbors),
                    len(actual_neighbors),
                    interface_name,
                    expected_device_name,
                )
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.INFO,
                    message=f"Found {len(actual_neighbors)} neighbors, expecting {len(expected_neighbors)}",
                )

                # Compare each expected neighbor
                for neighbor_id, expected_neighbor_data in expected_neighbors.items():
                    logger.info(
                        "Checking current state of neighbor %s on interface %s of device %s",
                        neighbor_id,
                        interface_name,
                        expected_device_name,
                    )
                    if neighbor_id not in actual_neighbors:
                        msg = (
                            f"Neighbor {neighbor_id} on interface {interface_name} not found in "
                            f"current state for device {expected_device_name}"
                        )
                        testbed_adapter.result_collector.add_result(
                            status=ResultStatus.FAILED, message=msg
                        )
                        self.failed(msg)
                        continue

                    logger.info(
                        f"Found expected neighbor {neighbor_id} on interface {interface_name} "
                        f"for device {expected_device_name}"
                    )
                    current_neighbor_data = actual_neighbors[neighbor_id]
                    current_neighbor_address = current_neighbor_data.get("address")
                    expected_neighbor_address = expected_neighbor_data.get("address")

                    logger.info(
                        "Comparing current IP address '%s' of neighbor %s on interface %s of device %s "
                        "against expected IP address '%s'",
                        current_neighbor_address,
                        neighbor_id,
                        interface_name,
                        expected_device_name,
                        expected_neighbor_address,
                    )
                    if current_neighbor_address != expected_neighbor_address:
                        msg = (
                            f"The current IP address of neighbor {neighbor_id} on interface "
                            f"{interface_name} is {current_neighbor_address}, which does not match "
                            "the expected IP address of this neighbor which is "
                            f"{expected_neighbor_address}"
                        )
                        testbed_adapter.result_collector.add_result(
                            status=ResultStatus.FAILED, message=msg
                        )
                        self.failed(msg)
                    else:
                        logger.info(
                            f"The current IP address of neighbor {neighbor_id} on interface "
                            f"{interface_name} is {current_neighbor_address}, which matches the "
                            f"expected IP address of this neighbor which is {expected_neighbor_address}"
                        )
                        testbed_adapter.result_collector.add_result(
                            status=ResultStatus.PASSED,
                            message=f"Neighbor {neighbor_id} IP address matches expected: {current_neighbor_address}",
                        )

    @aetest.test
    def verify_ospf_neighbors_ip_addresses(
        self, testbed_adapter: TestbedAdapter, parameters_file
    ):
        """
        Learning mode: Learn OSPF neighbor IP addresses and save to parameters file
        Testing mode: Verify OSPF neighbor IP addresses against parameters file
        """
        current_state = self.gather_current_state(testbed_adapter)

        # LEARNING MODE: Save the collected data to parameters file
        if self.mode == "learning":
            if save_parameters_to_file(current_state, parameters_file):
                result_msg = "Successfully learned OSPF neighbor IP addresses and saved to parameters file"
                self.passed(result_msg)
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.PASSED, message=result_msg
                )
            else:
                result_msg = (
                    "Failed to save OSPF neighbor IP addresses to parameters file"
                )
                self.failed(result_msg)
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.FAILED, message=result_msg
                )
        # TESTING MODE: Verify against parameters file
        else:  # testing mode
            # Load expected parameters
            expected_parameters = load_parameters_from_file(parameters_file)
            testbed_adapter.parameters = expected_parameters
            if not expected_parameters:
                result_msg = "No expected parameters found. Run in learning mode first."
                self.failed(result_msg)
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.FAILED, message=result_msg
                )
                return

            logger.info("Comparing current state to expected parameters")
            try:
                self.compare_expected_parameters_to_current_state(
                    current_state, expected_parameters, testbed_adapter
                )
                result_msg = "All OSPF neighbor IP addresses on all devices verified successfully"
                self.passed(result_msg)
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.PASSED, message=result_msg
                )
            except Exception as e:
                result_msg = str(e)
                self.failed(result_msg)
                testbed_adapter.result_collector.add_result(
                    status=ResultStatus.FAILED, message=result_msg
                )


class CommonCleanup(aetest.CommonCleanup):
    """Cleanup for script."""

    @aetest.subsection
    def add_results_to_report(self, testbed_adapter: TestbedAdapter, mode):
        """Add accumulated results to the HTML report."""
        if mode == RunningMode.TESTING:
            generate_job_report(
                task_id="ospf_neighbors_ip_addresses_detailed",
                title="OSPF IPv4 Neighbors IP Addresses",
                description=DESCRIPTION,
                setup=SETUP,
                procedure=PROCEDURE,
                pass_fail_criteria=PASS_FAIL_CRITERIA,
                results=testbed_adapter.result_collector.results,
                status=testbed_adapter.result_collector.status,
                parameters=testbed_adapter.parameters,
            )

    @aetest.subsection
    def disconnect_from_devices(self, testbed_adapter: TestbedAdapter):
        """Disconnect from all devices in the testbed."""
        disconnect_from_testbed_devices(testbed_adapter)
