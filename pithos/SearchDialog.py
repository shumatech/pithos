# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
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

import html
from gi.repository import GObject, Gtk



@Gtk.Template(ui='/io/github/Pithos/ui/SearchDialog.ui')
class SearchDialog(Gtk.Dialog):

    def __init__(self, *args, **kwargs):
        self.worker_run = kwargs["worker"]
        del kwargs["worker"]

        super().__init__(*args, use_header_bar=1, **kwargs)

        self.entry = self.get_template_child(Gtk.Entry, 'entry')
        self.treeview = self.get_template_child(Gtk.TreeView, 'treeview')

        self.model = Gtk.ListStore(GObject.TYPE_PYOBJECT, str)
        self.treeview.set_model(self.model)

        self.result = None

    @Gtk.Template.Callback
    def search_clicked(self, widget):
        self.search(self.entry.get_text())

    @Gtk.Template.Callback
    def get_selected(self):
        sel = self.treeview.get_selection().get_selected()
        if sel[1]:
            return self.treeview.get_model().get_value(sel[1], 0)

    def search(self, query):
        if not query: return
        def callback(results):
            self.model.clear()
            for i in results:
                if i.resultType is 'song':
                    mk = "<b>%s</b> by %s"%(html.escape(i.title), html.escape(i.artist))
                elif i.resultType is 'artist':
                    mk = "<b>%s</b> (artist)"%(html.escape(i.name))
                self.model.append((i, mk))
            self.treeview.show()
        self.worker_run('search', (query,), callback, "Searching...")

    def cursor_changed(self, *ignore):
        self.result = self.get_selected()
        self.set_response_sensitive(Gtk.ResponseType.OK, not not self.result)
