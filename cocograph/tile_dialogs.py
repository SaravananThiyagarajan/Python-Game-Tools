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

the_image_extensions = ['.png', '.jpg', '.bmp', '.gif', '.tga']

def texture_set_mag_filter_nearest(texture):
    glBindTexture(texture.target, texture.id)
    glTexParameteri(texture.target, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glBindTexture(texture.target, 0)

def on_prop_container_edit(prop_container, parent_dnode, filename=None):
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
            tset_element = _generic_as_xml(
                parent_dnode.active_tileset, root, 'tileset')
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
    def __init__(self, window=None, level_to_edit=None, tile_size=None):
        self.level_to_edit = level_to_edit
        self.tilesets = {}
        self.selected = None
        self.tile_size = tile_size
        self.palettes = {}
        self.vlayout = None
        self._load_tilesets(level_to_edit)
        
        def on_menu_select(choice):
            if choice == 'From Dir':
                self._create_from_directory_dialog()
            elif choice == 'From Image':
                self._create_from_image_dialog()
            elif choice == 'Open':
                dnode = DialogNode()
                def on_open_click(filename):
                    r = tiles.load(filename)
                    # XXX Maybe more error checking?
                    self._load_tilesets(r)
                    self._make_resource_relative(r)
                    dnode.dialog.on_escape(dnode.dialog)
                    
                dnode.dialog = kytten.FileLoadDialog(
                    extensions=['.xml'], window=self.dialog.window, 
                    theme=self.dialog.theme, 
                    on_select=on_open_click,
                    on_escape=dnode.delete)
                self.parent.add(dnode)
                
        def on_palette_select(id):
            if self.vlayout.saved_dialog is not None:
                self.active_tileset = self.tilesets[id]
                self.active_palette = self.palettes[id]
                self.vlayout.set([self.palette_menu, self.active_palette])
                self.layout.set([self.file_menu, self.vlayout])
                #~ self.active_palette.select(
                    #~ self.active_palette.options.iterkeys().next())
        
        # Create tabs of tilesets
        self.palette_menu = HorizontalMenu([ 
            k for k, v in self.palettes.iteritems()],
            padding=16,
            on_select=on_palette_select) 
            
        # Combine tabs and palette
        self.vlayout = kytten.VerticalLayout(
            [self.palette_menu, self.active_palette],
            align=kytten.HALIGN_LEFT)
            
        # Create tileset file menu
        self.file_menu = kytten.VerticalLayout([
            kytten.FoldingSection("Tileset", NoSelectMenu(
                ['From Dir', 'From Image', 'Open'], on_select=on_menu_select))])
                    
        # Create final combined tileset dialog
        self.layout = kytten.VerticalLayout(
            [self.file_menu, self.vlayout])
        print self.layout.is_expandable()
            
        self.scrollable = kytten.Scrollable(self.layout, 
                                            height=window.height-32,
                                            width=288)
            
        super(TilesetDialog, self).__init__(
            kytten.Dialog(
                kytten.Frame(self.scrollable),
                window=window,
                anchor=kytten.ANCHOR_TOP_RIGHT,
                theme=the_theme))
                
        # Make first palette active
        try:
            self.palette_menu.select(self.palettes.iterkeys().next())
        except:
            pass
            
    def select_tile(self, id):
        for tset_id, tset in self.tilesets.iteritems():
            if id in tset:
                self.palette_menu.select(tset_id)
                self.active_palette.select(id)
            
    def _load_tilesets(self, resource):
        select_id = ''
        for id, ts in resource.findall(tiles.TileSet):
            if id is None:
                self._id_count += 1
                id = 'Untitled' + str(self._id_count)
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
            img = tset.itervalues().next().image
            is_atlas = isinstance(img, pyglet.image.ImageData)
            if self.tile_size != None:
                tile_size = self.tile_size
            else:
                tile_size = img.width   
                while tile_size < 32:
                    tile_size = tile_size * 2
                while tile_size > 32: 
                    tile_size = tile_size // 2
            default_row_tile_count = tile_size // 4
    
            # Sort to keep order
            for i, k in enumerate(sorted(tset, key=str.lower)): 
                texture_set_mag_filter_nearest(tset[k].image.get_texture())
                img = tset[k].image
                option = TilePaletteOption(
                    id=k, 
                    image=tset[k].image, 
                    scale_size=tile_size, 
                    on_edit=self._on_tile_edit)
                if is_atlas:
                    option_index = img.y // img.width
                else:
                    option_index = i // default_row_tile_count
                try:
                    tile_options[option_index].append(option)
                except IndexError:
                    for x in range(option_index):
                        tile_options.append([])
                    tile_options[option_index].append(option)
            if is_atlas:
                tile_options.reverse() # Reverse to match image
            self.palettes[id] = Palette(tile_options, 
                                        on_select=on_tile_select)
        try:
            self.active_palette = self.palettes.itervalues().next()
        except:
            self.active_palette = None
        if self.vlayout is not None:
            self.palette_menu.set_options(
                [k for k, v in self.palettes.iteritems()])
            self.palette_menu.select(select_id)    
            self.vlayout.set([self.palette_menu, self.active_palette])
            
    def _on_tile_edit(self, id):
        tile = self.active_tileset[id]
        on_prop_container_edit(tile, self)
        
    def _make_resource_relative(self, resource):
        # Tilesets filename should be relative to maps
        level_dir = os.path.split(
            self.level_to_edit.filename)[0] + os.sep
            
        # Remove map path from tileset filename
        if level_dir is not '/':
            resource.filename = resource.filename.replace(level_dir, '')
        resource.filename = resource.filename.replace('\\', '/')
        self.level_to_edit.requires.append(('', resource))
        
    def _save_directory_xml(self, filepath, filenames):
        root = ElementTree.Element('resource')
        root.tail = '\n'
        for filename in filenames:
            img_element = ElementTree.SubElement(
                root, 
                'image', 
                id='i-' + os.path.splitext(filename)[0],
                file=filename)
            img_element.tail = '\n'
        xmlname = os.path.splitext(os.path.basename(filepath))[0]
        tset_element = ElementTree.SubElement(
            root, 
            'tileset', 
            id=xmlname)
        tset_element.tail = '\n'
        for filename in filenames:
            t_element = ElementTree.SubElement(
                tset_element, 
                'tile', 
                id=os.path.splitext(filename)[0])
            t_element.tail = '\n'
            img_element = ElementTree.SubElement(
                t_element, 
                'image', 
                ref='i-'+os.path.splitext(filename)[0])
        tree = ElementTree.ElementTree(root)
        tree.write(filepath)
        r = tiles.load(filepath)
        self._load_tilesets(r)
        self._make_resource_relative(r)
        
    def _save_image_xml(self, xmlpath, imagepath, tw, th, padding):
        img = pyglet.image.load(imagepath)
        root = ElementTree.Element('resource')
        root.text = '\n'
        root.tail = '\n'
        size = tw + 'x' + th 
        tw = int(tw)
        th = int(th)
        padding = int(padding)
        double_padding = padding * 2
        xmlname = os.path.splitext(os.path.basename(xmlpath))[0]
        
        # Remove xml path from image path to get relative path
        xmldir = os.path.split(xmlpath)[0] + os.sep
        imagepath = imagepath.replace(xmldir, '')
            
        atlas_element = ElementTree.SubElement(root, 'imageatlas', 
                                               size=size, file=imagepath)
        atlas_element.text = '\n'
        atlas_element.tail = '\n'
        id_count = 0
        for y in reversed(range(padding, img.height, th + double_padding)):
            for x in range(padding, img.width, tw + double_padding):
                img_element = ElementTree.SubElement(
                    atlas_element, 
                    'image', 
                    id='i-%s-%04d' % (xmlname, id_count),
                    offset='%d,%d' % (x, y))
                img_element.tail = '\n'
                id_count += 1
        tset_element = ElementTree.SubElement(root, 'tileset', id=xmlname)
        tset_element.text = '\n'
        tset_element.tail = '\n'
        id_count = 0
        for y in reversed(range(padding, img.height, th + double_padding)):
            for x in range(padding, img.width, tw + double_padding):
                t_element = ElementTree.SubElement(
                    tset_element, 
                    'tile', 
                    id='%s-%04d' % (xmlname, id_count))
                t_element.tail = '\n'
                ElementTree.SubElement(
                    t_element, 
                    'image', 
                    ref='i-%s-%04d' % (xmlname, id_count))
                id_count += 1
        tree = ElementTree.ElementTree(root)
        tree.write(xmlpath)
        r = tiles.load(xmlpath)
        self._load_tilesets(r)
        self._make_resource_relative(r)

    def _create_from_directory_dialog(self):
        dnode = DialogNode()
        def on_select_click(dirpath):
            filepaths = glob.glob(os.path.join(dirpath, '*'))
            filenames = []
            for filepath in filepaths:
                if os.path.isfile(filepath):
                    ext = os.path.splitext(filepath)[1]
                    if ext in the_image_extensions:
                        filenames.append(os.path.basename(filepath)) 
            if len(filenames) is not 0:
                save_dnode = DialogNode()
                def on_save(filepath):
                    self._save_directory_xml(filepath, filenames)
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

    def _create_from_image_dialog(self):
        dnode = DialogNode()
        def on_open_click(imagepath):
            prop_dnode = DialogNode()
            options = []
            tw = 'Tile Width (px)'
            th = 'Tile Height (px)'
            pad = 'Padding (px)'
            map = self.level_to_edit.find(tiles.MapLayer).next()[1]
            options.append((tw, map.tw))
            options.append((th, map.th))
            options.append((pad,'0'))
            def on_submit(dialog):
                values = dialog.get_values()
                def on_save(filepath):
                    self._save_image_xml(filepath, imagepath, 
                                         values[tw], values[th],
                                         values[pad])
                    save_dnode.dialog.on_escape(save_dnode.dialog)
                save_dnode.dialog = kytten.FileSaveDialog(
                    extensions=['.xml'],
                    title='Save Tileset As', 
                    window=self.dialog.window, 
                    theme=self.dialog.theme, 
                    on_select=on_save,
                    on_escape=save_dnode.delete)
                self.parent.add(save_dnode)
                prop_dnode.dialog.on_escape(prop_dnode.dialog)
            prop_dnode.dialog = PropertyDialog(
                'New Tileset', 
                properties=options, 
                window=self.dialog.window, 
                theme=self.dialog.theme,
                on_ok=on_submit,
                on_cancel=prop_dnode.delete)
            self.parent.add(prop_dnode)
            save_dnode = DialogNode()
            dnode.dialog.on_escape(dnode.dialog)
        dnode.dialog = kytten.FileLoadDialog(
            extensions=the_image_extensions, 
            window=self.dialog.window, 
            theme=self.dialog.theme, 
            on_select=on_open_click,
            on_escape=dnode.delete)
        self.parent.add(dnode)

class ToolMenuDialog(DialogNode):
    def __init__(self, window, on_new=None, on_open=None, on_save=None, 
                 map_layers=[], level_to_edit=None):
        self.on_new = on_new
        self.on_open = on_open
        self.on_save = on_save
        self.map_layers = map_layers
        self.level_to_edit = level_to_edit
        tool_layout = self._make_tool_layout()
        layer_layout = self._make_layer_layout()  
        map_menu_layout = self._make_map_menu_layout()  
        super(ToolMenuDialog, self).__init__(kytten.Dialog(
            kytten.Frame(
                kytten.Scrollable(
                    kytten.VerticalLayout([
                        tool_layout,
                        kytten.FoldingSection('Layer', layer_layout),
                        kytten.FoldingSection('Map', map_menu_layout),
                    ], align=kytten.HALIGN_CENTER))
            ),
            window=window,
            anchor=kytten.ANCHOR_TOP_LEFT,
            theme=the_theme))
            
        # Select last layer
        if len(self.map_layers):
            self.layer_menu.select(self.map_layers[-1].id)
        #self.layer_menu = layer_m
        
    def _add_opacity(self, layer):
        # Add opacity functionality to layer instance
        layer.opacity = 255 
        # Probably a way to do this with decorators?
        def enhance(lyr):
            set_dirty = lyr.set_dirty
            def set_dirty_and_opacity():
                set_dirty()
                for s in lyr._sprites.itervalues():
                    s.opacity = lyr.opacity
            return set_dirty_and_opacity
        layer.set_dirty = enhance(layer)
        
    def _make_tool_layout(self):
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
        palette_options = [[]]
        palette_options.append([])
        palette_options.append([])
        for i, pair in enumerate(images):
            option = PaletteOption(id=pair[0], image=pair[1], padding=4)
            
            # Build column down, 3 rows
            palette_options[i%3].append(option)
        def on_tool_select(id):
            self.active_tool = id
        layout = Palette(palette_options, on_select=on_tool_select)
            
        return layout
        
    def _make_layer_layout(self):
        for layer in self.map_layers:
            self._add_opacity(layer)
            
        # Reverse order for menu so layer names are top to bottom    
        layer_options = [layer.id for layer in reversed(self.map_layers)]
        
        if len(self.map_layers):
            def on_opacity_set(value):
                m = self.map_layers.selected
                m.opacity = int(value)
                m.set_dirty()
                #~ for s in m._sprites.itervalues():
                    #~ s.opacity = value
                    #self.map_layers.selected.set_dirty()
        else:
            on_opacity_set = None
        opacity_slider = kytten.Slider(value=255, max_value=255,steps=8, 
                                       width=10, on_set=on_opacity_set)
        def on_layer_select(id):
            for i, layer in enumerate(self.map_layers):
                if layer.id is id:
                    self.map_layers.select(i)
                    opacity_slider.set_pos(
                        self.map_layers.selected.opacity / 255.0)
        self.layer_menu = kytten.Menu(layer_options, on_select=on_layer_select)
        if len(self.map_layers):
            def on_add_layer():
                dnode = DialogNode()
                ID = 'Layer ID'
                TW = 'Tile Width (px)'
                TH = 'Tile Height (px)'
                OZ = 'Z Origin'
                selected = self.map_layers.selected
                tile_width = selected.tw
                tile_height = selected.th
                origin_z = selected.origin_z + 1
                col_count = len(selected.cells)
                row_count = len(selected.cells[0])
                options = [(ID, ''), (TW, tile_width), (TH, tile_height),
                           (OZ, origin_z)]
                cells = [[tiles.RectCell(i, j, tile_width, tile_height, {}, None) 
                          for j in range(col_count)] for i in range(row_count)]
                def on_submit(dialog):
                    values = dialog.get_values()
                    layer = tiles.RectMapLayer(values[ID], int(values[TW]), 
                                               int(values[TH]), cells, 
                                               (0, 0, int(values[OZ])), {})
                    self._add_opacity(layer)
                    self.map_layers.append(layer)
                    self.map_layers.sort(lambda x, y: x.origin_z - y.origin_z)
                    selected.parent.add(layer, z=layer.origin_z)
                    self.level_to_edit.contents[layer.id] = layer
                    self.layer_menu.set_options(
                        [l.id for l in reversed(self.map_layers)])
                    self.layer_menu.select(layer.id)
                    dnode.dialog.on_escape(dnode.dialog)
                dnode.dialog = PropertyDialog(
                    'New Layer', 
                    properties=options, 
                    window=self.dialog.window, 
                    theme=self.dialog.theme,
                    on_ok=on_submit,
                    on_cancel=dnode.delete)
                self.parent.add(dnode)
                    
            def on_remove_layer():
                layers = self.map_layers
                if len(layers) > 1:
                    layers.selected.parent.remove(layers.selected) # scrolling manager
                    layers.remove(layers.selected) # map layers / layer selector
                    del self.level_to_edit.contents[layers.selected.id] # resource
                    self.layer_menu.set_options([l.id for l in reversed(layers)])
                    self.layer_menu.select(layers[-1].id)
            def on_layer_prop_edit(choice):
                on_prop_container_edit(self.map_layers.selected, self)
        else:
            on_add_layer = None
            on_remove_layer = None
            on_layer_prop_edit = None
            on_opacity_set = None
        layout = kytten.VerticalLayout([
            kytten.HorizontalLayout([
                kytten.Label('op'),
                opacity_slider]),
            self.layer_menu,
            
            kytten.HorizontalLayout([
                kytten.Button('+', on_click=on_add_layer),
                kytten.Button('x', on_click=on_remove_layer)]),
            NoSelectMenu(
                options=['Properties'],
                on_select=on_layer_prop_edit),])
                
        return layout

    def _make_map_menu_layout(self):
        def on_select(choice):
            if choice == 'New':
                self._create_new_dialog()
            elif choice == 'Open':
                self._create_open_dialog()
            elif choice == 'Save':
                if self.on_save is not None:
                    self.on_save()
            elif choice == 'Quit':
                director.pop()
        layout = kytten.VerticalLayout([
            NoSelectMenu(
                options=['New', 'Open', 'Save', 'Quit'],
                on_select=on_select)])
                
        return layout
            
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
