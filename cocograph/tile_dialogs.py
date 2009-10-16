'''
Copyright (c) 2009, Devon Scott-Tunkin
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Thanks to Richard Jones for his original editor and tile library
and Conrad Wong for the "kytten" gui library

Cocograph tile map editor for cocos2d
'''

import os
import glob
import weakref
from xml.etree import ElementTree

import pyglet
# Disable error checking for increased performance
pyglet.options['debug_gl'] = False
from pyglet.gl import *

import cocos
from cocos import tiles, actions

import kytten

from tile_widgets import *
from dialog_node import *

the_theme = kytten.Theme(os.path.join(os.getcwd(), 'theme'), override={
    "gui_color": [255, 235, 128, 255],
    "font_size": 12,
})

def _on_escape(dialog):
    dialog.teardown() 

def _on_prop_container_edit(prop_container, parent_dnode, filename=None):
    if prop_container is None:
        return
    options = prop_container.properties.iteritems()
    dnode = DialogNode()
    
    def on_submit(dialog):
        pd = PropertyDialog
        for k, v in dialog.get_values().iteritems():
            
            # Check prefix is not removal value
            if not k.startswith(pd.REMOVE_PRE) \
                and not k.startswith(pd.TYPE_PRE) \
                and not k.startswith(pd.ADD_NAME_PRE):
                
                # If matching removal prefix + key is true, remove
                if dialog.get_value(pd.REMOVE_PRE+k):
                    del prop_container.properties[k]

                # If new property find matching name and type then add    
                elif k.startswith(pd.ADD_VALUE_PRE):
                    id_num = k.lstrip(pd.ADD_VALUE_PRE)
                    v_name = dialog.get_value(pd.ADD_NAME_PRE+id_num)
                    v_type = dialog.get_value(pd.TYPE_PRE+id_num)
                    if v_type is not 'bool':
                        v_type = tiles._xml_to_python[v_type]
                    else:
                        v_type = bool
                    prop_container.properties[v_name] = v_type(v)
                    
                # Otherwise change to new value and cast to old type
                else: 
                    prop_container.properties[k] = \
                        type(prop_container.properties[k])(v)
        if isinstance(prop_container, tiles.Tile):
            for ns, res in parent_dnode.level_to_edit.requires:
                if prop_container in res.contents.itervalues():
                    resource = res
            dirname = os.path.dirname(parent_dnode.level_to_edit.filename)
            xmlname = os.path.join(dirname, resource.filename)
            in_tree = ElementTree.parse(xmlname)
            root = ElementTree.Element('resource')
            root.text = '\n'
            root.tail = '\n'
            for namespace, res in resource.requires:
                r_element = ElementTree.SubElement(root, 'requires', 
                                           file=res.filename)
                r_element.tail = '\n'
                if namespace:
                    r_element.set('namespace', namespace)
            for img_element in in_tree.findall('image'):
                root.append(img_element)
            for atlas_element in in_tree.findall('imageatlas'):
                root.append(atlas_element)
            tset_element = _generic_as_xml(parent_dnode.active_tileset, root, 'tileset')
            for n, k in enumerate(parent_dnode.active_tileset):
                t = parent_dnode.active_tileset[k]
                t_element = _generic_as_xml(t, tset_element, 'tile')
                if t.offset:
                    t_element.set('offset', t.offset)
                for k, v in resource.contents.iteritems():
                    if t.image is v:
                        img_element = ElementTree.SubElement(
                            t_element, 'image', ref=k)
                        img_element.tail = '\n'
            out_tree = ElementTree.ElementTree(root)
            out_tree.write(xmlname)
        dnode.delete()
    
    try:
        id = prop_container.id
    except AttributeError:
        id = ''
    dnode.dialog = PropertyDialog(id, properties=options, 
                                  window=parent_dnode.dialog.window, 
                                  theme=parent_dnode.dialog.theme,
                                  on_ok=on_submit,
                                  on_cancel=dnode.delete,
                                  has_remove=True, has_add=True)
    parent_dnode.parent.add(dnode)
        
