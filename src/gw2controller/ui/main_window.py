from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gw2controller.controller.xinput import (
    ALL_BUTTONS,
    BUTTON_LABELS,
    PadState,
)
from gw2controller.mapping.models import DEFAULT_LAYOUT_KEY, Action, Profile
from gw2controller.mapping.profiles import list_profiles, load_profile, save_profile
from gw2controller.overlay.glyphs import app_icon_pixmap
from gw2controller.overlay.window import screen_choices
from gw2controller.paths import PROFILES_DIR
from gw2controller.ui.binding_dialog import FunctionDialog, ModifierTab, OverrideLayerTab
from gw2controller.ui.gamepad_view import GamepadView
from gw2controller.gw2.mumble import MumbleState


class MainWindow(QMainWindow):
    overlay_edit_toggled = Signal()
    overlay_visibility_toggled = Signal()
    overlay_add_slot = Signal(str)
    overlay_layout_selected = Signal(str)
    profile_changed = Signal()
    profile_persisted = Signal()

    def __init__(self, profile: Profile, profile_path: Path) -> None:
        super().__init__()
        self.profile = profile
        self.profile_path = profile_path
        self.setWindowTitle("GW2Controller")
        self.setWindowIcon(QIcon(app_icon_pixmap(32)))
        self.resize(1040, 720)

        self._gamepad = GamepadView()
        self._name = QLineEdit(profile.name)
        self._profile_combo = QComboBox()
        self._status = QLabel("Procurando controle Xbox…")
        self._layer_label = QLabel("Camada: Padrão")
        self._mumble_label = QLabel("Jogo: sem sinal")
        self._table = QTableWidget(0, 4)
        self._tabs = QTabWidget()
        self._modifier_tabs: dict[tuple[str, str], ModifierTab] = {}
        self._long_press = QSpinBox()
        self._radial_dead = QDoubleSpinBox()
        self._trigger = QDoubleSpinBox()
        self._left_mode = QComboBox()
        self._right_mode = QComboBox()
        self._left_dead = QSlider(Qt.Orientation.Horizontal)
        self._right_dead = QSlider(Qt.Orientation.Horizontal)
        self._right_sens = QSlider(Qt.Orientation.Horizontal)
        self._left_dead_label = QLabel()
        self._right_dead_label = QLabel()
        self._right_sens_label = QLabel()
        self._slot_button = QComboBox()
        self._overlay_visible = QCheckBox("Mostrar sobreposição de skills")
        self._overlay_screen = QComboBox()
        self._overlay_theme = QComboBox()
        self._radial_alpha = QSlider(Qt.Orientation.Horizontal)
        self._radial_alpha_label = QLabel()
        self._item_size = QSlider(Qt.Orientation.Horizontal)
        self._item_size_label = QLabel()
        self._overlay_layout = QComboBox()
        self._current_buttons_enabled = QCheckBox("Mostrar botões pressionados")
        self._current_buttons_movable = QCheckBox("Permitir mover esse painel")
        self._long_rumble = QCheckBox("Vibrar ao ativar longo")

        self._build()
        self._build_menu()
        self._name.editingFinished.connect(self._rename_profile)
        self.reload_from_profile()
        self.refresh_profile_list()

    def _build(self) -> None:
        header = QHBoxLayout()
        self._profile_combo.currentIndexChanged.connect(self._load_selected_profile)
        save_btn = QPushButton("Salvar")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.save_current)
        save_as_btn = QPushButton("Salvar como…")
        save_as_btn.clicked.connect(self.save_as)
        header.addWidget(QLabel("Perfil"))
        header.addWidget(self._profile_combo, 1)
        header.addWidget(self._name, 1)
        header.addWidget(save_btn)
        header.addWidget(save_as_btn)

        info = QHBoxLayout()
        info.addWidget(self._status)
        info.addStretch()
        info.addWidget(self._mumble_label)
        info.addWidget(self._layer_label)

        self._tabs.addTab(self._build_buttons_tab(), "Botões")
        self._tabs.addTab(self._build_sticks_tab(), "Analógicos")
        self._map_open_tab = OverrideLayerTab(
            "Enquanto o mapa do mundo (tecla M) estiver aberto. "
            "Deixe em branco para manter a função normal do botão. "
            "Ordem: modificadora → mapa → chat → montaria → normal.",
            self.profile.context_layers.map_open,
        )
        self._chat_tab = OverrideLayerTab(
            "Enquanto o chat ou um campo de texto do jogo estiver ativo. "
            "Deixe em branco para manter a função normal do botão.",
            self.profile.context_layers.chat,
        )
        self._mounted_tab = OverrideLayerTab(
            "Enquanto o personagem estiver em uma montaria. "
            "Deixe em branco para manter a função normal do botão.",
            self.profile.context_layers.mounted,
        )
        self._map_open_tab.changed.connect(self._on_context_layer_changed)
        self._chat_tab.changed.connect(self._on_context_layer_changed)
        self._mounted_tab.changed.connect(self._on_context_layer_changed)
        self._tabs.addTab(self._map_open_tab, "Mapa aberto")
        self._tabs.addTab(self._chat_tab, "Chat")
        self._tabs.addTab(self._mounted_tab, "Montaria")
        self._tabs.addTab(self._build_overlay_tab(), "Sobreposição")
        self._tabs.addTab(self._build_options_tab(), "Opções")

        root = QVBoxLayout()
        root.addLayout(header)
        root.addWidget(self._gamepad, 0, Qt.AlignmentFlag.AlignHCenter)
        root.addLayout(info)
        root.addWidget(self._tabs, 1)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)
        self.statusBar().showMessage(
            "F8 — posicionar ícones  •  F9 — mostrar/ocultar  •  jogo em janela ou sem bordas"
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Arquivo")
        save_action = QAction("Salvar", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_current)
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

    def _build_buttons_tab(self) -> QWidget:
        hint = QLabel(
            "Ao apertar: a função fica ativa enquanto o botão estiver pressionado. "
            "Ao soltar: dispara uma tecla quando você solta o botão. "
            "Curto / Longo: soltar rápido = curto; segurar = longo. "
            "Modificadora (ex.: LB): enquanto segura, outros botões podem mudar de função "
            "(configure na aba Mod)."
        )
        hint.setWordWrap(True)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Botão", "Modo", "Função / Curto", "Ao soltar / Longo"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        layout = QVBoxLayout()
        layout.addWidget(hint)
        layout.addWidget(self._table)
        page = QWidget()
        page.setLayout(layout)
        return page

    def _build_sticks_tab(self) -> QWidget:
        left_box = QGroupBox("Analógico esquerdo")
        self._left_mode.addItem("WASD (movimento)", "wasd")
        self._left_mode.addItem("Setas", "arrows")
        self._left_mode.addItem("Mouse", "mouse")
        self._left_mode.addItem("Desligado", "off")
        self._left_dead.setRange(0, 50)
        left_form = QFormLayout(left_box)
        left_form.addRow("Modo", self._left_mode)
        left_form.addRow("Zona morta", self._left_dead)
        left_form.addRow("", self._left_dead_label)

        right_box = QGroupBox("Analógico direito")
        self._right_mode.addItem("Mouse (câmera)", "mouse")
        self._right_mode.addItem("Desligado", "off")
        self._right_dead.setRange(0, 50)
        self._right_sens.setRange(1, 40)
        right_form = QFormLayout(right_box)
        right_form.addRow("Modo", self._right_mode)
        right_form.addRow("Zona morta", self._right_dead)
        right_form.addRow("", self._right_dead_label)
        right_form.addRow("Sensibilidade", self._right_sens)
        right_form.addRow("", self._right_sens_label)

        self._left_mode.currentIndexChanged.connect(self._read_stick_controls)
        self._right_mode.currentIndexChanged.connect(self._read_stick_controls)
        self._left_dead.valueChanged.connect(self._read_stick_controls)
        self._right_dead.valueChanged.connect(self._read_stick_controls)
        self._right_sens.valueChanged.connect(self._read_stick_controls)

        grid = QGridLayout()
        grid.addWidget(left_box, 0, 0)
        grid.addWidget(right_box, 0, 1)
        page = QWidget()
        page.setLayout(grid)
        return page

    def _build_overlay_tab(self) -> QWidget:
        for button in ALL_BUTTONS:
            self._slot_button.addItem(BUTTON_LABELS.get(button, button), button)
        add_btn = QPushButton("Adicionar na tela")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(lambda: self.overlay_add_slot.emit(str(self._slot_button.currentData())))
        edit_btn = QPushButton("Posicionar (F8)")
        edit_btn.clicked.connect(self.overlay_edit_toggled.emit)
        hide_btn = QPushButton("Mostrar/ocultar (F9)")
        hide_btn.clicked.connect(self.overlay_visibility_toggled.emit)
        self._overlay_visible.toggled.connect(self._toggle_overlay_checkbox)
        self._refresh_screen_choices()
        self._overlay_screen.currentIndexChanged.connect(self._read_overlay_screen)
        self._overlay_theme.addItem("Escuro", "dark")
        self._overlay_theme.addItem("Claro", "light")
        self._overlay_theme.currentIndexChanged.connect(self._read_overlay_theme)
        self._radial_alpha.setRange(10, 100)
        self._radial_alpha.valueChanged.connect(self._read_radial_alpha)
        self._item_size.setRange(20, 96)
        self._item_size.valueChanged.connect(self._read_item_size)
        self._overlay_layout.currentIndexChanged.connect(self._read_overlay_layout)
        self._current_buttons_enabled.toggled.connect(self._read_current_buttons)
        self._current_buttons_movable.toggled.connect(self._read_current_buttons)

        hint = QLabel(
            "A sobreposição fica só na tela escolhida (melhor com dois monitores). "
            "Com F8, arraste os nomes dos botões por cima das skills. "
            "Cada modificadora (LB, RB…) pode ter posições próprias — escolha em “Layout ativo”. "
            "O jogo precisa estar em janela ou sem bordas."
        )
        hint.setWordWrap(True)

        screen_row = QHBoxLayout()
        screen_row.addWidget(QLabel("Tela"))
        screen_row.addWidget(self._overlay_screen, 1)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Tema"))
        theme_row.addWidget(self._overlay_theme, 1)

        layout_row = QHBoxLayout()
        layout_row.addWidget(QLabel("Layout ativo"))
        layout_row.addWidget(self._overlay_layout, 1)

        alpha_row = QHBoxLayout()
        alpha_row.addWidget(QLabel("Opacidade do menu radial"))
        alpha_row.addWidget(self._radial_alpha, 1)
        alpha_row.addWidget(self._radial_alpha_label)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Tamanho dos nomes"))
        size_row.addWidget(self._item_size, 1)
        size_row.addWidget(self._item_size_label)

        row = QHBoxLayout()
        row.addWidget(QLabel("Botão"))
        row.addWidget(self._slot_button)
        row.addWidget(add_btn)
        row.addWidget(edit_btn)
        row.addWidget(hide_btn)
        row.addStretch()

        current_box = QGroupBox("Painel de botões pressionados")
        current_layout = QVBoxLayout(current_box)
        current_layout.addWidget(self._current_buttons_enabled)
        current_layout.addWidget(self._current_buttons_movable)
        current_hint = QLabel(
            "Mostra o que você está apertando. "
            "Com modificadora + skill: “LB + A”. "
            "Se o botão não muda com a modificadora: só o botão. "
            "Nada pressionado: —. Em curto/longo, a cor sobe até o longo ativar."
        )
        current_hint.setWordWrap(True)
        current_layout.addWidget(current_hint)

        layout = QVBoxLayout()
        layout.addWidget(self._overlay_visible)
        layout.addLayout(screen_row)
        layout.addLayout(theme_row)
        layout.addLayout(layout_row)
        layout.addLayout(size_row)
        layout.addLayout(alpha_row)
        layout.addLayout(row)
        layout.addWidget(current_box)
        layout.addWidget(hint)
        layout.addStretch()
        page = QWidget()
        page.setLayout(layout)
        return page

    def _build_options_tab(self) -> QWidget:
        self._long_press.setRange(80, 1200)
        self._long_press.setSuffix(" ms")
        self._radial_dead.setRange(0.15, 0.8)
        self._radial_dead.setSingleStep(0.05)
        self._trigger.setRange(0.1, 0.95)
        self._trigger.setSingleStep(0.05)
        self._long_press.valueChanged.connect(self._read_options)
        self._radial_dead.valueChanged.connect(self._read_options)
        self._trigger.valueChanged.connect(self._read_options)
        self._long_rumble.toggled.connect(self._read_options)
        form = QFormLayout()
        form.addRow("Tempo curto / longo", self._long_press)
        form.addRow("Zona morta do menu radial", self._radial_dead)
        form.addRow("Sensibilidade dos gatilhos (LT/RT)", self._trigger)
        form.addRow(self._long_rumble)
        box = QGroupBox("Tempos e precisão")
        box.setLayout(form)
        hint = QLabel(
            "No menu radial, segure o botão e empurre o analógico direito. "
            "A câmera do stick direito pausa enquanto o menu estiver aberto. "
            "A vibração confirma quando o longo dispara."
        )
        hint.setWordWrap(True)
        layout = QVBoxLayout()
        layout.addWidget(box)
        layout.addWidget(hint)
        layout.addStretch()
        page = QWidget()
        page.setLayout(layout)
        return page

    def reload_from_profile(self) -> None:
        self._name.blockSignals(True)
        self._name.setText(self.profile.name)
        self._name.blockSignals(False)
        self._rebuild_table()
        self._sync_modifier_tabs()
        self._load_stick_controls()
        self._load_options()
        self._overlay_visible.blockSignals(True)
        self._overlay_visible.setChecked(self.profile.overlay.visible)
        self._overlay_visible.blockSignals(False)
        self._refresh_screen_choices()
        self._refresh_overlay_theme()
        self._refresh_radial_alpha()
        self._refresh_item_size()
        self._refresh_overlay_layout()
        self._refresh_current_buttons()
        self._map_open_tab.overrides = self.profile.context_layers.map_open
        self._chat_tab.overrides = self.profile.context_layers.chat
        self._mounted_tab.overrides = self.profile.context_layers.mounted
        self._map_open_tab.reload()
        self._chat_tab.reload()
        self._mounted_tab.reload()

    def refresh_profile_list(self) -> None:
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        paths = list_profiles()
        if self.profile_path not in paths:
            paths.append(self.profile_path)
        for path in paths:
            self._profile_combo.addItem(path.stem, str(path))
        index = self._profile_combo.findData(str(self.profile_path))
        if index >= 0:
            self._profile_combo.setCurrentIndex(index)
        self._profile_combo.blockSignals(False)

    def set_pad_state(self, pad: PadState, layer: str, mumble: MumbleState | None = None) -> None:
        self._gamepad.set_pad(pad)
        self._gamepad.set_layer(layer)
        if pad.connected:
            self._status.setText("Controle Xbox conectado")
        else:
            self._status.setText("Nenhum controle Xbox encontrado")
        self._layer_label.setText(f"Camada: {layer}")
        if mumble is not None:
            self._mumble_label.setText(mumble.status_label())

    def _on_context_layer_changed(self) -> None:
        self.profile.context_layers.map_open = self._map_open_tab.overrides
        self.profile.context_layers.chat = self._chat_tab.overrides
        self.profile.context_layers.mounted = self._mounted_tab.overrides
        self.profile_changed.emit()

    def save_current(self) -> None:
        self.profile.name = self._name.text().strip() or self.profile.name
        save_profile(self.profile, self.profile_path)
        self.refresh_profile_list()
        self.profile_persisted.emit()
        self.statusBar().showMessage(f"Salvo em {self.profile_path.name}", 3000)

    def save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar perfil",
            str(PROFILES_DIR),
            "Perfil JSON (*.json)",
        )
        if not path:
            return
        self.profile_path = Path(path)
        self.save_current()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        self.hide()

    def _rename_profile(self) -> None:
        self.profile.name = self._name.text().strip() or self.profile.name

    def _load_selected_profile(self) -> None:
        path_str = self._profile_combo.currentData()
        if not path_str:
            return
        path = Path(path_str)
        if path == self.profile_path:
            return
        try:
            self.profile = load_profile(path)
            self.profile_path = path
            self.reload_from_profile()
            self.profile_changed.emit()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Perfil", f"Não foi possível abrir o perfil:\n{exc}")

    def _rebuild_table(self) -> None:
        self._table.setRowCount(len(ALL_BUTTONS))
        for row, button in enumerate(ALL_BUTTONS):
            mapping = self.profile.button_map(button)
            label = QTableWidgetItem(BUTTON_LABELS.get(button, button))
            label.setFlags(label.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, label)

            mode = QComboBox()
            mode.addItem("Ao apertar", "press")
            mode.addItem("Curto / Longo", "short_long")
            mode.setCurrentIndex(1 if mapping.mode == "short_long" else 0)
            mode.currentIndexChanged.connect(lambda _i, b=button, c=mode: self._change_mode(b, str(c.currentData())))
            self._table.setCellWidget(row, 1, mode)

            if mapping.mode == "short_long":
                self._table.setCellWidget(row, 2, self._action_button(button, "short", mapping.short))
                self._table.setCellWidget(row, 3, self._action_button(button, "long", mapping.long))
            else:
                self._table.setCellWidget(row, 2, self._action_button(button, "press", mapping.press))
                self._table.setCellWidget(row, 3, self._action_button(button, "release", mapping.release))

    def _action_button(self, button: str, slot: str, action: Action) -> QPushButton:
        btn = QPushButton(action.label())
        btn.clicked.connect(lambda _=False, b=button, s=slot: self._edit_action(b, s))
        return btn

    def _change_mode(self, button: str, mode: str) -> None:
        mapping = self.profile.button_map(button)
        mapping.mode = "short_long" if mode == "short_long" else "press"
        if mapping.mode == "short_long" and not mapping.short.is_active() and mapping.press.is_active():
            mapping.short = mapping.press
        self.profile.set_button_map(button, mapping)
        self._rebuild_table()
        self._sync_modifier_tabs()
        self._refresh_overlay_layout()
        self.profile_changed.emit()

    def _edit_action(self, button: str, slot: str) -> None:
        mapping = self.profile.button_map(button)
        current = mapping.slot_action(slot)
        if slot == "release" and current.type not in ("keys", "none"):
            current = Action()
        dialog = FunctionDialog(current, self, keys_only=(slot == "release"))
        if slot == "release":
            dialog.setWindowTitle("Ao soltar o botão")
        if not dialog.exec():
            return
        result = dialog.result_action()
        if result.type == "modifier" and current.type == "modifier":
            result.overrides = current.overrides
        mapping.set_slot_action(slot, result)
        self.profile.set_button_map(button, mapping)
        self._rebuild_table()
        self._sync_modifier_tabs()
        self._refresh_overlay_layout()
        self.profile_changed.emit()

    def _sync_modifier_tabs(self) -> None:
        wanted = self.profile.modifier_sources()
        wanted_set = set(wanted)
        for key, tab in list(self._modifier_tabs.items()):
            if key not in wanted_set:
                index = self._tabs.indexOf(tab)
                if index >= 0:
                    self._tabs.removeTab(index)
                tab.deleteLater()
                self._modifier_tabs.pop(key, None)
        slot_names = {"press": "", "short": " (curto)", "long": " (longo)"}
        for button, slot in wanted:
            key = (button, slot)
            mapping = self.profile.button_map(button)
            action = mapping.slot_action(slot)
            if key in self._modifier_tabs:
                tab = self._modifier_tabs[key]
                tab.action = action
                tab.reload()
                continue
            tab = ModifierTab(button, action, self._tabs)
            tab.changed.connect(self.profile_changed.emit)
            label = BUTTON_LABELS.get(button, button)
            title = f"Mod {label}{slot_names.get(slot, '')}"
            self._tabs.addTab(tab, title)
            self._modifier_tabs[key] = tab

    def _load_options(self) -> None:
        self._long_press.blockSignals(True)
        self._radial_dead.blockSignals(True)
        self._trigger.blockSignals(True)
        self._long_rumble.blockSignals(True)
        self._long_press.setValue(self.profile.long_press_ms)
        self._radial_dead.setValue(self.profile.radial_deadzone)
        self._trigger.setValue(self.profile.trigger_threshold)
        self._long_rumble.setChecked(self.profile.long_press_rumble)
        self._long_press.blockSignals(False)
        self._radial_dead.blockSignals(False)
        self._trigger.blockSignals(False)
        self._long_rumble.blockSignals(False)

    def _read_options(self) -> None:
        self.profile.long_press_ms = self._long_press.value()
        self.profile.radial_deadzone = float(self._radial_dead.value())
        self.profile.trigger_threshold = float(self._trigger.value())
        self.profile.long_press_rumble = self._long_rumble.isChecked()
        self.profile_changed.emit()

    def _load_stick_controls(self) -> None:
        left = self.profile.sticks["left"]
        right = self.profile.sticks["right"]
        for combo, mode in ((self._left_mode, left.mode), (self._right_mode, right.mode)):
            combo.blockSignals(True)
            index = combo.findData(mode)
            combo.setCurrentIndex(max(0, index))
            combo.blockSignals(False)
        self._left_dead.blockSignals(True)
        self._right_dead.blockSignals(True)
        self._right_sens.blockSignals(True)
        self._left_dead.setValue(int(left.deadzone * 100))
        self._right_dead.setValue(int(right.deadzone * 100))
        self._right_sens.setValue(int(right.sensitivity))
        self._left_dead.blockSignals(False)
        self._right_dead.blockSignals(False)
        self._right_sens.blockSignals(False)
        self._update_stick_labels()

    def _read_stick_controls(self) -> None:
        left = self.profile.sticks["left"]
        right = self.profile.sticks["right"]
        left.mode = str(self._left_mode.currentData())  # type: ignore[assignment]
        right.mode = str(self._right_mode.currentData())  # type: ignore[assignment]
        left.deadzone = self._left_dead.value() / 100.0
        right.deadzone = self._right_dead.value() / 100.0
        right.sensitivity = float(self._right_sens.value())
        self._update_stick_labels()
        self.profile_changed.emit()

    def _update_stick_labels(self) -> None:
        self._left_dead_label.setText(f"{self._left_dead.value()}%")
        self._right_dead_label.setText(f"{self._right_dead.value()}%")
        self._right_sens_label.setText(str(self._right_sens.value()))

    def _toggle_overlay_checkbox(self, checked: bool) -> None:
        self.profile.overlay.visible = checked
        self.profile_changed.emit()

    def _refresh_screen_choices(self) -> None:
        self._overlay_screen.blockSignals(True)
        self._overlay_screen.clear()
        for index, label in screen_choices():
            self._overlay_screen.addItem(label, index)
        current = self.profile.overlay.screen_index
        found = self._overlay_screen.findData(current)
        self._overlay_screen.setCurrentIndex(found if found >= 0 else 0)
        self._overlay_screen.blockSignals(False)

    def _read_overlay_screen(self) -> None:
        data = self._overlay_screen.currentData()
        if data is None:
            return
        self.profile.overlay.screen_index = int(data)
        self.profile_changed.emit()

    def _refresh_overlay_theme(self) -> None:
        self._overlay_theme.blockSignals(True)
        found = self._overlay_theme.findData(self.profile.overlay.theme)
        self._overlay_theme.setCurrentIndex(found if found >= 0 else 0)
        self._overlay_theme.blockSignals(False)

    def _read_overlay_theme(self) -> None:
        data = self._overlay_theme.currentData()
        if data is None:
            return
        self.profile.overlay.theme = str(data)
        self.profile_changed.emit()

    def _refresh_radial_alpha(self) -> None:
        self._radial_alpha.blockSignals(True)
        self._radial_alpha.setValue(self.profile.overlay.radial_alpha)
        self._radial_alpha.blockSignals(False)
        self._radial_alpha_label.setText(f"{self.profile.overlay.radial_alpha}%")

    def _read_radial_alpha(self, value: int) -> None:
        self.profile.overlay.radial_alpha = int(value)
        self._radial_alpha_label.setText(f"{value}%")
        self.profile_changed.emit()

    def _refresh_item_size(self) -> None:
        self._item_size.blockSignals(True)
        self._item_size.setValue(self.profile.overlay.item_size)
        self._item_size.blockSignals(False)
        self._item_size_label.setText(f"{self.profile.overlay.item_size}px")

    def _read_item_size(self, value: int) -> None:
        size = int(value)
        self.profile.overlay.item_size = size
        for slot in self.profile.overlay.slots:
            slot.size = size
        for slots in self.profile.overlay.layouts.values():
            for slot in slots:
                slot.size = size
        self._item_size_label.setText(f"{size}px")
        self.profile_changed.emit()

    def _refresh_overlay_layout(self) -> None:
        current = self._overlay_layout.currentData()
        self._overlay_layout.blockSignals(True)
        self._overlay_layout.clear()
        self._overlay_layout.addItem("Padrão", DEFAULT_LAYOUT_KEY)
        for button, _slot in self.profile.modifier_sources():
            label = BUTTON_LABELS.get(button, button)
            if self._overlay_layout.findData(button) < 0:
                self._overlay_layout.addItem(f"Com {label}", button)
        for key in self.profile.overlay.layout_keys():
            if key == DEFAULT_LAYOUT_KEY:
                continue
            if self._overlay_layout.findData(key) < 0:
                friendly = BUTTON_LABELS.get(key, key)
                self._overlay_layout.addItem(f"Com {friendly}", key)
        found = self._overlay_layout.findData(current if current else DEFAULT_LAYOUT_KEY)
        self._overlay_layout.setCurrentIndex(found if found >= 0 else 0)
        self._overlay_layout.blockSignals(False)

    def _read_overlay_layout(self) -> None:
        data = self._overlay_layout.currentData()
        if data is None:
            return
        self.overlay_layout_selected.emit(str(data))

    def _refresh_current_buttons(self) -> None:
        self._current_buttons_enabled.blockSignals(True)
        self._current_buttons_movable.blockSignals(True)
        self._current_buttons_enabled.setChecked(self.profile.overlay.current_buttons_enabled)
        self._current_buttons_movable.setChecked(self.profile.overlay.current_buttons_movable)
        self._current_buttons_movable.setEnabled(self.profile.overlay.current_buttons_enabled)
        self._current_buttons_enabled.blockSignals(False)
        self._current_buttons_movable.blockSignals(False)

    def _read_current_buttons(self) -> None:
        enabled = self._current_buttons_enabled.isChecked()
        self.profile.overlay.current_buttons_enabled = enabled
        self.profile.overlay.current_buttons_movable = self._current_buttons_movable.isChecked()
        self._current_buttons_movable.setEnabled(enabled)
        self.profile_changed.emit()
