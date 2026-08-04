# Desktop file
desktop_file = 'com.rdp.SessionManager.desktop'
desktop_conf = configuration_data()
desktop_conf.set('bindir', get_option('bindir'))

configured_desktop = configure_file(
    input: desktop_file + '.in',
    output: desktop_file,
    configuration: desktop_conf,
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications')
)

# AppData file
appdata_file = 'com.rdp.SessionManager.appdata.xml'
install_data(
    appdata_file,
    install_dir: join_paths(get_option('datadir'), 'metainfo')
)

# PolicyKit policy
polkit_policy = 'com.rdp.SessionManager.policy'
install_data(
    polkit_policy,
    install_dir: join_paths(get_option('datadir'), 'polkit-1', 'actions')
)

# GSettings schema
gschema_file = 'com.rdp.SessionManager.gschema.xml'
install_data(
    gschema_file,
    install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)

install_subdir(
    'windows-app-recipes',
    install_dir: join_paths(get_option('datadir'), 'rdp-session-manager')
)

# UI files
subdir('ui')
subdir('icons')
