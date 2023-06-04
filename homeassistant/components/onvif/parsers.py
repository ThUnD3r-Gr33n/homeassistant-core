"""ONVIF event parsers."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
import datetime
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.util import dt as dt_util
from homeassistant.util.decorator import Registry

from .models import Event

PARSERS: Registry[
    str, Callable[[str, Any], Coroutine[Any, Any, Event | None]]
] = Registry()

VIDEO_SOURCE_MAPPING = {
    "vsconf": "VideoSourceToken",
}


def _normalize_video_source(source: str) -> str:
    """Normalize video source.

    Some cameras do not set the VideoSourceToken correctly so we get duplicate
    sensors, so we need to normalize it to the correct value.
    """
    return VIDEO_SOURCE_MAPPING.get(source, source)


def local_datetime_or_none(value: str) -> datetime.datetime | None:
    """Convert strings to datetimes, if invalid, return None."""
    # To handle cameras that return times like '0000-00-00T00:00:00Z' (e.g. hikvision)
    try:
        ret = dt_util.parse_datetime(value)
    except ValueError:
        return None
    if ret is not None:
        return dt_util.as_local(ret)
    return None


@PARSERS.register("tns1:VideoSource/MotionAlarm")
# pylint: disable=protected-access
async def async_parse_motion_alarm(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:VideoSource/MotionAlarm
    """
    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "motion_alarm",
            "Motion Alarm",
            "binary_sensor",
            "motion",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:VideoSource/ImageTooBlurry/AnalyticsService")
