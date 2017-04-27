from collections import namedtuple
from PyQt5.QtCore import QPoint
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt
from behave import *

from power_hour_creator.media import TRACK_LENGTH
from power_hour_creator.ui.tracklist import Tracklist, TracklistModel

Track = namedtuple('Track', 'url length')
tracks = [
    Track('https://soundcloud.com/dan-weniger/dead-winter', 136),
    Track('https://www.youtube.com/watch?v=JzkvgqTcmmY', 110)
]

videos = [
    Track('https://www.youtube.com/watch?v=XSVunk2LUAo', 202),
    Track('https://www.youtube.com/watch?v=JzkvgqTcmmY', 110)
]


@when('I add {num_tracks} tracks to a power hour')
def step_impl(context, num_tracks):
    for track_num in range(int(num_tracks)):
        add_song_to_tracklist(context)


def add_song_to_tracklist(context, full_song=False, video=False, pos=None):
    viewport = context.main_window.tracklist.viewport()

    current_row = pos or context.num_tracks + 1
    url_cell_pos = tracklist_cell_pos(context, row=current_row, column=TracklistModel.Columns.url)

    QTest.mouseClick(viewport, Qt.LeftButton, pos=url_cell_pos)

    track = videos[context.num_tracks % len(videos)] if video else tracks[context.num_tracks % len(tracks)]
    context.last_track_added = track

    QTest.keyClicks(viewport.focusWidget(), track.url)
    QTest.keyClick(viewport.focusWidget(), Qt.Key_Return)

    if full_song:
        full_song_cell_pos = tracklist_cell_pos(context, row=current_row, column=TracklistModel.Columns.full_song)
        QTest.mouseClick(viewport, Qt.LeftButton, pos=full_song_cell_pos)
        QTest.keyClick(viewport.focusWidget(), Qt.Key_Down)

    context.num_tracks += 1
    context.prhr_length += track.length if full_song else TRACK_LENGTH


def tracklist_cell_pos(context, row, column):
    tracklist = context.main_window.tracklist

    return QPoint(
        tracklist.columnViewportPosition(column),
        tracklist.rowViewportPosition(row)
    )
