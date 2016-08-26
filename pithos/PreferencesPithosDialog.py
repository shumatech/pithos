# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License version 3, as published
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranties of
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import logging

from gi.repository import Gio, Gtk, GObject, Pango


from .util import get_account_password, set_account_password
from .pandora.data import valid_audio_formats

try:
    import pacparser
except ImportError:
    pacparser = None
    logging.info("Could not import python-pacparser.")


class PithosPluginRow(Gtk.ListBoxRow):

    def __init__(self, plugin):
        super().__init__()

        self.plugin = plugin

        box = Gtk.Box()
        label = Gtk.Label()
        label.set_markup('<b>{}</b>\n{}'.format(plugin.name.title().replace('_', ' '), plugin.description))
        label.set_halign(Gtk.Align.START)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(30)
        label.set_line_wrap(True)
        label.set_lines(1)
        box.pack_start(label, True, True, 4)

        self.switch = Gtk.Switch()
        plugin.settings.bind('enabled', self.switch, 'active', Gio.SettingsBindFlags.DEFAULT)
        self.switch.connect('notify::active', self.on_activated)
        self.switch.set_valign(Gtk.Align.CENTER)
        box.pack_end(self.switch, False, False, 2)

        if plugin.prepared and plugin.error:
            self.set_sensitive(False)
            self.set_tooltip_text(plugin.error)

        self.add(box)

    def on_activated(self, obj, params):
        if not self.is_selected():
            self.get_parent().select_row(self)

        if self.switch.get_active():
            self.plugin.enable()
        else:
            self.plugin.disable()

        if self.plugin.prepared and self.plugin.error:
            self.get_parent().unselect_row(self)
            self.set_sensitive(False)
            self.set_tooltip_text(self.plugin.error)
        elif self.plugin.prepared:
            self.get_toplevel().preference_btn.set_sensitive(self.plugin.preferences_dialog is not None)


@Gtk.Template(ui='/io/github/Pithos/ui/PreferencesPithosDialog.ui')
class PreferencesPithosDialog(Gtk.Dialog):
    __gsignals__ = {
        'login-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, *args, **kwargs):
        super(Gtk.Dialog, self).__init__(*args, use_header_bar=1, **kwargs)

        self.preference_btn = self.get_template_child('preference_btn')
        self.plugins_listbox = self.get_template_child('plugins_listbox')
        self.email_entry = self.get_template_child('email_entry')
        self.password_entry = self.get_template_child('password_entry')
        self.audio_quality_combo = self.get_template_child('audio_quality_combo')
        self.proxy_entry = self.get_template_child('proxy_entry')
        self.control_proxy_entry = self.get_template_child('control_proxy_entry')
        self.control_proxy_pac_entry = self.get_template_child('control_proxy_pac_entry')
        self.pandora_one_checkbutton = self.get_template_child('pandora_one_checkbutton')
        self.explicit_content_filter_checkbutton = self.get_template_child('explicit_content_filter_checkbutton')

        self.settings = Gio.Settings.new('io.github.Pithos')

        # initialize the "Audio Quality" combobox backing list
        fmt_store = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        for audio_quality in valid_audio_formats:
            fmt_store.append(audio_quality)
        self.audio_quality_combo.set_model(fmt_store)
        render_text = Gtk.CellRendererText()
        self.audio_quality_combo.pack_start(render_text, True)
        self.audio_quality_combo.add_attribute(render_text, "text", 1)
        self.audio_quality_combo.set_id_column(0)

        if not pacparser:
            self.control_proxy_pac_entry.set_sensitive(False)
            self.control_proxy_pac_entry.set_tooltip_text("Please install python-pacparser")

        settings_mapping = {
            'email': (self.email_entry, 'text'),
            'pandora-one': (self.pandora_one_checkbutton, 'active'),
            'proxy': (self.proxy_entry, 'text'),
            'control-proxy': (self.control_proxy_entry, 'text'),
            'control-proxy-pac': (self.control_proxy_pac_entry, 'text'),
            'audio-quality': (self.audio_quality_combo, 'active-id'),
        }

        for key, val in settings_mapping.items():
            self.settings.bind(key, val[0], val[1],
                        Gio.SettingsBindFlags.DEFAULT|Gio.SettingsBindFlags.NO_SENSITIVITY)

    def set_plugins(self, plugins):
        self.plugins_listbox.set_header_func(self.on_listbox_update_header)
        for plugin in plugins.values():
            row = PithosPluginRow(plugin)
            self.plugins_listbox.add(row)
        self.plugins_listbox.show_all()

    @Gtk.Template.Callback
    def on_plugins_row_selected(self, box, row):
        if row:
            self.preference_btn.set_sensitive(row.plugin.preferences_dialog is not None)

    @Gtk.Template.Callback
    def on_prefs_btn_clicked(self, btn):
        dialog = self.plugins_listbox.get_selected_rows()[0].plugin.preferences_dialog
        dialog.set_transient_for(self)
        dialog.set_destroy_with_parent(True)
        dialog.set_modal(True)
        dialog.show_all()

    @Gtk.Template.Callback
    def on_account_changed(self, widget):
        if not self.email_entry.get_text() or not self.password_entry.get_text():
            self.set_response_sensitive(Gtk.ResponseType.APPLY, False)
        else:
            self.set_response_sensitive(Gtk.ResponseType.APPLY, True)

    def on_listbox_update_header(self, row, before, junk = None):
        if before and not row.get_header():
            row.set_header(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL))

    @Gtk.Template.Callback
    def on_show(self, widget):
        self.settings.delay()

        self.last_email = self.settings['email']
        self.password_entry.set_text(get_account_password(self.settings['email']))
        self.on_account_changed(None)

    def do_response(self, response_id):
        if response_id == Gtk.ResponseType.APPLY:
            self.settings.apply()
            if set_account_password(self.settings['email'], self.password_entry.get_text(),
                                    self.last_email):
                self.emit('login-changed')
        else:
            self.settings.revert()