def _generic_as_xml(resource, parent, tag):
    element = ElementTree.SubElement(parent, tag)
    element.text = '\n'
    element.tail = '\n'
    if resource.id:
        element.set('id', resource.id)
    for k in resource.properties:
        v = resource.properties[k]
        vs = tiles._python_to_xml[type(v)](v)
        p = ElementTree.SubElement(element, 'property', name=k, value=vs,
            type=tiles._xml_type[type(v)])
        p.tail = '\n'
    return element

class TilesetDialog(DialogNode):
    _id_count = 0
    def __init__(self, window=None, level_to_edit=None, tile_size=32):
        self.level_to_edit = level_to_edit
        self.tilesets = {}
        self.tile_size = tile_size
        self.selected = None
        self.palettes = {}
        self.vlayout = None
        self._load_tilesets(level_to_edit)
        
        def on_menu_select(choice):
            if choice is 'New':
                self._create_new_dialog()
            if choice is 'Open':
                dnode = DialogNode()
                
                def on_open_click(filename):
                    r = tiles.load(filename)
                    self._load_tilesets(r)
                    
                    dnode.dialog.on_escape(dnode.dialog)
                    
                dnode.dialog = kytten.FileLoadDialog(
                    extensions=['.xml'], window=self.dialog.window, 
                    theme=self.dialog.theme, 
                    on_select=on_open_click,
                    on_escape=dnode.delete)
                self.parent.add(dnode)
                
        def on_palette_select(id):
            if self.hlayout.saved_dialog is not None:
                self.active_tileset = self.tilesets[id]
                self.active_palette = self.palettes[id]
                self.hlayout.set([
                    self.active_palette,
                    kytten.VerticalLayout([
                        kytten.SectionHeader("Tileset"),
                        kytten.Menu(['New','Open'], 
                    on_select=on_menu_select)])])
                self.active_palette.select(
                    self.active_palette.options.iterkeys().next())
        
        self.palette_menu = HorizontalMenu([ 
            k for k, v in self.palettes.iteritems()],
            padding=16,
            on_select=on_palette_select)  
        self.hlayout = kytten.HorizontalLayout([
            self.active_palette,
            kytten.VerticalLayout([
                kytten.SectionHeader("Tileset"),
                NoSelectMenu(['New','Open'], 
                    on_select=on_menu_select)])])
        self.vlayout = kytten.VerticalLayout([
                self.palette_menu,
                self.hlayout],
            align=kytten.HALIGN_LEFT)
        super(TilesetDialog, self).__init__(
            kytten.Dialog(
                kytten.Frame(
                    kytten.Scrollable(
                        self.vlayout,
                        width=window.width-30)),
                window=window,
                anchor=kytten.ANCHOR_BOTTOM,
                theme=the_theme))
                
        # Make first palette active
        try:
            self.palette_menu.select(self.palettes.iterkeys().next())
        except:
            pass
            
    def _load_tilesets(self, resource):
        select_id = ''
        for id, ts in resource.findall(tiles.TileSet):
            if id is None:
                self._id_count += 1
                id = 'Untitled'+str(self._id_count)
            self.tilesets[id] = ts
            select_id = id
        try:
            self.active_tileset = resource.findall(
                tiles.TileSet).next()[1]
        except:
            self.active_tileset = None
        
        def on_tile_select(id):
            try:
                self.selected = self.active_tileset[id]
            except KeyError:
                pass
                
        for id, tset in self.tilesets.iteritems():
            tile_options = [[]]
            tile_options.append([])
            for i, k in enumerate(tset):
                option = TilePaletteOption(id=k, 
                    image=tset[k].image, 
                    scale_size=self.tile_size, 
                    on_edit=self._on_tile_edit)
                tile_options[i%2].append(option)
            self.palettes[id] = Palette(tile_options, 
                                        on_select=on_tile_select)
        try:
            self.active_palette = self.palettes.itervalues().next()
        except:
            self.active_palette = None
        if self.vlayout is not None:
            self.palette_menu.set_options([ 
                k for k, v in self.palettes.iteritems()])
            self.palette_menu.select(select_id)    
            self.vlayout.set([self.palette_menu, self.hlayout])
        
    def select_tile(self, id):
        for tset_id, tset in self.tilesets.iteritems():
            if id in tset:
                self.palette_menu.select(tset_id)
                self.active_palette.select(id)
            
    def _on_tile_edit(self, id):
        tile = self.active_tileset[id]
        _on_prop_container_edit(tile, self)
        
    def _create_new_dialog(self):
        dnode = DialogNode()
        
        def on_select_click(dirpath):
            filepaths = glob.glob(os.path.join(dirpath, '*'))
            extensions = ['.png', '.jpg', '.bmp', '.gif']
            filenames = []
            for filepath in filepaths:
                if os.path.isfile(filepath):
                    ext = os.path.splitext(filepath)[1]
                    if ext in extensions:
                        filenames.append(os.path.basename(filepath))
            if len(filenames) is not 0:
                save_dnode = DialogNode()
                
                def on_save(filepath):
                    root = ElementTree.Element('resource')
                    root.tail = '\n'
                    for filename in filenames:
                        img_element = ElementTree.SubElement(root, 
                            'image', 
                            id='i-'+os.path.splitext(filename)[0],
                            file=filename)
                        img_element.tail = '\n'
                    xmlname = os.path.basename(filepath)
                    tset_element = ElementTree.SubElement(root, 
                        'tileset', id=os.path.splitext(xmlname)[0])
                    tset_element.tail = '\n'
                    for filename in filenames:
                        t_element = ElementTree.SubElement(tset_element, 
                            'tile', id=os.path.splitext(filename)[0])
                        t_element.tail = '\n'
                        img_element = ElementTree.SubElement(t_element, 
                            'image', ref='i-'+os.path.splitext(filename)[0])
                    tree = ElementTree.ElementTree(root)
                    tree.write(filepath)
                    r = tiles.load(filepath)
                    self._load_tilesets(r)
                    
                    # Tilesets filename should be relative to maps
                    level_dir = os.path.split(
                        self.level_to_edit.filename)[0] + os.sep
                        
                    # Remove map path from tileset filename
                    r.filename = r.filename.replace(level_dir, '')
                    r.filename = r.filename.replace('\\', '/')
                    self.level_to_edit.requires.append(('',r))
                    
                    save_dnode.dialog.on_escape(save_dnode.dialog)
                save_dnode.dialog = kytten.FileSaveDialog(
                    path=dirpath,
                    extensions=['.xml'],
                    title='Save Tileset As', 
                    window=self.dialog.window, 
                    theme=self.dialog.theme, 
                    on_select=on_save,
                    on_escape=save_dnode.delete)
                self.parent.add(save_dnode)
                   
            dnode.dialog.on_escape(dnode.dialog)
            
        dnode.dialog = kytten.DirectorySelectDialog(
            title='Select Directory of Images',
            window=self.dialog.window, 
            theme=self.dialog.theme, 
            on_select=on_select_click,
            on_escape=dnode.delete)
        self.parent.add(dnode)


