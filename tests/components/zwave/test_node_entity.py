"""Test Z-Wave node entity."""
import pytest

from homeassistant.components.zwave import const, node_entity
from homeassistant.const import ATTR_ENTITY_ID

from tests.async_mock import MagicMock, patch
import tests.mock.zwave as mock_zwave


async def test_maybe_schedule_update(hass, mock_openzwave):
    """Test maybe schedule update."""
    base_entity = node_entity.ZWaveBaseEntity()
    base_entity.entity_id = "zwave.bla"
    base_entity.hass = hass

    with patch.object(hass.loop, "call_later") as mock_call_later:
        base_entity._schedule_update()
        assert mock_call_later.called

        base_entity._schedule_update()
        assert len(mock_call_later.mock_calls) == 1
        assert base_entity._update_scheduled is True

        do_update = mock_call_later.mock_calls[0][1][1]

        do_update()
        assert base_entity._update_scheduled is False

        base_entity._schedule_update()
        assert len(mock_call_later.mock_calls) == 2


async def test_node_event_activated(hass, mock_openzwave):
    """Test Node event activated event."""
    mock_receivers = []

    def mock_connect(receiver, signal, *args, **kwargs):
        if signal == mock_zwave.MockNetwork.SIGNAL_NODE_EVENT:
            mock_receivers.append(receiver)

    node = mock_zwave.MockNode(node_id=11)

    with patch("pydispatch.dispatcher.connect", new=mock_connect):
        entity = node_entity.ZWaveNodeEntity(node, mock_openzwave)

    assert len(mock_receivers) == 1

    events = []

    def listener(event):
        events.append(event)

    hass.bus.async_listen(const.EVENT_NODE_EVENT, listener)

    # Test event before entity added to hass
    value = 234
    hass.async_add_job(mock_receivers[0], node, value)
    await hass.async_block_till_done()
    assert len(events) == 0

    # Add entity to hass
    entity.hass = hass
    entity.entity_id = "zwave.mock_node"

    value = 234
    hass.async_add_job(mock_receivers[0], node, value)
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data[ATTR_ENTITY_ID] == "zwave.mock_node"
    assert events[0].data[const.ATTR_NODE_ID] == 11
    assert events[0].data[const.ATTR_BASIC_LEVEL] == value


async def test_scene_activated(hass, mock_openzwave):
    """Test scene activated event."""
    mock_receivers = []

    def mock_connect(receiver, signal, *args, **kwargs):
        if signal == mock_zwave.MockNetwork.SIGNAL_SCENE_EVENT:
            mock_receivers.append(receiver)

    node = mock_zwave.MockNode(node_id=11)

    with patch("pydispatch.dispatcher.connect", new=mock_connect):
        entity = node_entity.ZWaveNodeEntity(node, mock_openzwave)

    assert len(mock_receivers) == 1

    events = []

    def listener(event):
        events.append(event)

    hass.bus.async_listen(const.EVENT_SCENE_ACTIVATED, listener)

    # Test event before entity added to hass
    scene_id = 123
    hass.async_add_job(mock_receivers[0], node, scene_id)
    await hass.async_block_till_done()
    assert len(events) == 0

    # Add entity to hass
    entity.hass = hass
    entity.entity_id = "zwave.mock_node"

    scene_id = 123
    hass.async_add_job(mock_receivers[0], node, scene_id)
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data[ATTR_ENTITY_ID] == "zwave.mock_node"
    assert events[0].data[const.ATTR_NODE_ID] == 11
    assert events[0].data[const.ATTR_SCENE_ID] == scene_id


async def test_central_scene_activated(hass, mock_openzwave):
    """Test central scene activated event."""
    mock_receivers = []

    def mock_connect(receiver, signal, *args, **kwargs):
        if signal == mock_zwave.MockNetwork.SIGNAL_VALUE_CHANGED:
            mock_receivers.append(receiver)

    node = mock_zwave.MockNode(node_id=11)

    with patch("pydispatch.dispatcher.connect", new=mock_connect):
        entity = node_entity.ZWaveNodeEntity(node, mock_openzwave)

    assert len(mock_receivers) == 1

    events = []

    def listener(event):
        events.append(event)

    hass.bus.async_listen(const.EVENT_SCENE_ACTIVATED, listener)

    # Test event before entity added to hass
    scene_id = 1
    scene_data = 3
    value = mock_zwave.MockValue(
        command_class=const.COMMAND_CLASS_CENTRAL_SCENE, index=scene_id, data=scene_data
    )
    hass.async_add_job(mock_receivers[0], node, value)
    await hass.async_block_till_done()
    assert len(events) == 0

    # Add entity to hass
    entity.hass = hass
    entity.entity_id = "zwave.mock_node"

    scene_id = 1
    scene_data = 3
    value = mock_zwave.MockValue(
        command_class=const.COMMAND_CLASS_CENTRAL_SCENE, index=scene_id, data=scene_data
    )
    hass.async_add_job(mock_receivers[0], node, value)
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data[ATTR_ENTITY_ID] == "zwave.mock_node"
    assert events[0].data[const.ATTR_NODE_ID] == 11
    assert events[0].data[const.ATTR_SCENE_ID] == scene_id
    assert events[0].data[const.ATTR_SCENE_DATA] == scene_data


