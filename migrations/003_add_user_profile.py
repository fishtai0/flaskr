"""Peewee migrations -- 003_add_user_profile.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['model_name']            # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.python(func, *args, **kwargs)        # Run python code
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.drop_index(model, *col_names)
    > migrator.add_not_null(model, *field_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)

"""

from app.models import User


def migrate(migrator, database, fake=False, **kwargs):
    migrator.add_fields(User,
                        name=User.name,
                        location=User.location,
                        about_me=User.about_me,
                        member_since=User.member_since,
                        last_seen=User.last_seen)


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_fields(User,
                           'name',
                           'location',
                           'about_me',
                           'member_since',
                           'last_seen')