@PARSERS.register("tns1:VideoSource/ImageTooBlurry/ImagingService")
@PARSERS.register("tns1:VideoSource/ImageTooBlurry/RecordingService")
# pylint: disable=protected-access
async def async_parse_image_too_blurry(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:VideoSource/ImageTooBlurry/*
    """
    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "image_too_blurry",
            "Image Too Blurry",
            "binary_sensor",
            "problem",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:VideoSource/ImageTooDark/AnalyticsService")
@PARSERS.register("tns1:VideoSource/ImageTooDark/ImagingService")
@PARSERS.register("tns1:VideoSource/ImageTooDark/RecordingService")
# pylint: disable=protected-access
async def async_parse_image_too_dark(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:VideoSource/ImageTooDark/*
    """
    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "image_too_dark",
            "Image Too Dark",
            "binary_sensor",
            "problem",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:VideoSource/ImageTooBright/AnalyticsService")
@PARSERS.register("tns1:VideoSource/ImageTooBright/ImagingService")
@PARSERS.register("tns1:VideoSource/ImageTooBright/RecordingService")
# pylint: disable=protected-access
async def async_parse_image_too_bright(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:VideoSource/ImageTooBright/*
    """
    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "image_too_bright",
            "Image Too Bright",
            "binary_sensor",
            "problem",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:VideoSource/GlobalSceneChange/AnalyticsService")
@PARSERS.register("tns1:VideoSource/GlobalSceneChange/ImagingService")
@PARSERS.register("tns1:VideoSource/GlobalSceneChange/RecordingService")
# pylint: disable=protected-access
async def async_parse_scene_change(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:VideoSource/GlobalSceneChange/*
    """
    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "global_scene_change",
            "Global Scene Change",
            "binary_sensor",
            "problem",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:AudioAnalytics/Audio/DetectedSound")
# pylint: disable=protected-access
async def async_parse_detected_sound(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:AudioAnalytics/Audio/DetectedSound
    """
    try:
        audio_source = ""
        audio_analytics = ""
        rule = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "AudioSourceConfigurationToken":
                audio_source = source.Value
            if source.Name == "AudioAnalyticsConfigurationToken":
                audio_analytics = source.Value
            if source.Name == "Rule":
                rule = source.Value

        return Event(
            f"{uid}_{msg.Topic._value_1}_{audio_source}_{audio_analytics}_{rule}",
            "detected_sound",
            "Detected Sound",
            "binary_sensor",
            "sound",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/FieldDetector/ObjectsInside")
# pylint: disable=protected-access
async def async_parse_field_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/FieldDetector/ObjectsInside
    """
    try:
        video_source = ""
        video_analytics = ""
        rule = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "VideoSourceConfigurationToken":
                video_source = _normalize_video_source(source.Value)
            if source.Name == "VideoAnalyticsConfigurationToken":
                video_analytics = source.Value
            if source.Name == "Rule":
                rule = source.Value

        evt = Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}_{video_analytics}_{rule}",
            "field_detection",
            "Field Detection",
            "binary_sensor",
            "motion",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
        return evt
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/CellMotionDetector/Motion")
# pylint: disable=protected-access
async def async_parse_cell_motion_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/CellMotionDetector/Motion
    """
    try:
        video_source = ""
        video_analytics = ""
        rule = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "VideoSourceConfigurationToken":
                video_source = _normalize_video_source(source.Value)
            if source.Name == "VideoAnalyticsConfigurationToken":
                video_analytics = source.Value
            if source.Name == "Rule":
                rule = source.Value

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}_{video_analytics}_{rule}",
            "cell_motion_detection",
            "Cell Motion Detection",
            "binary_sensor",
            "motion",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/MotionRegionDetector/Motion")
# pylint: disable=protected-access
async def async_parse_motion_region_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/MotionRegionDetector/Motion
    """
    try:
        video_source = ""
        video_analytics = ""
        rule = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "VideoSourceConfigurationToken":
                video_source = _normalize_video_source(source.Value)
            if source.Name == "VideoAnalyticsConfigurationToken":
                video_analytics = source.Value
            if source.Name == "Rule":
                rule = source.Value

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}_{video_analytics}_{rule}",
            "motion_region_detection",
            "Motion Region Detection",
            "binary_sensor",
            "motion",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value in ["1", "true"],
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/LineDetector/Crossed")
# pylint: disable=protected-access
async def async_parse_line_crossed(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/LineDetector/Crossed.
    """
    try:
        video_source = ""
        video_analytics = ""
        rule = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "VideoSourceConfigurationToken":
                video_source = source.Value
            if source.Name == "VideoAnalyticsConfigurationToken":
                video_analytics = source.Value
            if source.Name == "Rule":
                rule = source.Value

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}_{video_analytics}_{rule}",
            f"{rule}_line_crossed",
            f"{rule} Line Crossed",
            "event",
            entity_enabled=msg.Message._value_1.PropertyOperation != "Initialized",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/TamperDetector/Tamper")
# pylint: disable=protected-access
async def async_parse_tamper_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/TamperDetector/Tamper
    """
    try:
        video_source = ""
        video_analytics = ""
        rule = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "VideoSourceConfigurationToken":
                video_source = _normalize_video_source(source.Value)
            if source.Name == "VideoAnalyticsConfigurationToken":
                video_analytics = source.Value
            if source.Name == "Rule":
                rule = source.Value

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}_{video_analytics}_{rule}",
            "tamper_detection",
            "Tamper Detection",
            "binary_sensor",
            "problem",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/MyRuleDetector/DogCatDetect")
# pylint: disable=protected-access
async def async_parse_dog_cat_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/MyRuleDetector/DogCatDetect
    """
    try:
        video_source = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "Source":
                video_source = _normalize_video_source(source.Value)

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}",
            "Pet Detection",
            "binary_sensor",
            "motion",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/MyRuleDetector/VehicleDetect")
# pylint: disable=protected-access
async def async_parse_vehicle_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/MyRuleDetector/VehicleDetect
    """
    try:
        video_source = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "Source":
                video_source = _normalize_video_source(source.Value)

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}",
            "Vehicle Detection",
            "binary_sensor",
            "motion",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/MyRuleDetector/PeopleDetect")
# pylint: disable=protected-access
async def async_parse_person_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/MyRuleDetector/PeopleDetect
    """
    try:
        video_source = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "Source":
                video_source = _normalize_video_source(source.Value)

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}",
            "Person Detection",
            "binary_sensor",
            "motion",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/MyRuleDetector/FaceDetect")
# pylint: disable=protected-access
async def async_parse_face_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/MyRuleDetector/FaceDetect
    """
    try:
        video_source = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "Source":
                video_source = _normalize_video_source(source.Value)

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}",
            "Face Detection",
            "binary_sensor",
            "motion",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/MyRuleDetector/Visitor")
# pylint: disable=protected-access
async def async_parse_visitor_detector(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/MyRuleDetector/Visitor
    """
    try:
        video_source = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "Source":
                video_source = _normalize_video_source(source.Value)

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}",
            "Visitor Detection",
            "binary_sensor",
            "occupancy",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:Device/Trigger/DigitalInput")
# pylint: disable=protected-access
async def async_parse_digital_input(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:Device/Trigger/DigitalInput
    """
    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "digital_input",
            "Digital Input",
            "binary_sensor",
            None,
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:Device/Trigger/Relay")
# pylint: disable=protected-access
async def async_parse_relay(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:Device/Trigger/Relay
    """
    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "relay_triggered",
            "Relay Triggered",
            "binary_sensor",
            None,
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "active",
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:Device/HardwareFailure/StorageFailure")
# pylint: disable=protected-access
async def async_parse_storage_failure(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:Device/HardwareFailure/StorageFailure
    """
    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "storage_failure",
            "Storage Failure",
            "binary_sensor",
            "problem",
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "true",
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:Monitoring/ProcessorUsage")
# pylint: disable=protected-access
async def async_parse_processor_usage(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:Monitoring/ProcessorUsage
    """
    try:
        usage = float(msg.Message._value_1.Data.SimpleItem[0].Value)
        if usage <= 1:
            usage *= 100

        return Event(
            f"{uid}_{msg.Topic._value_1}",
            "processor_usage",
            "Processor Usage",
            "sensor",
            None,
            "percent",
            int(usage),
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:Monitoring/OperatingTime/LastReboot")
# pylint: disable=protected-access
async def async_parse_last_reboot(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:Monitoring/OperatingTime/LastReboot
    """
    try:
        date_time = local_datetime_or_none(
            msg.Message._value_1.Data.SimpleItem[0].Value
        )
        return Event(
            f"{uid}_{msg.Topic._value_1}",
            "last_reboot",
            "Last Reboot",
            "sensor",
            "timestamp",
            None,
            date_time,
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:Monitoring/OperatingTime/LastReset")
# pylint: disable=protected-access
async def async_parse_last_reset(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:Monitoring/OperatingTime/LastReset
    """
    try:
        date_time = local_datetime_or_none(
            msg.Message._value_1.Data.SimpleItem[0].Value
        )
        return Event(
            f"{uid}_{msg.Topic._value_1}",
            "last_reset",
            "Last Reset",
            "sensor",
            "timestamp",
            None,
            date_time,
            EntityCategory.DIAGNOSTIC,
            enabled=False,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:Monitoring/Backup/Last")
# pylint: disable=protected-access
async def async_parse_backup_last(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:Monitoring/Backup/Last
    """

    try:
        date_time = local_datetime_or_none(
            msg.Message._value_1.Data.SimpleItem[0].Value
        )
        return Event(
            f"{uid}_{msg.Topic._value_1}",
            "last_backup",
            "Last Backup",
            "sensor",
            "timestamp",
            None,
            date_time,
            EntityCategory.DIAGNOSTIC,
            enabled=False,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:Monitoring/OperatingTime/LastClockSynchronization")
# pylint: disable=protected-access
async def async_parse_last_clock_sync(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:Monitoring/OperatingTime/LastClockSynchronization
    """
    try:
        date_time = local_datetime_or_none(
            msg.Message._value_1.Data.SimpleItem[0].Value
        )
        return Event(
            f"{uid}_{msg.Topic._value_1}",
            "last_clock_synchronization",
            "Last Clock Synchronization",
            "sensor",
            "timestamp",
            None,
            date_time,
            EntityCategory.DIAGNOSTIC,
            enabled=False,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RecordingConfig/JobState")
# pylint: disable=protected-access
async def async_parse_jobstate(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RecordingConfig/JobState
    """

    try:
        source = msg.Message._value_1.Source.SimpleItem[0].Value
        return Event(
            f"{uid}_{msg.Topic._value_1}_{source}",
            "recording_job_state",
            "Recording Job State",
            "binary_sensor",
            None,
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value == "Active",
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/LineDetector/Crossed")
# pylint: disable=protected-access
async def async_parse_linedetector_crossed(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/LineDetector/Crossed
    """
    try:
        video_source = ""
        video_analytics = ""
        rule = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "VideoSourceConfigurationToken":
                video_source = source.Value
            if source.Name == "VideoAnalyticsConfigurationToken":
                video_analytics = source.Value
            if source.Name == "Rule":
                rule = source.Value

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}_{video_analytics}_{rule}",
            "Line Detector Crossed",
            "sensor",
            None,
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value,
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None


@PARSERS.register("tns1:RuleEngine/CountAggregation/Counter")
# pylint: disable=protected-access
async def async_parse_count_aggregation_counter(uid: str, msg) -> Event | None:
    """Handle parsing event message.

    Topic: tns1:RuleEngine/CountAggregation/Counter
    """
    try:
        video_source = ""
        video_analytics = ""
        rule = ""
        for source in msg.Message._value_1.Source.SimpleItem:
            if source.Name == "VideoSourceConfigurationToken":
                video_source = _normalize_video_source(source.Value)
            if source.Name == "VideoAnalyticsConfigurationToken":
                video_analytics = source.Value
            if source.Name == "Rule":
                rule = source.Value

        return Event(
            f"{uid}_{msg.Topic._value_1}_{video_source}_{video_analytics}_{rule}",
            "Count Aggregation Counter",
            "sensor",
            None,
            None,
            msg.Message._value_1.Data.SimpleItem[0].Value,
            EntityCategory.DIAGNOSTIC,
        )
    except (AttributeError, KeyError):
        return None
