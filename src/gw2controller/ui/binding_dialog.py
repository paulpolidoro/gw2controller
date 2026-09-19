from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gw2controller.controller.xinput import ALL_BUTTONS, BUTTON_LABELS
from gw2controller.mapping.models import MAX_RADIAL_ITEMS, Action, RadialItem
from gw2controller.output.sendinput import (
    key_display_name,
    key_name_from_native_vk,
    normalize_key_name,
    resolve_vk,
)

MOUSE_OPTIONS = [
    ("mouse_left", "Mouse esquerdo"),
    ("mouse_right", "Mouse direito"),
    ("mouse_middle", "Mouse meio"),
    ("mouse_x1", "Mouse 4"),
    ("mouse_x2", "Mouse 5"),
]


class KeyCaptureEdit(QLineEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.key_name = ""
        self.setPlaceholderText("Clique e pressione uma tecla")
        self.setReadOnly(True)

    def set_key(self, name: str) -> None:
        self.key_name = normalize_key_name(name) if name else ""
        self.setText(key_display_name(self.key_name) if self.key_name else "")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        name = _qt_key_to_name(event)
        if name:
            self.set_key(name)
            event.accept()
            return
        super().keyPressEvent(event)


def _qt_key_to_name(event: QKeyEvent) -> str | None:
    native = key_name_from_native_vk(int(event.nativeVirtualKey()))
    if native:
        return native

    keypad = bool(event.modifiers() & Qt.KeyboardModifier.KeypadModifier)
    key = event.key()
    if keypad:
        numpad = _qt_numpad_name(key)
        if numpad:
            return numpad

    mapping = {
        Qt.Key.Key_Space: "space",
        Qt.Key.Key_Return: "enter",
        Qt.Key.Key_Enter: "numpad_enter" if keypad else "enter",
        Qt.Key.Key_Escape: "escape",
        Qt.Key.Key_Tab: "tab",
        Qt.Key.Key_Backspace: "backspace",
        Qt.Key.Key_Shift: "shift",
        Qt.Key.Key_Control: "ctrl",
        Qt.Key.Key_Alt: "alt",
        Qt.Key.Key_Insert: "insert",
        Qt.Key.Key_Delete: "delete",
        Qt.Key.Key_Home: "home",
        Qt.Key.Key_End: "end",
        Qt.Key.Key_PageUp: "pageup",
        Qt.Key.Key_PageDown: "pagedown",
        Qt.Key.Key_Up: "up",
        Qt.Key.Key_Down: "down",
        Qt.Key.Key_Left: "left",
        Qt.Key.Key_Right: "right",
        Qt.Key.Key_Minus: "-",
        Qt.Key.Key_Equal: "=",
        Qt.Key.Key_Comma: ",",
        Qt.Key.Key_Period: ".",
        Qt.Key.Key_Slash: "/",
        Qt.Key.Key_Semicolon: ";",
        Qt.Key.Key_Apostrophe: "'",
        Qt.Key.Key_BracketLeft: "[",
        Qt.Key.Key_BracketRight: "]",
        Qt.Key.Key_Backslash: "\\",
        Qt.Key.Key_QuoteLeft: "`",
    }
    if key in mapping:
        return mapping[key]
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
        return f"f{key - Qt.Key.Key_F1 + 1}"
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return chr(ord("0") + (key - Qt.Key.Key_0))
    text = event.text()
    if text and resolve_vk(text):
        return normalize_key_name(text)
    return None


def _qt_numpad_name(key: int) -> str | None:
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return f"numpad{key - Qt.Key.Key_0}"
    ops = {
        Qt.Key.Key_Asterisk: "numpad_multiply",
        Qt.Key.Key_Plus: "numpad_add",
        Qt.Key.Key_Minus: "numpad_subtract",
        Qt.Key.Key_Period: "numpad_decimal",
        Qt.Key.Key_Comma: "numpad_decimal",
        Qt.Key.Key_Slash: "numpad_divide",
        Qt.Key.Key_Enter: "numpad_enter",
    }
    return ops.get(key)


class KeysEditor(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[KeyCaptureEdit] = []
        self._list = QVBoxLayout()
        self._list.setContentsMargins(0, 0, 0, 0)
        add = QPushButton("Adicionar tecla")
        add.clicked.connect(lambda: self._add_row(""))
        mouse = QComboBox()
        mouse.addItem("Adicionar clique…", "")
        for value, label in MOUSE_OPTIONS:
            mouse.addItem(label, value)
        mouse.currentIndexChanged.connect(lambda: self._add_mouse(mouse))
        row = QHBoxLayout()
        row.addWidget(add)
        row.addWidget(mouse)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._list)
        layout.addLayout(row)

    def set_keys(self, keys: list[str]) -> None:
        while self._rows:
            self._remove_last()
        for key in keys or [""]:
            self._add_row(key)
        if not self._rows:
            self._add_row("")

    def keys(self) -> list[str]:
        return [editor.key_name for editor in self._rows if editor.key_name]

    def _add_row(self, key: str) -> None:
        editor = KeyCaptureEdit()
        editor.set_key(key)
        remove = QPushButton("X")
        remove.setFixedWidth(32)
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(editor, 1)
        box.addWidget(remove)
        remove.clicked.connect(lambda: self._remove_row(row, editor))
        self._list.addWidget(row)
        self._rows.append(editor)

    def _add_mouse(self, combo: QComboBox) -> None:
        value = str(combo.currentData() or "")
        combo.setCurrentIndex(0)
        if value:
            self._add_row(value)

    def _remove_row(self, row: QWidget, editor: KeyCaptureEdit) -> None:
        if editor in self._rows:
            self._rows.remove(editor)
        row.deleteLater()
        if not self._rows:
            self._add_row("")

    def _remove_last(self) -> None:
        if not self._rows:
            return
        editor = self._rows.pop()
        item = self._list.takeAt(self._list.count() - 1)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        editor.deleteLater()


class FunctionDialog(QDialog):
    def __init__(self, action: Action, parent: QWidget | None = None, *, keys_only: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle("Função do botão")
        self.setModal(True)
        self.resize(480, 520 if not keys_only else 280)
        self._none = QRadioButton("Nenhuma")
        self._keys = QRadioButton("Tecla(s)")
        self._modifier = QRadioButton("Modificadora")
        self._radial = QRadioButton("Radial select")
        self._keys_editor = KeysEditor()
        self._radial_table = QTableWidget(MAX_RADIAL_ITEMS, 2)
        self._radial_table.setHorizontalHeaderLabels(["Nome", "Teclas (ex: shift+1)"])
        self._radial_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._mod_hint = QLabel(
            "Enquanto este botão estiver ativo, os outros botões usam os overrides da aba Mod. "
            "Os que você não alterar continuam com a função base."
        )
        self._mod_hint.setWordWrap(True)
        self._radial_hint = QLabel(
            "Até 8 itens. Segure o botão e use o analógico direito para escolher. "
            "Ao soltar, dispara as teclas do item. Deixe a linha vazia para não usar o setor."
        )
        self._radial_hint.setWordWrap(True)

        form = QFormLayout()
        form.addRow(self._none)
        form.addRow(self._keys)
        form.addRow(self._keys_editor)
        form.addRow(self._modifier)
        form.addRow(self._mod_hint)
        form.addRow(self._radial)
        form.addRow(self._radial_hint)
        form.addRow(self._radial_table)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(box)

        self._original = action
        self._keys_only = keys_only
        if keys_only:
            for widget in (self._modifier, self._mod_hint, self._radial, self._radial_hint, self._radial_table):
                widget.setVisible(False)
        self._load(action)
        for radio in (self._none, self._keys, self._modifier, self._radial):
            radio.toggled.connect(self._sync_enabled)
        self._sync_enabled()

    def _load(self, action: Action) -> None:
        if action.type == "keys":
            self._keys.setChecked(True)
            self._keys_editor.set_keys(action.keys)
        elif action.type == "modifier":
            self._modifier.setChecked(True)
            self._keys_editor.set_keys([])
        elif action.type == "radial":
            self._radial.setChecked(True)
            self._keys_editor.set_keys([])
            items = list(action.radial_items)
            while len(items) < MAX_RADIAL_ITEMS:
                items.append(RadialItem())
            for row, item in enumerate(items[:MAX_RADIAL_ITEMS]):
                self._radial_table.setItem(row, 0, QTableWidgetItem(item.label))
                self._radial_table.setItem(row, 1, QTableWidgetItem("+".join(item.keys)))
        else:
            self._none.setChecked(True)
            self._keys_editor.set_keys([])

    def _sync_enabled(self) -> None:
        self._keys_editor.setEnabled(self._keys.isChecked())
        self._mod_hint.setEnabled(self._modifier.isChecked())
        radial = self._radial.isChecked()
        self._radial_table.setEnabled(radial)
        self._radial_hint.setEnabled(radial)

    def result_action(self) -> Action:
        if self._keys_only and self._modifier.isChecked():
            return Action()
        if self._keys_only and self._radial.isChecked():
            return Action()
        if self._keys.isChecked():
            return Action(type="keys", keys=self._keys_editor.keys())
        if self._modifier.isChecked():
            overrides = self._original.overrides if self._original.type == "modifier" else {}
            return Action(type="modifier", overrides=dict(overrides))
        if self._radial.isChecked():
            items: list[RadialItem] = []
            for row in range(MAX_RADIAL_ITEMS):
                name_item = self._radial_table.item(row, 0)
                keys_item = self._radial_table.item(row, 1)
                raw = (keys_item.text() if keys_item else "").replace(",", "+")
                keys = [part.strip().lower() for part in raw.split("+") if part.strip()]
                items.append(
                    RadialItem(
                        label=(name_item.text().strip() if name_item else ""),
                        keys=keys,
                    )
                )
            return Action(type="radial", radial_items=items)
        return Action()


class ModifierTab(QWidget):
    changed = Signal()

    def __init__(self, owner_button: str, action: Action, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.owner_button = owner_button
        self.action = action
        self._layer = OverrideLayerTab(
            title_hint=(
                f"Overrides de {BUTTON_LABELS.get(owner_button, owner_button)}. "
                "Vazio = mantém a função base do botão."
            ),
            overrides=action.overrides,
            exclude_button=owner_button,
            parent=self,
        )
        self._layer.changed.connect(self.changed.emit)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._layer)

    def reload(self) -> None:
        self._layer.overrides = self.action.overrides
        self._layer.reload()


class OverrideLayerTab(QWidget):
    changed = Signal()

    def __init__(
        self,
        title_hint: str,
        overrides: dict[str, Action],
        parent: QWidget | None = None,
        *,
        exclude_button: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.overrides = overrides
        self._exclude = exclude_button
        hint = QLabel(title_hint)
        hint.setWordWrap(True)
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Botão", "Teclas", ""])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self._table)
        self.reload()

    def reload(self) -> None:
        buttons = [button for button in ALL_BUTTONS if button != self._exclude]
        self._table.setRowCount(len(buttons))
        for row, button in enumerate(buttons):
            label = QTableWidgetItem(BUTTON_LABELS.get(button, button))
            label.setFlags(label.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, label)
            override = self.overrides.get(button, Action())
            current = QTableWidgetItem(override.label() if override.is_active() else "Função base")
            current.setFlags(current.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, current)
            edit = QPushButton("Definir")
            clear = QPushButton("Base")
            cell = QWidget()
            box = QHBoxLayout(cell)
            box.setContentsMargins(4, 2, 4, 2)
            box.addWidget(edit)
            box.addWidget(clear)
            edit.clicked.connect(lambda _=False, b=button: self._edit(b))
            clear.clicked.connect(lambda _=False, b=button: self._clear(b))
            self._table.setCellWidget(row, 2, cell)

    def _edit(self, button: str) -> None:
        current = self.overrides.get(button, Action())
        if current.type not in ("keys", "none"):
            current = Action(type="keys", keys=current.keys)
        dialog = FunctionDialog(current if current.type == "keys" else Action(type="keys"), self, keys_only=True)
        if dialog.exec():
            result = dialog.result_action()
            if result.type == "keys" and result.is_active():
                self.overrides[button] = result
            else:
                self.overrides.pop(button, None)
            self.reload()
            self.changed.emit()

    def _clear(self, button: str) -> None:
        self.overrides.pop(button, None)
        self.reload()
        self.changed.emit()
