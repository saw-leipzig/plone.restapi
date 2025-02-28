# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from Acquisition import aq_parent
from plone.restapi.deserializer import json_body
from plone.restapi.services import Service
from Products.CMFCore.utils import getToolByName
from Products.PluggableAuthService.interfaces.plugins import (
    IAuthenticationPlugin,
)
from zope.interface import alsoProvides

import plone.protect.interfaces
import six


class Login(Service):
    """Handles login and returns a JSON web token (JWT).
    """

    def reply(self):
        data = json_body(self.request)
        if "login" not in data or "password" not in data:
            self.request.response.setStatus(400)
            return dict(
                error=dict(
                    type="Missing credentials",
                    message="Login and password must be provided in body.",
                )
            )

        # Disable CSRF protection
        if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
            alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)

        userid = data["login"]
        password = data["password"]
        if six.PY2:
            userid = userid.encode("utf8")
            password = password.encode("utf8")
        uf = self._find_userfolder(userid)

        if uf is not None:
            plugins = uf._getOb("plugins")
            authenticators = plugins.listPlugins(IAuthenticationPlugin)
            plugin = None
            for id_, authenticator in authenticators:
                if authenticator.meta_type == "JWT Authentication Plugin":
                    plugin = authenticator
                    break

            if plugin is None:
                self.request.response.setStatus(501)
                return dict(
                    error=dict(
                        type="Login failed",
                        message="JWT authentication plugin not installed.",
                    )
                )

            user = uf.authenticate(userid, password, self.request)
        else:
            user = None

        if not user:
            self.request.response.setStatus(401)
            return dict(
                error=dict(
                    type="Invalid credentials", message="Wrong login and/or password."
                )
            )

        payload = {}
        payload["fullname"] = user.getProperty("fullname")
        return {"token": plugin.create_token(user.getId(), data=payload)}

    def _find_userfolder(self, userid):
        """Try to find a user folder that contains a user with the given
           userid.
        """
        uf_parent = aq_inner(self.context)
        info = None

        while not info:
            uf = getToolByName(uf_parent, "acl_users")
            if uf:
                info = uf._verifyUser(uf.plugins, login=userid)
            if uf_parent is self.context.getPhysicalRoot():
                break
            uf_parent = aq_parent(uf_parent)

        if info:
            return uf
        return None

    def check_permission(self):
        return
