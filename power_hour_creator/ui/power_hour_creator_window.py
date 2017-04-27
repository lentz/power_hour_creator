import os

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtSql import QSqlTableModel
from PyQt5.QtWidgets import QMainWindow, QHeaderView, QFileDialog, QDialog, \
    QMessageBox

from power_hour_creator import config
from power_hour_creator.media import CreatePowerHourService, PowerHour
from power_hour_creator.resources import image_path
from power_hour_creator.ui.power_hour_list import PowerHourModel
from power_hour_creator.ui.tracklist import TracklistModel, TrackDelegate
from .forms.mainwindow import Ui_mainWindow
from .forms.power_hour_export_dialog import Ui_PowerHourExportDialog

class PowerHourCreatorWindow(QMainWindow, Ui_mainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self._setup_power_hour_list_view()
        self._setup_tracklist()
        self._connect_create_power_hour_button()
        self._connect_track_errors()
        self._enable_create_power_hour_button_when_tracks_present()
        self._connect_help_menu()
        self._connect_file_menu()
        self._connect_power_hour_list_view()
        self.setWindowIcon(QIcon(image_path('Beer-80.png')))

    def _setup_tracklist(self):
        self._setup_tracklist_model()
        self._setup_tracklist_delegate()
        self._setup_tracklist_appearance()

    def _setup_power_hour_list_view(self):
        self.power_hour_model = PowerHourModel(self)
        self.power_hour_model.setTable('power_hours')
        self.power_hour_model.setEditStrategy(QSqlTableModel.OnFieldChange)
        self.power_hour_model.select()

        self.powerHoursListView.setModel(self.power_hour_model)
        self.powerHoursListView.setModelColumn(1)

        self.power_hour_model.rowsInserted.connect(self.powerHoursListView.select_new_power_hour)

    def _setup_tracklist_delegate(self):
        delegate = TrackDelegate(
            read_only_columns=self.tracklist_model.Columns.read_only,
            time_columns=self.tracklist_model.Columns.time,
            boolean_columns=self.tracklist_model.Columns.checkbox
        )
        self.tracklist.setItemDelegate(delegate)

    def _setup_tracklist_appearance(self):
        self.tracklist.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)

    def _setup_tracklist_model(self):
        self.tracklist_model = TracklistModel(self)
        self.tracklist_model.setTable("tracks")
        self.tracklist_model.setEditStrategy(QSqlTableModel.OnFieldChange)
        self.tracklist_model.select()

        self.tracklist_model.setHeaderData(self.tracklist_model.Columns.url, Qt.Horizontal, "URL")
        self.tracklist_model.setHeaderData(self.tracklist_model.Columns.title, Qt.Horizontal, "Title")
        self.tracklist_model.setHeaderData(self.tracklist_model.Columns.length, Qt.Horizontal, "Duration")
        self.tracklist_model.setHeaderData(self.tracklist_model.Columns.start_time, Qt.Horizontal, "Start Time")
        self.tracklist_model.setHeaderData(self.tracklist_model.Columns.full_song, Qt.Horizontal, "Full Song?")

        self.tracklist.setModel(self.tracklist_model)
        self.tracklist.hideColumn(0)  # id
        self.tracklist.hideColumn(1)  # position
        self.tracklist.hideColumn(7)  # power_hour_id

    def _connect_create_power_hour_button(self):
        self.createPowerHourButton.clicked.connect(self._export_power_hour)

    def _connect_track_errors(self):
        self.tracklist.invalid_url.connect(self._show_invalid_url)
        self.tracklist.error_downloading.connect(self._show_error_downloading)

    def _enable_create_power_hour_button_when_tracks_present(self):
        self.tracklist_model.power_hour_changed.connect(self._try_to_enable_create_button_on_tracklist_change)
        self.tracklist_model.dataChanged.connect(self._try_to_enable_create_button_on_tracklist_change)
        self._try_to_enable_create_button_on_tracklist_change()

    def _try_to_enable_create_button_on_tracklist_change(self):
        self.createPowerHourButton.setEnabled(self.tracklist_model.has_tracks())

    def _show_invalid_url(self, url):
        self.statusBar.showMessage('URL "{}" is invalid'.format(url))

    def _show_error_downloading(self, url):
        self.statusBar.showMessage('Error downloading "{}"'.format(url))

    def _show_worker_error(self, message):
        msg = QMessageBox(self)
        msg.setText('Error occured')
        msg.setDetailedText(message)
        msg.show()

    def _export_power_hour(self):
        is_video = self.videoCheckBox.checkState()
        power_hour_path = self.get_power_hour_path(is_video=is_video)
        if power_hour_path:
            power_hour = PowerHour(self.tracklist_model.tracks, power_hour_path, is_video)
            thread = PowerHourExportThread(self, power_hour)
            progress_dialog = ExportPowerHourDialog(self, power_hour)

            thread.progress.connect(progress_dialog.overallProgressBar.setValue)
            thread.new_track_downloading.connect(progress_dialog.show_new_downloading_track)
            thread.track_download_progress.connect(progress_dialog.show_track_download_progress)
            thread.error.connect(self._show_worker_error)
            thread.finished.connect(progress_dialog.close)
            thread.finished.connect(self._show_finished_status)
            thread.finished.connect(thread.deleteLater)

            progress_dialog.show()
            thread.start()

    def get_power_hour_path(self, is_video):
        if is_video:
            return QFileDialog.getSaveFileName(self, "Export Power Hour",
                                               os.path.expanduser('~/Videos'),
                                               "Video (*.mp4)")[0]
        else:
            return QFileDialog.getSaveFileName(self, "Export Power Hour",
                                               os.path.expanduser('~/Music'),
                                               "Audio (*.m4a)")[0]

    def _show_finished_status(self):
        self.statusBar.showMessage("Power hour created!", 5000)

    def _connect_help_menu(self):
        def show_logs():
            os.startfile(config.APP_DIRS.user_log_dir, 'explore')
        self.actionShow_logs.triggered.connect(show_logs)

    def _connect_file_menu(self):
        def new_power_hour():
            power_hour_id = self.power_hour_model.add_power_hour()
            self.tracklist_model.add_tracks_to_new_power_hour(power_hour_id)
            self.tracklist_model.show_tracks_for_power_hour(power_hour_id)

        self.actionNew_Power_Hour.triggered.connect(new_power_hour)

    def _connect_power_hour_list_view(self):
        def show_power_hour_name(new_index, _=None):
            ph_name = new_index.data()
            self.powerHourNameLabel.setText(ph_name)

        def show_renamed_power_hour_name(top_left_index, _):
            current_selection = self.powerHoursListView.selectionModel().selectedIndexes()
            if top_left_index in current_selection:
                show_power_hour_name(top_left_index)

        def show_this_power_hours_tracks(new_index, _):
            ph_id = new_index.sibling(new_index.row(), 0).data()
            self.tracklist_model.show_tracks_for_power_hour(ph_id)

        self.powerHoursListView.selectionModel().currentRowChanged.connect(show_power_hour_name)
        self.powerHoursListView.selectionModel().currentRowChanged.connect(show_this_power_hours_tracks)
        self.powerHoursListView.model().dataChanged.connect(show_renamed_power_hour_name)


