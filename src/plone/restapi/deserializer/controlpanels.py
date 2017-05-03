# -*- coding: utf-8 -*-
from plone.registry.interfaces import IRegistry
from plone.restapi.controlpanels import IControlpanel
from plone.restapi.deserializer import json_body
from plone.restapi.interfaces import IDeserializeFromJson
from zExceptions import BadRequest
from zope.component import adapter
from zope.component import getUtility
from zope.interface import implementer
from zope.schema import getFields
from zope.schema.interfaces import ValidationError
from plone.dexterity.interfaces import IDexterityContent
from zope.component import queryMultiAdapter
from plone.restapi.interfaces import IFieldDeserializer
from z3c.form.interfaces import IManagerValidator


@implementer(IDexterityContent)
class FakeDXContext(object):
    """Fake DX content class, so we can re-use the DX field deserializers
    """


@implementer(IDeserializeFromJson)
@adapter(IControlpanel)
class ControlpanelDeserializeFromJson(object):

    def __init__(self, controlpanel):
        self.controlpanel = controlpanel
        self.schema = self.controlpanel.registry_schema

        self.registry = getUtility(IRegistry)

        self.context = self.controlpanel.context
        self.request = self.controlpanel.request

    def __call__(self):
        data = json_body(self.controlpanel.request)
        proxy = self.registry.forInterface(self.schema, prefix='plone')

        schema_data = {}
        errors = []

        # Make a fake context
        fake_context = FakeDXContext()

        for name, field in getFields(self.schema).items():
            field_data = schema_data.setdefault(self.schema, {})

            if field.readonly:
                continue

            if name in data:
                deserializer = queryMultiAdapter(
                    (field, fake_context, self.request),
                    IFieldDeserializer
                )

                try:
                    # Make it sane
                    value = deserializer(data[name])
                    # Validate required etc
                    field.validate(value)
                    # Set the value.
                    setattr(proxy, name, value)
                except ValueError as e:
                    errors.append({
                        'message': e.message, 'field': name, 'error': e})
                except ValidationError as e:
                    errors.append({
                        'message': e.doc(), 'field': name, 'error': e})
                else:
                    field_data[name] = value

        # Validate schemata
        for schema, field_data in schema_data.items():
            validator = queryMultiAdapter(
                (self.context, self.request, None, schema, None),
                IManagerValidator)
            for error in validator.validate(field_data):
                errors.append({'error': error, 'message': error.message})

        if errors:
            raise BadRequest(errors)
