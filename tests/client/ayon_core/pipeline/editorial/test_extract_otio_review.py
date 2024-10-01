import mock
import os
import pytest
from typing import NamedTuple

import opentimelineio as otio

import ayon_core.lib
from ayon_core.plugins.publish import extract_otio_review


_RESOURCE_DIR = os.path.join(
    os.path.dirname(__file__),
    "resources"
)


class MockInstance():
    """ Mock pyblish instance for testing purpose.
    """
    def __init__(self, data: dict):
        self.data = data 
        self.context = self


class CaptureFFmpegCalls():
    """ Mock calls made to ffmpeg subprocess.
    """
    def __init__(self):
        self.calls = []

    def append_call(self, *args, **kwargs):
        ffmpeg_args_list, = args
        self.calls.append(" ".join(ffmpeg_args_list))
        return True

    def get_fmpeg_executable(self, _):
        return ["/path/to/ffmpeg"]


def run_process(file_name: str):
    """
    """
    # Get OTIO review data from serialized file_name
    file_path = os.path.join(_RESOURCE_DIR, file_name)
    clip = otio.schema.Clip.from_json_file(file_path)

    # Prepare dummy instance and capture call object
    capture_call = CaptureFFmpegCalls()
    processor = extract_otio_review.ExtractOTIOReview()
    instance = MockInstance({
        "otioReviewClips": [clip],
        "handleStart": 10,
        "handleEnd": 10,
        "workfileFrameStart": 1001,
        "folderPath": "/dummy/path",
        "anatomy": NamedTuple("Anatomy", [('project_name', "test_project")])
    })

    # Mock calls to extern and run plugins.
    with mock.patch.object(
        extract_otio_review,
        "get_ffmpeg_tool_args",
        side_effect=capture_call.get_fmpeg_executable,
    ):
        with mock.patch.object(
            extract_otio_review,
            "run_subprocess",
            side_effect=capture_call.append_call,
        ):
            with mock.patch.object(
                processor,
                "_get_folder_name_based_prefix",
                return_value="C:/result/output."
            ):
                processor.process(instance)

    # return all calls made to ffmpeg subprocess
    return capture_call.calls


def test_image_sequence_with_embedded_tc_and_handles_out_of_range():
    """
    Img sequence clip (embedded timecode 1h/24fps)
    available_files = 1000-1100
    available_range = 87399-87500 24fps
    source_range = 87399-87500 24fps
    """
    calls = run_process("img_seq_embedded_tc_review.json")

    expected = [
        # 10 head black handles generated from gap (991-1000)
        "/path/to/ffmpeg -t 0.4166666666666667 -r 24.0 -f lavfi -i "
        "color=c=black:s=1280x720 -tune stillimage -start_number 991 "
        "C:/result/output.%03d.jpg",

        # 10 tail black handles generated from gap (1102-1111)
        "/path/to/ffmpeg -t 0.4166666666666667 -r 24.0 -f lavfi -i "
        "color=c=black:s=1280x720 -tune stillimage -start_number 1102 "
        "C:/result/output.%03d.jpg",

        # Report from source exr (1001-1101) with enforce framerate
        "/path/to/ffmpeg -start_number 1000 -framerate 24.0 -i "
        "C:\\exr_embedded_tc\\output.%04d.exr -start_number 1001 "
        "C:/result/output.%03d.jpg"
    ]

    assert calls == expected


def test_image_sequence_and_handles_out_of_range():
    """
    Img sequence clip (no timecode)
    available_files = 1000-1100
    available_range = 0-101 25fps
    source_range = 5-91 24fps
    """
    calls = run_process("img_seq_review.json")

    expected = [
        # 5 head black frames generated from gap (991-995)
        "/path/to/ffmpeg -t 0.2 -r 25.0 -f lavfi -i color=c=black:s=1280x720 -tune "
        "stillimage -start_number 991 C:/result/output.%03d.jpg",

        # 9 tail back frames generated from gap (1097-1105)
        "/path/to/ffmpeg -t 0.36 -r 25.0 -f lavfi -i color=c=black:s=1280x720 -tune "
        "stillimage -start_number 1097 C:/result/output.%03d.jpg",

        # Report from source tiff (996-1096)
        # 996-1000 = additional 5 head frames
        # 1001-1095 = source range conformed to 25fps
        # 1096-1096 = additional 1 tail frames
        "/path/to/ffmpeg -start_number 1000 -framerate 25.0 -i "
        "C:\\tif_seq\\output.%04d.tif -start_number 996 C:/result/output.%03d.jpg"
    ]

    assert calls == expected


def test_movie_with_embedded_tc_no_gap_handles():
    """
    Qt movie clip (embedded timecode 1h/24fps)
    available_range = 86400-86500 24fps
    source_range = 86414-86482 24fps
    """
    calls = run_process("qt_embedded_tc_review.json")

    expected = [
        # Handles are all included in media available range.
        # Extract source range from Qt
        # - first_frame = 14 src - 10 (head tail) = frame 4 = 0.1666s
        # - duration = 68fr (source) + 20fr (handles) = 88frames = 3.666s
        "/path/to/ffmpeg -ss 0.16666666666666666 -t 3.6666666666666665 "
        "-i C:\\data\\qt_embedded_tc.mov -start_number 991 "
        "C:/result/output.%03d.jpg"
    ]

    assert calls == expected


def test_short_movie_head_gap_handles():
    """
    Qt movie clip.
    available_range = 0-30822 25fps
    source_range = 0-50 24fps
    """
    calls = run_process("qt_review.json")

    expected = [
        # 10 head black frames generated from gap (991-1000)
        "/path/to/ffmpeg -t 0.4 -r 25.0 -f lavfi -i color=c=black:s=1280x720 -tune "
        "stillimage -start_number 991 C:/result/output.%03d.jpg",

        # source range + 10 tail frames
        # duration = 50fr (source) + 10fr (tail handle) = 60 fr = 2.4s
        "/path/to/ffmpeg -ss 0.0 -t 2.4 -i C:\\data\\movie.mp4 -start_number 1001 "
        "C:/result/output.%03d.jpg"
    ]

    assert calls == expected


def test_short_movie_tail_gap_handles():
    """
    Qt movie clip.
    available_range = 0-101 24fps
    source_range = 35-101 24fps
    """
    calls = run_process("qt_handle_tail_review.json")

    expected = [
        # 10 tail black frames generated from gap (1067-1076)
        "/path/to/ffmpeg -t 0.4166666666666667 -r 24.0 -f lavfi -i "
        "color=c=black:s=1280x720 -tune stillimage -start_number 1067 "
        "C:/result/output.%03d.jpg",

        # 10 head frames + source range
        # duration = 10fr (head handle) + 66fr (source) = 76fr = 3.16s
        "/path/to/ffmpeg -ss 1.0416666666666667 -t 3.1666666666666665 -i "
        "C:\\data\\qt_no_tc_24fps.mov -start_number 991 C:/result/output.%03d.jpg"
    ]

    assert calls == expected