"""
Verify OSPF IPv4 Neighbors Status Test Job
-----------------------------------------
This job file verifies that all OSPF IPv4 neighbors on the device
have a state containing "FULL".

Can run in two modes:
- learning: Learn current OSPF neighbors and save to parameters JSON file
- testing: Verify OSPF neighbors against saved parameters
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
from utils.types import RunningMode

logger = logging.getLogger(__name__)


DESCRIPTION = (
    "The purpose of this test case is to validate the adjacency status of "
    "IPv4 OSPF neighbors on one or more IOS-XE devices. "
    "{% if parameters.keys()|list %}"
    "    The test will verify OSPF neighbors on the following devices: "
    "{{ parameters.keys()|list|join(', ') }}. "
    "{% endif %}"
    "This verification ensures that each OSPF neighbor relationship is in the expected state, "
    "primarily focusing on FULL adjacencies.\n\n"
    "OSPF (Open Shortest Path First) is a link-state routing protocol that requires neighbors to "
    "establish and maintain adjacencies for proper routing information exchange. "
    "Verifying the OSPF neighbor adjacency status is critical for ensuring network stability and "
    "proper control plane operation. "
    "Failed or improper adjacencies can lead to routing inconsistencies, suboptimal paths, "
    "or network outages. "
    "This test helps identify potential OSPF relationship issues that could impact network performance."
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
    "**OSPF Neighbor Relationships to Verify:**\n"
    "{% for device, interfaces in parameters.items() %}"
    "* Device: {{ device }}\n"
    "{% for interface, interface_data in interfaces.items() %}"
    "  * Interface: {{ interface }}\n"
    "{% for neighbor_id, neighbor_data in interface_data.get('neighbors', {}).items() %}"
    "    * Neighbor Router ID: {{ neighbor_id }}\n"
    "    * Expected State: {{ neighbor_data.get('state') }}\n"
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
    "   * Current neighbor state (e.g., FULL/DR, FULL/BDR)\n"
    "5. For each device, compare the current OSPF neighbor information against expected parameters:\n"
    "{% for device, interfaces in parameters.items() %}"
    "   * Device {{ device }}:\n"
    "{% for interface, interface_data in interfaces.items() %}"
    "     * Interface {{ interface }}:\n"
    "{% for neighbor_id, neighbor_data in interface_data.get('neighbors', {}).items() %}"
    "       * Verify neighbor {{ neighbor_id }} is in state \"{{ neighbor_data.get('state') }}\"\n"
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
    "5. Each OSPF neighbor is in the expected state (e.g., FULL/DR, FULL/BDR)\n\n"
    "**This test fails if any of the following criteria are met:**\n"
    "1. One or more devices are unreachable over the network\n"
    "2. One or more devices are not responsive to SSH connections\n"
    "3. Authentication against one or more devices is unsuccessful\n"
    "4. An expected OSPF interface is missing on a device\n"
    "5. An expected OSPF neighbor is missing on an interface\n"
    "6. An OSPF neighbor is in an incorrect state (e.g., expected FULL/DR but found INIT)\n\n"
    "**Specific Verification Points:**\n"
    "{% for device, interfaces in parameters.items() %}"
    "* Device {{ device }}:\n"
    "{% for interface, interface_data in interfaces.items() %}"
    "  * Interface {{ interface }} must be present and running OSPF\n"
    "{% for neighbor_id, neighbor_data in interface_data.get('neighbors', {}).items() %}"
    "    * Neighbor {{ neighbor_id }} must be present\n"
    "    * Neighbor {{ neighbor_id }} must be in state \"{{ neighbor_data.get('state') }}\"\n"
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


class VerifyOSPFNeighborsStatus(aetest.Testcase):
    """
    Verify OSPF IPv4 Neighbors Status
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

        # Collect OSPF data from all devices
        parsed_data = run_command_on_devices(
            command="show ip ospf neighbor",
            testbed=testbed_adapter,
        )

        # Collect OSPF data from all devices
        for device in testbed_adapter.devices.values():
            execution_result = parsed_data.get(device.name)
            if execution_result is None:
                self.failed(f"No OSPF data found for device {device.name}")
                continue

            data = execution_result.data

            # Check if there are any OSPF interfaces and neighbors
            if "interfaces" not in data or not data["interfaces"]:
                logger.warning(f"No OSPF interfaces found on {device.name}")
                all_devices_data[device.name] = {}
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
                        "state": neighbor_data.get("state", ""),
                    }

            all_devices_data[device.name] = device_ospf_data

        return all_devices_data

    def compare_expected_parameters_to_current_state(
        self, current_state: dict, expected_parameters: dict
    ) -> None:
        """Compare the current state of each device to the expected parameters for each device."""
        logger.info("Validating current state of devices against expected parameters")
        for expected_device_name, expected_device_data in expected_parameters.items():
            logger.info("Checking current state of device %s", expected_device_name)
            if expected_device_name not in current_state:
                self.failed(
                    f"Expected device {expected_device_name} not found in current state"
                )
                continue

            logger.info(
                f"Found expected device {expected_device_name} in current state"
            )

            # Compare each interface and neighbor
            for interface_name, interface_data in expected_device_data.items():
                logger.info(
                    "Checking current state of interface %s on device %s",
                    interface_name,
                    expected_device_name,
                )
                if interface_name not in current_state[expected_device_name]:
                    self.failed(
                        f"Interface {interface_name} not found in current state for device "
                        f"{expected_device_name}"
                    )
                    continue

                logger.info(
                    f"Found expected interface {interface_name} in current state for device "
                    f"{expected_device_name}"
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

                # Compare each expected neighbor
                for neighbor_id, expected_neighbor_data in expected_neighbors.items():
                    logger.info(
                        "Checking current state of neighbor %s on interface %s of device %s",
                        neighbor_id,
                        interface_name,
                        expected_device_name,
                    )
                    if neighbor_id not in actual_neighbors:
                        self.failed(
                            f"Neighbor {neighbor_id} on interface {interface_name} not found in "
                            f"current state for device {expected_device_name}"
                        )
                        continue

                    logger.info(
                        f"Found expected neighbor {neighbor_id} on interface {interface_name} "
                        f"for device {expected_device_name}"
                    )

                    current_neighbor_data = actual_neighbors[neighbor_id]
                    current_neighbor_state = current_neighbor_data.get("state")
                    expected_neighbor_state = expected_neighbor_data.get("state")
                    logger.info(
                        "Comparing current state '%s' of neighbor %s on interface %s of device %s "
                        "against expected state '%s'",
                        current_neighbor_state,
                        neighbor_id,
                        interface_name,
                        expected_device_name,
                        expected_neighbor_state,
                    )
                    if current_neighbor_state != expected_neighbor_state:
                        self.failed(
                            f"The current state of neighbor {neighbor_id} on interface "
                            f"{interface_name} is {current_neighbor_state}, which does not match "
                            "the expected state of this neighbor which is "
                            f"{expected_neighbor_state}"
                        )
                    else:
                        logger.info(
                            f"The current state of neighbor {neighbor_id} on interface "
                            f"{interface_name} is {current_neighbor_state}, which matches the "
                            f"expected state of this neighbor which is {expected_neighbor_state}"
                        )

    @aetest.test
    def verify_ospf_neighbors_status(
        self, testbed_adapter: TestbedAdapter, parameters_file
    ):
        """
        Learning mode: Learn OSPF neighbors and save to parameters file
        Testing mode: Verify OSPF neighbors against parameters file
        """
        current_state = self.gather_current_state(testbed_adapter)

        # LEARNING MODE: Save the collected data to parameters file
        if self.mode == "learning":
            if save_parameters_to_file(current_state, parameters_file):
                self.passed(
                    "Successfully learned OSPF neighbors and saved to parameters file"
                )
            else:
                self.failed("Failed to save OSPF neighbors to parameters file")

        # TESTING MODE: Verify against parameters file
        else:  # testing mode
            # Load expected parameters
            expected_parameters = load_parameters_from_file(parameters_file)

            if not expected_parameters:
                self.failed("No expected parameters found. Run in learning mode first.")
                return

            logger.info("Comparing current state to expected parameters")
            self.compare_expected_parameters_to_current_state(
                current_state, expected_parameters
            )

            # If we get here without failing, all devices passed
            self.passed("All OSPF neighbors on all devices verified successfully")


class CommonCleanup(aetest.CommonCleanup):
    """Cleanup for script."""

    @aetest.subsection
    def disconnect_from_devices(self, testbed_adapter: TestbedAdapter):
        """Disconnect from all devices in the testbed."""
        disconnect_from_testbed_devices(testbed_adapter)
