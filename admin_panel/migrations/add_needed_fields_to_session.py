# Generated manually

from django.db import migrations, models, connection
from django.db.migrations.operations.fields import FieldOperation
from django.db.models.fields import NOT_PROVIDED

class AddFieldIfNotExists(FieldOperation):
    """Adds a field to a model if it doesn't already exist"""
    
    def __init__(self, model_name, name, field, preserve_default=True):
        self.model_name = model_name
        self.name = name
        self.field = field
        self.preserve_default = preserve_default

    def deconstruct(self):
        kwargs = {
            'model_name': self.model_name,
            'name': self.name,
            'field': self.field,
        }
        if self.preserve_default is not True:
            kwargs['preserve_default'] = self.preserve_default
        return (
            self.__class__.__name__,
            [],
            kwargs
        )

    def state_forwards(self, app_label, state):
        # Only add the field if it doesn't exist in the state
        model_state = state.models[app_label, self.model_name.lower()]
        if self.name not in model_state.fields:
            model_state.fields.append((self.name, self.field))
            state.reload_model(app_label, self.model_name.lower())

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        # Check if column already exists in database
        table_name = f"{app_label}_{self.model_name.lower()}"
        column_name = self.name
        
        # Check if column exists using the database introspection
        with connection.cursor() as cursor:
            # Different SQL for different database backends
            if connection.vendor == 'postgresql':
                cursor.execute(
                    """
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                    """, 
                    [table_name, column_name]
                )
                if cursor.fetchone():
                    # Column already exists, skip adding
                    return
            elif connection.vendor == 'sqlite':
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [info[1] for info in cursor.fetchall()]
                if column_name in columns:
                    # Column already exists, skip adding
                    return
        
        # If we get here, column doesn't exist - add it
        to_model = to_state.apps.get_model(app_label, self.model_name)
        field = to_model._meta.get_field(self.name)
        schema_editor.add_field(to_model, field)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.apps.get_model(app_label, self.model_name)
        to_model = to_state.apps.get_model(app_label, self.model_name)
        
        if hasattr(to_model, '_meta') and not hasattr(to_model._meta, 'get_field'):
            return  # Can't get field, so can't drop it
            
        if self.name not in to_model._meta.fields_map:
            field = from_model._meta.get_field(self.name)
            schema_editor.remove_field(from_model, field)

    def describe(self):
        return "Add field %s to %s if it doesn't exist" % (self.name, self.model_name)


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0010_telegramsession_session_data"),
    ]

    operations = [
        AddFieldIfNotExists(
            model_name="TelegramSession",
            name="session_data",
            field=models.TextField(
                blank=True,
                help_text="Encoded session data for persistent storage",
                null=True,
            ),
        ),
        AddFieldIfNotExists(
            model_name="TelegramSession",
            name="needs_auth",
            field=models.BooleanField(
                default=True,
                help_text="Indicates if this session needs manual authentication"
            ),
        ),
        AddFieldIfNotExists(
            model_name="TelegramSession",
            name="auth_token",
            field=models.CharField(
                blank=True,
                help_text="Token for authorizing this session via bot",
                max_length=255,
                null=True,
            ),
        ),
    ] 