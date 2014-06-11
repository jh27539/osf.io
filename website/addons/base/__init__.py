"""

"""

import os
import glob
import importlib
import mimetypes
from bson import ObjectId
from mako.lookup import TemplateLookup

from framework import StoredObject, fields
from framework.routing import process_rules
from framework.guid.model import GuidStoredObject

from website import settings

lookup = TemplateLookup(
    directories=[
        settings.TEMPLATES_PATH
    ]
)

def _is_image(filename):
    mtype, _ = mimetypes.guess_type(filename)
    return mtype and mtype.startswith('image')


class AddonConfig(object):

    def __init__(self, short_name, full_name, owners, categories,
                 added_default=None, added_mandatory=None,
                 node_settings_model=None, user_settings_model=None, include_js=None, include_css=None,
                 widget_help=None, views=None, configs=None, models=None,
                 has_hgrid_files=False, get_hgrid_data=None, max_file_size=None,
                 accept_extensions=True,
                 **kwargs):

        self.models = models
        self.settings_models = {}

        if node_settings_model:
            node_settings_model.config = self
            self.settings_models['node'] = node_settings_model

        if user_settings_model:
            user_settings_model.config = self
            self.settings_models['user'] = user_settings_model

        self.short_name = short_name
        self.full_name = full_name
        self.owners = owners
        self.categories = categories

        self.added_default = added_default or []
        self.added_mandatory = added_mandatory or []
        if set(self.added_mandatory).difference(self.added_default):
            raise ValueError('All mandatory targets must also be defaults.')

        self.include_js = self._include_to_static(include_js or {})
        self.include_css = self._include_to_static(include_css or {})

        self.widget_help = widget_help

        self.views = views or []
        self.configs = configs or []

        self.has_hgrid_files = has_hgrid_files
        self.get_hgrid_data = get_hgrid_data #if has_hgrid_files and not get_hgrid_data rubeus.make_dummy()
        self.max_file_size = max_file_size
        self.accept_extensions = accept_extensions

        # Build template lookup
        template_path = os.path.join('website', 'addons', short_name, 'templates')
        if os.path.exists(template_path):
            self.template_lookup = TemplateLookup(
                directories=[
                    template_path,
                    settings.TEMPLATES_PATH,
                ]
            )
        else:
            self.template_lookup = None

    def _static_url(self, filename):
        """Build static URL for file; use the current addon if relative path,
        else the global static directory.

        :param str filename: Local path to file
        :return str: Static URL for file

        """
        if filename.startswith('/'):
            return filename
        return '/static/addons/{addon}/{filename}'.format(
            addon=self.short_name,
            filename=filename,
        )

    def _include_to_static(self, include):
        """

        """
        # TODO: minify static assets
        return {
            key: [
                self._static_url(item)
                for item in value
            ]
            for key, value in include.iteritems()
        }

    # TODO: Make INCLUDE_JS and INCLUDE_CSS one option

    @property
    def icon(self):

        try:
            return self._icon
        except:
            static_path = os.path.join('website', 'addons', self.short_name, 'static')
            static_files = glob.glob(os.path.join(static_path, 'comicon.*'))
            image_files = [
                os.path.split(filename)[1]
                for filename in static_files
                if _is_image(filename)
            ]
            if len(image_files) == 1:
                self._icon = image_files[0]
            else:
                self._icon = None
            return self._icon

    @property
    def icon_url(self):
        return self._static_url(self.icon) if self.icon else None

    def to_json(self):
        return {
            'short_name': self.short_name,
            'full_name': self.full_name,
            'capabilities': self.short_name in settings.ADDON_CAPABILITIES,
            'addon_capabilities': settings.ADDON_CAPABILITIES.get(self.short_name),
            'icon': self.icon_url,
            'has_page': 'page' in self.views,
            'has_widget': 'widget' in self.views,
        }

    @property
    def path(self):
        return os.path.join(settings.BASE_PATH, self.short_name)


class GuidFile(GuidStoredObject):

    redirect_mode = 'proxy'

    _id = fields.StringField(primary=True)
    node = fields.ForeignField('node', index=True)

    _meta = {
        'abstract': True,
    }

    @property
    def file_url(self):
        raise NotImplementedError

    @property
    def deep_url(self):
        if self.node is None:
            raise ValueError('Node field must be defined.')
        return os.path.join(
            self.node.deep_url, self.file_url,
        )



