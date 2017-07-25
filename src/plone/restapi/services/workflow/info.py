# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces._content import IWorkflowAware
from plone.restapi.interfaces import IExpandableElement
from plone.restapi.serializer.converters import json_compatible
from plone.restapi.services import Service
from zope.component import adapter
from zope.interface import Interface
from zope.interface import implementer


@implementer(IExpandableElement)
@adapter(IWorkflowAware, Interface)
class WorkflowInfo(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, expand=False):
        result = {
            'workflow': {
                "@id": '{}/@workflow'.format(self.context.absolute_url()),
            },
        }
        if not expand:
            return result

        wftool = getToolByName(self.context, 'portal_workflow')
        history = wftool.getInfoFor(self.context, "review_history")

        actions = wftool.listActionInfos(object=self.context)
        transitions = []
        for action in actions:
            if action['category'] != 'workflow':
                continue

            transitions.append({
                '@id': '{}/@workflow/{}'.format(
                    self.context.absolute_url(), action['id']),
                'title': action['title'],
            })

        for item, action in enumerate(history):
            history[item]['title'] = wftool.getTitleForStateOnType(
                action['review_state'],
                self.context.portal_type)

        result['workflow'].update({
            'history': json_compatible(history),
            'transitions': transitions,
            })
        return result


class WorkflowInfoService(Service):
    """Get workflow information
    """
    def reply(self):
        info = WorkflowInfo(self.context, self.request)
        return info(expand=True)['workflow']
