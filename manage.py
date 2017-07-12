import os
import sys

from flask.cli import with_appcontext

from flask_pw import BaseSignalModel
import click

from app import create_app, db


app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@db.cli.command('createtables', short_help='Create database tables.')
@click.option('--safe', default=False, is_flag=True,
              help=('Check first whether the table exists '
                    'before attempting to create it.'))
@click.argument('models', nargs=-1, type=click.UNPROCESSED)
@with_appcontext
def create_tables(models, safe):
    from importlib import import_module
    from flask.globals import _app_ctx_stack
    app = _app_ctx_stack.top.app
    if models:
        pw_models = []

        module = import_module(app.config['PEEWEE_MODELS_MODULE'])
        for mod in models:
            model = getattr(module, mod)
            if not isinstance(model, BaseSignalModel):
                continue
            pw_models.append(model)
        if pw_models:
            db.database.create_tables(pw_models, safe)
        return
    db.database.create_tables(db.models, safe)


@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


@app.shell_context_processor
def make_shell_context():
    pw_models = {mod.__name__: mod for mod in db.models}
    return dict(db=db, **pw_models)
# Equivalent to the following
# app.shell_context_processors.append(make_shell_context)


@app.cli.command('ipython',
                 context_settings=dict(ignore_unknown_options=True),
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
