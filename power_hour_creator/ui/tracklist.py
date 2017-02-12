from PyQt5.QtWidgets import QItemDelegate
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView
from PyQt5.QtCore import pyqtSignal, Qt
import re

from power_hour_creator.media_handling import InvalidURL, MissingURL, DownloadError,\
    FindMediaDescriptionService, Track


class DisplayTime:
    def __init__(self, time):
        self._time = time

    def as_time_str(self):
        if ':' in str(self._time):
            return self._time

        m, s = divmod(int(self._time), 60)
        return "%02d:%02d" % (m, s)

    def as_seconds(self):
        if len(self._time) == 0:
            return self._time

        if type(self._time) is int:
            return self._time

        if re.search('[a-zA-Z]', self._time):
            return ""

        if ':' not in self._time:
            return int(self._time)

        return sum(x * int(t) for x, t in zip([60, 1], self._time.split(':')))




class TrackDelegate(QItemDelegate):
    def __init__(self, read_only_columns, time_columns, parent=None):
        super().__init__(parent)
        self._read_only_columns = read_only_columns
        self._time_columns = time_columns

    def paint(self, painter, option, index):
        if self._column_is_time_column_and_has_data(index):
            seconds = index.model().data(index, Qt.DisplayRole)
            time = DisplayTime(seconds)
            self.drawDisplay(painter, option, option.rect, time.as_time_str())
            self.drawFocus(painter, option, option.rect)
        else:
            super().paint(painter, option, index)

    def setEditorData(self, editor, index):
        if self._column_is_time_column_and_has_data(index):
            seconds = index.model().data(index, Qt.DisplayRole)
            time = DisplayTime(seconds)
            if type(editor) is QLineEdit:
                editor.setText(time.as_time_str())
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if self._column_is_time_column_and_has_data(index):
            model.setData(index, DisplayTime(editor.text()).as_seconds())
        else:
            super().setModelData(editor, model, index)

    def createEditor(self, parent, option, index):
        if index.column() in self._read_only_columns:
            return None
        if self._column_is_time_column(index):
            lineEdit = QLineEdit(parent)
            lineEdit.editingFinished.connect(self.commitAndCloseEditor)
            return lineEdit
        else:
            return super().createEditor(parent, option, index)

    def _column_is_time_column_and_has_data(self, index):
        return self._column_is_time_column(index) \
               and index.model().data(index, Qt.DisplayRole)

    def _column_is_time_column(self, index):
        return (index.column() in self._time_columns)

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)


class Tracklist(QTableWidget):

    invalid_url = pyqtSignal(str)
    error_downloading = pyqtSignal(str)

    class Columns:
        url = 0
        title = 1
        track_length = 2
        start_time = 3
        read_only = [title, track_length]
        time = [track_length, start_time]

    def __init__(self, parent):
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self._setup_delegate()
        self._setup_signals()

    def add_track(self):
        self.insertRow(self.rowCount())

    @property
    def tracks(self):
        tracks = []
        for row in range(self.rowCount()):
            url_item = self.item(row, self.Columns.url)
            start_time_item = self.item(row, self.Columns.start_time)
            title_item = self.item(row, self.Columns.title)
            length_item = self.item(row, self.Columns.track_length)
            if url_item and start_time_item:
                url = url_item.text().strip()
                start_time = int(start_time_item.text())
                title = title_item.text() if title_item else ""
                length = length_item.text() if length_item else 0
                if url and start_time:
                    tracks.append(Track(url=url, start_time=start_time, title=title, length=length))
        return tracks

    def _setup_delegate(self):
        self.setItemDelegate(
            TrackDelegate(
                read_only_columns=self.Columns.read_only,
                time_columns=self.Columns.time
            )
        )

    def _setup_signals(self):
        self.cellChanged.connect(self._handle_cell_change)

    def _handle_cell_change(self, row, column):
        if column == self.Columns.url:
            url = self.item(row, column).text()
            self._update_row_with_video_info(url, row)

    def _update_row_with_video_info(self, url, row):
        try:
            track = FindMediaDescriptionService(url).execute()

            self._show_track_details(row, track)

        except MissingURL:
            pass
        except InvalidURL:
            self.invalid_url.emit(url)
            self._clear_out_invalid_url(row)
        except DownloadError:
            self.error_downloading.emit(url)
            self._clear_out_invalid_url(row)

    def _show_track_details(self, row, track):
        self.setItem(row, self.Columns.title, QTableWidgetItem(track.title))
        self.setItem(row, self.Columns.track_length, QTableWidgetItem(str(track.length)))
        self.setItem(row, self.Columns.start_time, QTableWidgetItem(str(track.start_time)))

    def _clear_out_invalid_url(self, row):
        self.setItem(row, self.Columns.url, QTableWidgetItem(""))

    def _last_row_index(self):
        return self.rowCount() - 1

