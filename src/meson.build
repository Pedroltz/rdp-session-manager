# Install Python source files
python_sources = [
    '__init__.py',
    'main.py',
    'application.py',
    'cli.py',
]

py_installation.install_sources(
    python_sources,
    subdir: 'rdp_session_manager'
)

# Install submodules
subdir('core')
subdir('ui')
subdir('utils')
