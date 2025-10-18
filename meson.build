project('rdp-session-manager',
        version: '0.1.0',
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

# Subdirectories
subdir('src')
subdir('data')
subdir('scripts')

# Summary
summary({
    'prefix': get_option('prefix'),
    'bindir': get_option('bindir'),
}, section: 'Directories')
