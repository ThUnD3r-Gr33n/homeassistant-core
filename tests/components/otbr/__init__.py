"""Tests for the Open Thread Border Router integration."""
BASE_URL = "http://core-silabs-multiprotocol:8081"
CONFIG_ENTRY_DATA = {"url": "http://core-silabs-multiprotocol:8081"}
CONFIG_ENTRY_DATA_2 = {"url": "http://core-silabs-multiprotocol_2:8081"}

DATASET_CH15 = bytes.fromhex(
    "0E080000000000010000000300000F35060004001FFFE00208F642646DA209B1D00708FDF57B5A"
    "0FE2AAF60510DE98B5BA1A528FEE049D4B4B01835375030D4F70656E5468726561642048410102"
    "25A40410F5DD18371BFD29E1A601EF6FFAD94C030C0402A0F7F8"
)

DATASET_CH16 = bytes.fromhex(
    "0E080000000000010000000300001035060004001FFFE00208F642646DA209B1C00708FDF57B5A"
    "0FE2AAF60510DE98B5BA1A528FEE049D4B4B01835375030D4F70656E5468726561642048410102"
    "25A40410F5DD18371BFD29E1A601EF6FFAD94C030C0402A0F7F8"
)

DATASET_INSECURE_NW_KEY = bytes.fromhex(
    "0E080000000000010000000300000F35060004001FFFE0020811111111222222220708FDD24657"
    "0A336069051000112233445566778899AABBCCDDEEFF030E4F70656E54687265616444656D6F01"
    "0212340410445F2B5CA6F2A93A55CE570A70EFEECB0C0402A0F7F8"
)

DATASET_INSECURE_PASSPHRASE = bytes.fromhex(
    "0E080000000000010000000300000F35060004001FFFE0020811111111222222220708FDD24657"
    "0A336069051000112233445566778899AABBCCDDEEFA030E4F70656E54687265616444656D6F01"
    "0212340410445F2B5CA6F2A93A55CE570A70EFEECB0C0402A0F7F8"
)