async def test_application_version(hass, mock_openzwave):
    """Test application version."""
    mock_receivers = {}

    signal_mocks = [
        mock_zwave.MockNetwork.SIGNAL_VALUE_CHANGED,
        mock_zwave.MockNetwork.SIGNAL_VALUE_ADDED,
    ]

    def mock_connect(receiver, signal, *args, **kwargs):
        if signal in signal_mocks:
            mock_receivers[signal] = receiver

    node = mock_zwave.MockNode(node_id=11)

    with patch("pydispatch.dispatcher.connect", new=mock_connect):
        entity = node_entity.ZWaveNodeEntity(node, mock_openzwave)

    for signal_mock in signal_mocks:
        assert signal_mock in mock_receivers.keys()

    events = []

    def listener(event):
        events.append(event)

    # Make sure application version isn't set before
    assert (
        node_entity.ATTR_APPLICATION_VERSION
        not in entity.device_state_attributes.keys()
    )

    # Add entity to hass
    entity.hass = hass
    entity.entity_id = "zwave.mock_node"

    # Fire off an added value
    value = mock_zwave.MockValue(
        command_class=const.COMMAND_CLASS_VERSION,
        label="Application Version",
        data="5.10",
    )
    hass.async_add_job(
        mock_receivers[mock_zwave.MockNetwork.SIGNAL_VALUE_ADDED], node, value
    )
    await hass.async_block_till_done()

    assert (
        entity.device_state_attributes[node_entity.ATTR_APPLICATION_VERSION] == "5.10"
    )

    # Fire off a changed
    value = mock_zwave.MockValue(
        command_class=const.COMMAND_CLASS_VERSION,
        label="Application Version",
        data="4.14",
    )
    hass.async_add_job(
        mock_receivers[mock_zwave.MockNetwork.SIGNAL_VALUE_CHANGED], node, value
    )
    await hass.async_block_till_done()

    assert (
        entity.device_state_attributes[node_entity.ATTR_APPLICATION_VERSION] == "4.14"
    )


