# Install helper scripts
scripts = [
    'rdp-session-helper.py',
]

foreach script : scripts
    configure_file(
        input: script,
        output: script,
        configuration: conf,
        install: true,
        install_dir: get_option('libexecdir')
    )
endforeach
