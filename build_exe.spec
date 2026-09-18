# -*- mode: python ; coding: utf-8 -*-
# ============================================================
#  VentaTienda – PyInstaller Spec File
#  Ejecutar con:
#    .venv\Scripts\pyinstaller.exe build_exe.spec
# ============================================================

import os
from kivy_deps import sdl2, glew, angle
from kivymd import hooks_path as kivymd_hooks_path

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[os.path.abspath('src')],           # Para encontrar database.py y theme.py
    binaries=[],
    datas=[
        ('src/ventatienda.kv', '.'),            # Archivo KV junto al ejecutable
        ('data/ventatienda_datos.db', 'data'),  # BD en subcarpeta data/
    ],
    hiddenimports=[
        # KivyMD – módulos que PyInstaller no detecta automáticamente
        'kivymd.uix.card',
        'kivymd.uix.label',
        'kivymd.uix.button',
        'kivymd.uix.dialog',
        'kivymd.uix.menu',
        'kivymd.uix.snackbar',
        'kivymd.uix.screen',
        'kivymd.uix.screenmanager',
        'kivymd.uix.boxlayout',
        'kivymd.uix.textfield',
        'kivymd.uix.toolbar',
        'kivymd.uix.tab',
        'kivymd.uix.bottomnavigation',
        'kivymd.uix.navigationdrawer',
        'kivymd.uix.gridlayout',
        'kivymd.uix.list',
        'kivymd.uix.selectioncontrol',
        'kivymd.uix.behaviors',
        'kivymd.uix.behaviors.hover_behavior',
        'kivymd.icon_definitions',
        'kivymd.font_definitions',
        'kivymd.theming',
        # Extras detectados en tu entorno
        'fpdf',
        'PIL._tkinter_finder',
    ],
    hookspath=[kivymd_hooks_path],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',   # No se usa, reduce tamaño
        'matplotlib',
        'numpy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VentaTienda',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,    # Sin ventana negra de consola al abrir
    icon=None,        # Opcional: icon='assets/icono.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    # DLLs de renderizado gráfico (sdl2, glew, angle para GPU AMD/Intel)
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins + angle.dep_bins)],
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VentaTienda',
)
