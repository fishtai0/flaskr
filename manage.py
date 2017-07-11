import os
import sys

import click

from app import create_app, db


app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.cli.command()
def create_tables():
    db.database.create_tables(db.models)


@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


@app.cli.command('ipython', context_settings=dict(ignore_unknown_options=True),
                 short_help='Run a IPython shell in the app context.')
@click.argument('ipython_args', nargs=-1, type=click.UNPROCESSED)
def shell_command(ipython_args):
    import IPython
    from IPython.terminal.ipapp import load_default_config
    from traitlets.config.loader import Config

    from flask.globals import _app_ctx_stack
    app = _app_ctx_stack.top.app
    banner = 'Python %s on %s\nIPython: %s\nApp: %s%s\nInstance: %s\n' % (
        sys.version,
        sys.platform,
        IPython.__version__,
        app.import_name,
        app.debug and ' [debug]' or '',
        app.instance_path,
    )
    ctx = {}

    if 'IPYTHON_CONFIG' in app.config:
        config = Config(app.config['IPYTHON_CONFIG'])
    else:
        config = load_default_config()
    config.TerminalInteractiveShell.banner1 = banner

    ctx.update(app.make_shell_context())

    IPython.start_ipython(argv=ipython_args, user_ns=ctx, config=config)
