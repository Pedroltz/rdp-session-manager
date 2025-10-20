project('rdp-session-manager',
        version: '0.2.0',
        meson_version: '>= 0.59.0')

# Python installation directory
py_installation = import('python').find_installation('python3')

# Dependencies
gnome = import('gnome')

# Project configuration
conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('PACKAGE_NAME', meson.project_name())
conf.set('PYTHON', py_installation.full_path())
conf.set('PKGDATADIR', join_paths(get_option('prefix'), get_option('datadir'), meson.project_name()))

# Configure and install CLI script
cli_conf = configuration_data()
cli_conf.set('PYTHON', py_installation.full_path())
cli_conf.set('PKGDATADIR', join_paths(get_option('prefix'), get_option('datadir'), meson.project_name()))

configure_file(
    input: 'rdpsm.in',
    output: 'rdpsm',
    configuration: cli_conf,
    install: true,
    install_dir: get_option('bindir')
)

# Subdirectories
subdir('src')
subdir('data')
subdir('scripts')

# Summary
summary({
    'prefix': get_option('prefix'),
    'bindir': get_option('bindir'),
    'datadir': get_option('datadir'),
}, section: 'Directories')