class AddonSettingsBase(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    deleted = fields.BooleanField(default=False)

    _meta = {
        'abstract': True,
    }

    def delete(self, save=True):
        self.deleted = True
        if save:
            self.save()

    def undelete(self, save=True):
        self.deleted = False
        if save:
            self.save()

    def to_json(self, user):
        return {
            'addon_short_name': self.config.short_name,
            'addon_full_name': self.config.full_name,
        }


class AddonUserSettingsBase(AddonSettingsBase):

    owner = fields.ForeignField('user', backref='addons')

    _meta = {
        'abstract': True,
    }

    @property
    def public_id(self):
        return None

    def get_backref(self, schema, backref_name):
        return schema + "__" + backref_name

    #TODO show this
    @property
    def nodes(self):
        schema = self.config.settings_models['node']._name
        ret = []
        nodes_backref = self.get_backref(schema, "authorized")

        for node in getattr(self, nodes_backref):
            ret.append(node.owner)

        return ret

    #TODO show this
    def to_json(self, user):
        ret = super(AddonUserSettingsBase, self).to_json(user)
        ret.update({
            'nodes': self.nodes
        })
        return ret


class AddonNodeSettingsBase(AddonSettingsBase):

    owner = fields.ForeignField('node', backref='addons')

    _meta = {
        'abstract': True,
    }

    def to_json(self, user):
        ret = super(AddonNodeSettingsBase, self).to_json(user)
        ret.update({
            'user': {
                'permissions': self.owner.get_permissions(user)
            },
            'node': {
                'id': self.owner._id,
                'api_url': self.owner.api_url,
                'url': self.owner.url,
                'is_registration': self.owner.is_registration,
            }
        })
        return ret

    def render_config_error(self, data):
        """

        """
        # Note: `config` is added to `self` in `AddonConfig::__init__`.
        template = lookup.get_template('project/addon/config_error.mako')
        return template.get_def('config_error').render(
            title=self.config.full_name,
            name=self.config.short_name,
            **data
        )

    #############
    # Callbacks #
    #############

    def before_page_load(self, node, user):
        """

        :param User user:
        :param Node node:

        """
        pass

    def before_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:

        """
        pass

    def after_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:

        """
        pass

    def after_set_privacy(self, node, permissions):
        """

        :param Node node:
        :param str permissions:

        """
        pass

    def before_fork(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """
        pass

    def after_fork(self, node, fork, user, save=True):
        """

        :param Node node:
        :param Node fork:
        :param User user:
        :param bool save:
        :return tuple: Tuple of cloned settings and alert message

        """
        clone = self.clone()
        clone.owner = fork

        if save:
            clone.save()

        return clone, None

    def before_register(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """
        pass

    def after_register(self, node, registration, user, save=True):
        """

        :param Node node:
        :param Node registration:
        :param User user:
        :param bool save:
        :return tuple: Tuple of cloned settings and alert message

        """
        clone = self.clone()
        clone.owner = registration

        if save:
            clone.save()

        return clone, None


# TODO: Move this
LOG_TEMPLATES = 'website/templates/log_templates.mako'

# TODO: No more magicks
def init_addon(app, addon_name, routes=True):
    """Load addon module and create configuration object.

    :param app: Flask app object
    :param addon_name: Name of addon directory
    :param bool routes: Add routes
    :return AddonConfig: AddonConfig configuration object if module found,
        else None

    """
    addon_path = os.path.join('website', 'addons', addon_name)
    import_path = 'website.addons.{0}'.format(addon_name)

    # Import addon module
    addon_module = importlib.import_module(import_path)

    data = vars(addon_module)

    # Append add-on log templates to main log templates
    log_templates = os.path.join(
        addon_path, 'templates', 'log_templates.mako'
    )
    if os.path.exists(log_templates):
        with open(LOG_TEMPLATES, 'a') as fp:
            fp.write(open(log_templates, 'r').read())

    # Add routes
    if routes:
        for route_group in getattr(addon_module, 'ROUTES', []):
            process_rules(app, **route_group)

    # Build AddonConfig object
    return AddonConfig(
        **{
            key.lower(): value
            for key, value in data.iteritems()
        }
    )
