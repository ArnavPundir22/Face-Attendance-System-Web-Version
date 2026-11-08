from src import create_app
from src.utils.console_helpers import disable_windows_console_quickedit

# Early unfreeze safeguard for direct module execution or WSGI server startup
disable_windows_console_quickedit()

app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
