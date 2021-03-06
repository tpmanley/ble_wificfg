import time
import logging
from bgapi.bgmodule import BlueGigaServer
from bgapi.cmd_def import connection_status_mask

UUIDS = {"ACTIONS": "\x00\x01\x00\x00\x00\x00\xF0\x00\xF0\x00\xF0\x00\x00\x00\x00\x00"[::-1],
         "SSID": "\x00\x02\x00\x00\x00\x00\xF0\x00\xF0\x00\xF0\x00\x00\x00\x00\x00"[::-1],
         "PSK": "\x00\x03\x00\x00\x00\x00\xF0\x00\xF0\x00\xF0\x00\x00\x00\x00\x00"[::-1],
         "USERNAME":"\x00\x04\x00\x00\x00\x00\xF0\x00\xF0\x00\xF0\x00\x00\x00\x00\x00"[::-1],
         "PASSWORD":"\x00\x05\x00\x00\x00\x00\xF0\x00\xF0\x00\xF0\x00\x00\x00\x00\x00"[::-1],
         "ETH0_IP":"\x00\x06\x00\x00\x00\x00\xF0\x00\xF0\x00\xF0\x00\x00\x00\x00\x00"[::-1],
         "WLAN0_IP":"\x00\x07\x00\x00\x00\x00\xF0\x00\xF0\x00\xF0\x00\x00\x00\x00\x00"[::-1]}


class WifiCfgServer(BlueGigaServer):
    def __init__(self, port, baud, timeout):
        super(WifiCfgServer, self).__init__(port, baud, timeout)
        self.pipe_logs_to_terminal()
        self.connected = False
        self.app_handles = {}
        for key, handle in UUIDS.iteritems():
            self.app_handles[key] = None
        self.reset_ble_state()
        for handle in range(0xFFFF):
            type = self.read_type(handle)
            for key, uuid in UUIDS.iteritems():
                if uuid == type:
                    print("Found %s at %d" % (key, handle))
                    self.app_handles[key] = handle
                    self.read_by_handle(handle=handle, offset=0, timeout=1)
                    break
            for key, key_handle in self.app_handles.iteritems():
                if not key_handle:
                    break
            else:
                break
        else:
            raise Exception("Incorrect BLE112 Firmware! Could not find all required UUIDs for this application!")

    def ble_evt_attributes_value(self, connection, reason, handle, offset, value):
        super(WifiCfgServer, self).ble_evt_attributes_value(connection, reason, handle, offset, value)
        if handle == self.app_handles["ACTIONS"]:
            self.write_attribute(self.app_handles["ACTIONS"], offset=0, value="\x00"*20, timeout=1)
            self.associate_wlan0(self.handle_values[self.app_handles["SSID"]],
                                 self.handle_values[self.app_handles["PSK"]],
                                 self.handle_values[self.app_handles["USERNAME"]],
                                 self.handle_values[self.app_handles["PASSWORD"]])

    def ble_evt_connection_status(self, connection, flags, address, address_type, conn_interval, timeout, latency, bonding):
        super(WifiCfgServer, self).ble_evt_connection_status(connection, flags, address, address_type, conn_interval, timeout, latency, bonding)
        if flags & connection_status_mask["connection_connected"]:
            self.connected = True

    def ble_evt_connection_disconnected(self, connection, reason):
        super(WifiCfgServer, self).ble_evt_connection_disconnected(connection, reason)
        self.connected = False

    def associate_wlan0(self, ssid, psk, username, password):
        print("Associate WLAN0 - SSID:%s - PSK:%s - USER:%s - PASS:%s" % (ssid, psk, username, "x"*len(password)))
        self.write_attribute(self.app_handles["ETH0_IP"], get_eth0_ipaddress())
        self.write_attribute(self.app_handles["WLAN0_IP"], get_wlan0_ipaddress())

def get_eth0_ipaddress():
    return "192.168.1.100"

def get_wlan0_ipaddress():
    return "192.168.3.100"

def Main():
    cfg_server = WifiCfgServer(port="COM12", baud=115200, timeout=0.1)
    # BLE Device configuration and start advertising
    cfg_server.get_module_info()
    cfg_server.set_device_capabilities()
    cfg_server.delete_bonding()
    cfg_server.allow_bonding()
    cfg_server.advertise_general()

    fh = logging.FileHandler("wificfg_serverlog.log")
    logger = logging.getLogger("")
    logger.addHandler(fh)

    while (1):
        if not cfg_server.connected:
            cfg_server.advertise_general()
            while not cfg_server.connected:
                time.sleep(3)
        else:
            time.sleep(3)

if __name__ == "__main__":
    Main()