from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

added_files = [
    ("main.py", "."),
    ("data_processor.py", "."),
    ("visualizations.py", "."),
    ("holcim_logo_color.svg", "."),
    ("lafarge.png", "."),
]

added_files += collect_data_files("streamlit")

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        # Streamlit core — sans collect_submodules pour éviter le crash pytest
        "streamlit",
        "streamlit.runtime",
        "streamlit.runtime.scriptrunner",
        "streamlit.runtime.scriptrunner.magic_funcs",
        "streamlit.web",
        "streamlit.web.cli",
        "streamlit.components.v1",
        # Ton projet
        "data_processor",
        "visualizations",
        # Libs communes
        "pandas",
        "numpy",
        "plotly",
        "plotly.express",
        "altair",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
    "pytest", "_pytest", "py.test",
    "astropy", "astropy_iers_data",
    "tensorflow", "tensorflow_core", "keras",
    "torch", "torchvision",
    "sklearn", "scikit-learn",
    "matplotlib",
    "IPython", "ipykernel", "jupyter",
    "cv2", "PIL",
    "sympy",
    "numba", "llvmlite",
    ],   # ← exclure pytest explicitement
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LafargeDashboard",
    debug=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LafargeDashboard",
)