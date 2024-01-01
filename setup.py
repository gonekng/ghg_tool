from cx_Freeze import setup, Executable

packages = ['numpy', 'pandas', 'plotly', 'streamlit', 'streamlit_authenticator', 'streamlit_option_menu', 'sqlite3', 'yaml']
includes = []
excludes = ['pyinstaller']
includefiles = ['./gs_app.py', './gs_db.db', './config.yaml']

exe = [Executable('app_run.py', icon="icons.ico")]

setup(
    name = 'gs_app',
    version = '0.1',
    description = 'Scope3 GHG Emission Tool',
    author = 'ecoeye',
    author_email = 'donumm64@ecoeye.com',
    options = {'build_exe': {'packages':packages, 'excludes':excludes, 'include_files':includefiles}}, 
    executables = exe
)