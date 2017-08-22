import os
import sys

from flask.cli import with_appcontext

from flask_pw import BaseSignalModel
import click

from app import create_app, db

cov = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    cov = coverage.Coverage(branch=True, include='app/*')
    cov.start()


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
@click.option('--coverage', default=False, is_flag=True,
              help=('Run the coverage test.'))
def test(coverage):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if cov:
        cov.stop()
        cov.save()
        print('Coverage Summary:')
        cov.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        cov.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        cov.erase()


@app.shell_context_processor
def make_shell_context():
    from app.models import Permission
    pw_models = {mod.__name__: mod for mod in db.models}
    return dict(db=db, Permission=Permission, **pw_models)
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