class ToolMenuDialog(DialogNode):
    def __init__(self, window, on_new=None, on_open=None, on_save=None,
                 on_edit=None):
        self.on_new = on_new
        self.on_open = on_open
        self.on_save = on_save
        self.on_edit = on_edit
        
        # Load images into a list
        images = []
        images.append(('move',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'transform-move.png'))))
        images.append(('eraser',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'draw-eraser.png'))))
        images.append(('picker',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'color-picker.png'))))
        images.append(('zoom',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'page-magnifier.png'))))
        images.append(('pencil',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'draw-freehand.png'))))
        images.append(('fill',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'color-fill.png'))))

        # Create options from images to pass to Palette
        options = [[]]
        options.append([])
        options.append([])
        for i, pair in enumerate(images):
            option = PaletteOption(id=pair[0], image=pair[1], padding=4)
            options[i%3].append(option) # build column down, 3 rows
            
        def on_tool_select(id):
            self.active_tool = id
            
        super(ToolMenuDialog, self).__init__(kytten.Dialog(
            kytten.Frame(
                kytten.Scrollable(
                    kytten.VerticalLayout([
                        Palette(options, on_select=on_tool_select),
                        #kytten.SectionHeader("Layer"),
                        kytten.VerticalLayout([]),
                        kytten.SectionHeader("Map"),
                        kytten.VerticalLayout([
                            NoSelectMenu(
                                options=["New", "Open", "Save", 
                                         "Properties", "Quit"],
                                on_select=self._on_filemenu_select),
                        ]),
                    ], align=kytten.HALIGN_CENTER),
                    height=400)
            ),
            window=window,
            anchor=kytten.ANCHOR_LEFT,
            theme=the_theme))
            
    def _on_filemenu_select(self, choice):
        if choice == 'New':
            self._create_new_dialog()
        elif choice == 'Open':
            self._create_open_dialog()
        elif choice == 'Save':
            if self.on_save is not None:
                self.on_save()
        elif choice == 'Properties':
            if self.on_edit is not None:
                self.on_edit()
        elif choice == 'Quit':
            director.pop()
            
    def _create_new_dialog(self):
        dnode = DialogNode()
        options = []
        #mid = 'Map ID'
        
        # Options for new map form
        tw = 'Tile Width (px)'
        th = 'Tile Height (px)'
        mw = 'Map Width (tiles)'
        mh = 'Map Height (tiles)'
        #mo = 'Map Origin (x,y,z)'
        #options.append((mid,""))
        options.append((tw,""))
        options.append((th,""))
        options.append((mw,""))
        options.append((mh,""))
        #options.append((mo,"0,0,0"))
        
        def on_submit(dialog):
            root = ElementTree.Element('resource')
            root.tail = '\n'
            v = dialog.get_values()

            save_dnode = DialogNode()
            def on_save(filename):
                xmlname = os.path.basename(filename)    
                m = ElementTree.SubElement(root, 'rectmap', 
                    id=os.path.splitext(xmlname)[0],
                    tile_size='%dx%d'%(int(v[tw]), int(v[th])),
                    origin='%s,%s,%s'%(0, 0, 0))
                m.tail = '\n'  
                for column in range(int(v[mw])):
                    col = ElementTree.SubElement(m, 'column')
                    col.tail = '\n'
                    for cell in range(int(v[mh])):
                        c = ElementTree.SubElement(col, 'cell')
                        c.tail = '\n'
                tree = ElementTree.ElementTree(root)
                tree.write(filename)
                if self.on_open is not None:
                    self.on_open(filename)
                save_dnode.dialog.on_escape(save_dnode.dialog)
            save_dnode.dialog = kytten.FileSaveDialog(
                extensions=['.xml'],
                title='Save Map As', 
                window=self.dialog.window, 
                theme=self.dialog.theme, 
                on_select=on_save,
                on_escape=save_dnode.delete)
            self.parent.add(save_dnode)
            dnode.dialog.on_escape(dnode.dialog)

        dnode.dialog = PropertyDialog('New Map', properties=options, 
            window=self.dialog.window, 
            theme=self.dialog.theme,
            on_ok=on_submit,
            on_cancel=dnode.delete)
        self.parent.add(dnode)
        
    def _create_open_dialog(self):
        dnode = DialogNode()
        def on_open_click(filename):
            if self.on_open is not None:
                self.on_open(filename)
            dnode.dialog.on_escape(dnode.dialog)
        dnode.dialog = kytten.FileLoadDialog(
            extensions=['.xml'], window=self.dialog.window, 
            theme=self.dialog.theme, 
            on_select=on_open_click,
            on_escape=dnode.delete)
        self.parent.add(dnode)
