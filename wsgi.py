from src.utils.console_helpers import disable_windows_console_quickedit

# Early console unfreeze safeguard for WSGI entrypoint
disable_windows_console_quickedit()

from src import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