class ExportPowerHourDialog(QDialog, Ui_PowerHourExportDialog):
    def __init__(self, parent, power_hour):
        QDialog.__init__(self, parent)
        Ui_PowerHourExportDialog.__init__(self)
        self.setupUi(self)

        self._power_hour = power_hour

        self._setup_signals()
        self._setup_progress_bar()

    def _setup_progress_bar(self):
        self.overallProgressBar.setMaximum(len(self._power_hour.tracks))

    def _setup_signals(self):
        self.cancelButton.clicked.connect(self.close)

    def show_new_downloading_track(self, track):
        self.currentSongLabel.setText("Downloading: {}".format(track.title))
        self.currentSongProgressBar.reset()

    def show_track_download_progress(self, downloaded_bytes, total_bytes):
        if self.currentSongProgressBar.maximum() != total_bytes:
            self.currentSongProgressBar.setMaximum(total_bytes)

        self.currentSongProgressBar.setValue(downloaded_bytes)


class PowerHourExportThread(QThread):

    progress = pyqtSignal(int)
    new_track_downloading = pyqtSignal(object)
    finished = pyqtSignal()
    track_download_progress = pyqtSignal(object, object)
    error = pyqtSignal(object)

    def __init__(self, parent, power_hour):
        super().__init__(parent)
        self._power_hour = power_hour

    def run(self):
        service = CreatePowerHourService(
            power_hour=self._power_hour,
            progress_listener=self)

        service.execute()

        self.finished.emit()

    def on_new_track_downloading(self, download_number, track):
        self.progress.emit(download_number)
        self.new_track_downloading.emit(track)

    def on_download_progress(self, info):
        total_bytes = 1
        if 'total_bytes_estimate' in info:
            total_bytes = info['total_bytes_estimate']
        elif 'total_bytes' in info:
            total_bytes = info['total_bytes']
        self.track_download_progress.emit(info['downloaded_bytes'], total_bytes)

    def on_service_error(self, message):
        self.error.emit(message)

