"""Qt dialog; all FreeCAD operations remain on the GUI thread."""
from pathlib import Path
import traceback
from .manifest import load_manifest
from .compatibility import FreeCADAdapter
from .installer import Installer


def qt_modules():
    try:
        from PySide import QtCore, QtWidgets
    except ImportError:
        try:
            from PySide2 import QtCore, QtWidgets
        except ImportError:
            from PySide6 import QtCore, QtWidgets
    return QtCore, QtWidgets


def launch(root):
    import FreeCAD as App
    import FreeCADGui as Gui
    QtCore, QtWidgets = qt_modules()
    root = Path(root)
    collections = load_manifest(root / "libraries" / "manifest.json")
    adapter = FreeCADAdapter()
    backup = Path(App.getUserAppDataDir()) / "FreeCADCAMLibraries" / "backups"
    engine = Installer(adapter, backup, App.Version())

    class Dialog(QtWidgets.QDialog):
        def __init__(self):
            super().__init__(Gui.getMainWindow())
            self.busy = False
            self.setWindowTitle("FreeCAD CAM Tool Library Manager")
            self.resize(980, 760)
            layout = QtWidgets.QVBoxLayout(self)
            banner = QtWidgets.QLabel(f"FreeCAD {'.'.join(App.Version()[:3])} • Preview first • Existing tools and tool numbers are preserved")
            banner.setWordWrap(True); layout.addWidget(banner)
            self.tree = QtWidgets.QTreeWidget()
            self.tree.setHeaderLabels(["Collection", "Files / Expected", "Geometry"])
            layout.addWidget(self.tree)
            self.items = []
            for category in ("drills", "endmills", "threadmills"):
                parent = QtWidgets.QTreeWidgetItem(self.tree, [category.title()])
                for collection in collections:
                    if collection.category != category:
                        continue
                    available, count = collection.availability()
                    item = QtWidgets.QTreeWidgetItem(parent, [collection.name, f"{count} / {collection.expected_count}", collection.geometry["accuracy"]])
                    item.setToolTip(0, collection.geometry["notes"])
                    item.setCheckState(0, QtCore.Qt.Unchecked)
                    if not available:
                        item.setDisabled(True)
                        item.setText(2, "Unavailable — source files missing")
                    self.items.append((item, collection, available))
                parent.setExpanded(True)
            self.tree.setColumnWidth(0, 520)
            buttons = QtWidgets.QHBoxLayout()
            self.select_all = QtWidgets.QPushButton("Select All Available")
            self.clear = QtWidgets.QPushButton("Clear")
            self.preview_button = QtWidgets.QPushButton("Preview Selected Libraries")
            for button in (self.select_all, self.clear, self.preview_button):
                buttons.addWidget(button)
            layout.addLayout(buttons)
            self.preview = QtWidgets.QPlainTextEdit()
            self.preview.setReadOnly(True); self.preview.setMaximumHeight(160)
            layout.addWidget(self.preview)
            self.distinct = QtWidgets.QCheckBox("Keep different UUIDs as separate tools when definitions are equivalent (explicit duplicate policy)")
            layout.addWidget(self.distinct)
            self.dry = QtWidgets.QCheckBox("Dry-run: report planned changes without writing assets or backups")
            self.dry.setChecked(True); layout.addWidget(self.dry)
            self.install = QtWidgets.QPushButton("Install Selected Libraries")
            self.install.setEnabled(False); layout.addWidget(self.install)
            self.progress = QtWidgets.QProgressBar(); layout.addWidget(self.progress)
            self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); layout.addWidget(self.log)
            self.results = QtWidgets.QLabel("No installation performed.")
            self.results.setWordWrap(True); self.results.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            layout.addWidget(self.results)
            self.select_all.clicked.connect(lambda: self.mark(QtCore.Qt.Checked))
            self.clear.clicked.connect(lambda: self.mark(QtCore.Qt.Unchecked))
            self.tree.itemChanged.connect(self.selection_changed)
            self.preview_button.clicked.connect(lambda: self.run(True))
            self.install.clicked.connect(lambda: self.run(self.dry.isChecked()))
            self.selection_changed()

        def selected(self):
            return [c for item, c, available in self.items if available and item.checkState(0) == QtCore.Qt.Checked]

        def mark(self, state):
            for item, _, available in self.items:
                if available:
                    item.setCheckState(0, state)

        def selection_changed(self, *args):
            selected = self.selected()
            self.install.setEnabled(bool(selected) and not self.busy)
            self.preview_button.setEnabled(bool(selected) and not self.busy)
            lines = [f"Selected {len(selected)} collections; {sum(c.expected_count for c in selected)} source tools."]
            for collection in selected:
                lines.append(f"\n{collection.name}: {collection.geometry['notes']}")
            lines.append("\nUse Preview for duplicate checks and planned tool numbers. Data redistribution rights are unverified; this is a local development build.")
            self.preview.setPlainText("\n".join(lines))

        def append(self, message):
            self.log.appendPlainText(message)
            App.Console.PrintMessage(message + "\n")
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

        def update_progress(self, done, total):
            self.progress.setRange(0, max(total, 1)); self.progress.setValue(done)

        def reject(self):
            if not self.busy:
                super().reject()

        def closeEvent(self, event):
            if self.busy:
                event.ignore()
            else:
                super().closeEvent(event)

        def run(self, dry_run):
            selected = self.selected()
            if self.busy or not selected:
                return
            self.busy = True
            for widget in (self.tree, self.select_all, self.clear, self.preview_button, self.install, self.dry, self.distinct):
                widget.setEnabled(False)
            self.log.clear(); self.progress.setValue(0)
            try:
                report = engine.run(selected, dry_run, self.append, self.update_progress,
                                    equivalent_policy="distinct" if self.distinct.isChecked() else "skip")
                text = report.summary()
                if report.recovery_directory:
                    text += "\nBackups and report: " + report.recovery_directory
                if not dry_run:
                    text += "\nClose and reopen CAM Tool Bit Library to refresh. Verify tools again after restarting FreeCAD."
                self.results.setText(text)
                if dry_run:
                    self.preview.setPlainText(report.summary() + "\n\n" + "\n".join(report.errors))
            except Exception:
                self.append(traceback.format_exc())
                self.results.setText("Installation interrupted. Consult the log and recovery journal before retrying.")
            finally:
                self.busy = False
                for widget in (self.tree, self.select_all, self.clear, self.dry, self.distinct):
                    widget.setEnabled(True)
                self.install.setEnabled(bool(self.selected()))
                self.preview_button.setEnabled(bool(self.selected()))

    dialog = Dialog()
    # Keep a reference through the modal event loop on all supported bindings.
    return dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