@pytest.mark.usefixtures("mock_openzwave")
class TestZWaveNodeEntity:
    """Class to test ZWaveNodeEntity."""

    @staticmethod
    def test_network_node_changed_from_value(mock_node, mock_entity):
        """Test for network_node_changed."""
        value = mock_zwave.MockValue(node=mock_node)
        with patch.object(mock_entity, "maybe_schedule_update") as mock:
            mock_zwave.value_changed(value)
            mock.assert_called_once_with()

    @staticmethod
    def test_network_node_changed_from_node(mock_node, mock_entity):
        """Test for network_node_changed."""
        with patch.object(mock_entity, "maybe_schedule_update") as mock:
            mock_zwave.node_changed(mock_node)
            mock.assert_called_once_with()

    @staticmethod
    def test_network_node_changed_from_another_node(mock_entity):
        """Test for network_node_changed."""
        with patch.object(mock_entity, "maybe_schedule_update") as mock:
            node = mock_zwave.MockNode(node_id=1024)
            mock_zwave.node_changed(node)
            assert not mock.called

    @staticmethod
    def test_network_node_changed_from_notification(mock_node, mock_entity):
        """Test for network_node_changed."""
        with patch.object(mock_entity, "maybe_schedule_update") as mock:
            mock_zwave.notification(node_id=mock_node.node_id)
            mock.assert_called_once_with()

    @staticmethod
    def test_network_node_changed_from_another_notification(mock_entity):
        """Test for network_node_changed."""
        with patch.object(mock_entity, "maybe_schedule_update") as mock:
            mock_zwave.notification(node_id=1024)
            assert not mock.called

    @staticmethod
    def test_node_changed(mock_node):
        """Test node_changed function."""
        mock_zwave_network = MagicMock()
        mock_entity = node_entity.ZWaveNodeEntity(mock_node, mock_zwave_network)
        assert {
            "node_id": mock_node.node_id,
            "node_name": "Mock Node",
            "manufacturer_name": "Test Manufacturer",
            "product_name": "Test Product",
        } == mock_entity.device_state_attributes

        mock_node.get_values.return_value = {1: mock_zwave.MockValue(data=1800)}
        mock_zwave_network.manager.getNodeStatistics.return_value = {
            "receivedCnt": 4,
            "ccData": [
                {"receivedCnt": 0, "commandClassId": 134, "sentCnt": 0},
                {"receivedCnt": 1, "commandClassId": 133, "sentCnt": 1},
                {"receivedCnt": 1, "commandClassId": 115, "sentCnt": 1},
                {"receivedCnt": 0, "commandClassId": 114, "sentCnt": 0},
                {"receivedCnt": 0, "commandClassId": 112, "sentCnt": 0},
                {"receivedCnt": 1, "commandClassId": 32, "sentCnt": 1},
                {"receivedCnt": 0, "commandClassId": 0, "sentCnt": 0},
            ],
            "receivedUnsolicited": 0,
            "sentTS": "2017-03-27 15:38:15:620 ",
            "averageRequestRTT": 2462,
            "lastResponseRTT": 3679,
            "retries": 0,
            "sentFailed": 1,
            "sentCnt": 7,
            "quality": 0,
            "lastRequestRTT": 1591,
            "lastReceivedMessage": [
                0,
                4,
                0,
                15,
                3,
                32,
                3,
                0,
                221,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
            "receivedDups": 1,
            "averageResponseRTT": 2443,
            "receivedTS": "2017-03-27 15:38:19:298 ",
        }
        mock_entity.node_changed()
        assert {
            "node_id": mock_node.node_id,
            "node_name": "Mock Node",
            "manufacturer_name": "Test Manufacturer",
            "product_name": "Test Product",
            "query_stage": "Dynamic",
            "is_awake": True,
            "is_ready": False,
            "is_failed": False,
            "is_info_received": True,
            "max_baud_rate": 40000,
            "is_zwave_plus": False,
            "battery_level": 42,
            "wake_up_interval": 1800,
            "averageRequestRTT": 2462,
            "averageResponseRTT": 2443,
            "lastRequestRTT": 1591,
            "lastResponseRTT": 3679,
            "receivedCnt": 4,
            "receivedDups": 1,
            "receivedTS": "2017-03-27 15:38:19:298 ",
            "receivedUnsolicited": 0,
            "retries": 0,
            "sentCnt": 7,
            "sentFailed": 1,
            "sentTS": "2017-03-27 15:38:15:620 ",
        } == mock_entity.device_state_attributes

        mock_node.can_wake_up_value = False
        mock_entity.node_changed()

        assert "wake_up_interval" not in mock_entity.device_state_attributes

    @staticmethod
    def test_name(mock_entity):
        """Test name property."""
        assert mock_entity.name == "Mock Node"

    @staticmethod
    def test_state_before_update(mock_entity):
        """Test state before update was called."""
        assert mock_entity.state is None

    @staticmethod
    def test_state_not_ready(mock_node, mock_entity):
        """Test state property."""
        mock_node.is_ready = False
        mock_entity.node_changed()
        assert mock_entity.state == "initializing"

        mock_node.is_failed = True
        mock_node.query_stage = "Complete"
        mock_entity.node_changed()
        assert mock_entity.state == "dead"

        mock_node.is_failed = False
        mock_node.is_awake = False
        mock_entity.node_changed()
        assert mock_entity.state == "sleeping"

    @staticmethod
    def test_state_ready(mock_node, mock_entity):
        """Test state property."""
        mock_node.query_stage = "Complete"
        mock_node.is_ready = True
        mock_entity.node_changed()
        assert mock_entity.state == "ready"

        mock_node.is_failed = True
        mock_entity.node_changed()
        assert mock_entity.state == "dead"

        mock_node.is_failed = False
        mock_node.is_awake = False
        mock_entity.node_changed()
        assert mock_entity.state == "sleeping"

    @staticmethod
    def test_not_polled(mock_entity):
        """Test should_poll property."""
        assert not mock_entity.should_poll

    @staticmethod
    def test_unique_id(mock_entity):
        """Test unique_id."""
        assert mock_entity.unique_id == "node-567"

    @staticmethod
    def test_unique_id_missing_data(mock_node):
        """Test unique_id."""
        mock_node.manufacturer_name = None
        mock_node.name = None
        entity = node_entity.ZWaveNodeEntity(mock_node, MagicMock())

        assert entity.unique_id is None
