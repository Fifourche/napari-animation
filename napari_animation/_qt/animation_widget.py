from pathlib import Path

from napari import Viewer
from qtpy.QtWidgets import QErrorMessage, QPushButton, QVBoxLayout, QWidget

from ..animation import Animation
from .frame_widget import FrameWidget
from .frameslider_widget import QtFrameSliderWidget
from .keyframelistcontrol_widget import KeyFrameListControlWidget
from .keyframeslist_widget import KeyFramesListWidget
from .savedialog_widget import SaveDialogWidget


class AnimationWidget(QWidget):
    """Widget for interatviely making animations using the napari viewer.

    Parameters
    ----------
    viewer : napari.Viewer
        napari viewer.

    Attributes
    ----------
    viewer : napari.Viewer
        napari viewer.
    animation : napari_animation.Animation
        napari-animation animation in sync with the GUI.
    """

    def __init__(self, viewer: Viewer, parent=None):
        super().__init__(parent=parent)
        # Store reference to viewer and create animation
        self.viewer = viewer
        self.animation = Animation(self.viewer)

        # Initialise User Interface
        self.keyframesListControlWidget = KeyFrameListControlWidget(
            animation=self.animation, parent=self
        )
        self.keyframesListWidget = KeyFramesListWidget(
            self.animation.key_frames, parent=self
        )
        self.frameWidget = FrameWidget(parent=self)
        self.saveButton = QPushButton("Save Animation", parent=self)
        self.saveButton.setEnabled(len(self.animation.key_frames) > 1)
        self.frameSliderWidget = QtFrameSliderWidget(
            parent=self, frames=self.animation._frames, viewer=self.viewer
        )

        # Create layout
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.keyframesListControlWidget)
        self.layout().addWidget(self.keyframesListWidget)
        self.layout().addWidget(self.frameWidget)
        self.layout().addWidget(self.saveButton)
        self.layout().addWidget(self.frameSliderWidget)

        # establish key bindings and callbacks
        self._add_keybind_callbacks()
        self._add_callbacks()

    def _add_keybind_callbacks(self):
        """Bind keys"""
        self._keybindings = [
            ("Alt-f", self._capture_keyframe_callback),
            ("Alt-r", self._replace_keyframe_callback),
            ("Alt-d", self._delete_keyframe_callback),
            ("Alt-a", lambda e: self.animation.key_frames.select_next()),
            ("Alt-b", lambda e: self.animation.key_frames.select_previous()),
        ]
        for key, cb in self._keybindings:
            self.viewer.bind_key(key, cb)

    def _add_callbacks(self):
        """Establish callbacks"""
        self.keyframesListControlWidget.deleteButton.clicked.connect(
            self._delete_keyframe_callback
        )
        self.keyframesListControlWidget.captureButton.clicked.connect(
            self._capture_keyframe_callback
        )
        self.saveButton.clicked.connect(self._save_callback)

        keyframe_list = self.animation.key_frames
        keyframe_list.events.inserted.connect(self._on_keyframes_changed)
        keyframe_list.events.removed.connect(self._on_keyframes_changed)
        keyframe_list.events.changed.connect(self._on_keyframes_changed)
        keyframe_list.selection.events.active.connect(
            self._on_active_keyframe_changed
        )

    def _input_state(self):
        """Get current state of input widgets as {key->value} parameters."""
        return {
            "steps": int(self.frameWidget.stepsSpinBox.value()),
            "ease": self.frameWidget.get_easing_func(),
        }

    def _capture_keyframe_callback(self, event=None):
        """Record current key-frame"""
        self.animation.capture_keyframe(**self._input_state())

    def _replace_keyframe_callback(self, event=None):
        """Replace current key-frame with new view"""
        self.animation.capture_keyframe(**self._input_state(), insert=False)

    def _delete_keyframe_callback(self, event=None):
        """Delete current key-frame"""
        if self.animation.key_frames.selection.active:
            self.animation.key_frames.remove_selected()
        else:
            raise ValueError("No selected keyframe to delete !")

    def _on_keyframes_changed(self, event=None):
        n_keyframes = len(self.animation.key_frames)
        has_frames = bool(self.animation.key_frames)

        self.keyframesListControlWidget.deleteButton.setEnabled(has_frames)
        self.keyframesListWidget.setEnabled(has_frames)
        self.frameWidget.setEnabled(has_frames)
        self.saveButton.setEnabled(n_keyframes > 1)

    def _on_active_keyframe_changed(self, event):
        """Callback on change of active keyframe in the key frames list."""
        active_keyframe = event.value
        self.keyframesListControlWidget.deleteButton.setEnabled(
            bool(active_keyframe)
        )

    def _save_callback(self, event=None):

        filters = (
            "MP4 (*.mp4)"
            ";;GIF (*.gif)"
            ";;MOV (*.mov)"
            ";;AVI (*.avi)"
            ";;MPEG (*.mpg *.mpeg)"
            ";;MKV (*.mkv)"
            ";;WMV (*.wmv)"
            ";;Folder of PNGs (*)"  # sep filters with ";;"
        )

        saveDialogWidget = SaveDialogWidget(self)
        animation_kwargs = saveDialogWidget.getAnimationParameters(
            self, "Save animation", str(Path.home()), filters
        )

        if animation_kwargs["path"]:
            try:
                self.animation.animate(**animation_kwargs)
            except ValueError as err:
                # Should handle other types, differently maybe
                error_dialog = QErrorMessage()
                error_dialog.showMessage(str(err))
                error_dialog.exec_()

    def closeEvent(self, ev) -> None:
        # release callbacks
        for key, _ in self._keybindings:
            self.viewer.bind_key(key, None)
        return super().closeEvent(ev)
