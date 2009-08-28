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
from cocos.director import director

import kytten

from tile_widgets import *
from dialog_node import *

VERSION = 'Cocograph 1.0a1'

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
                    level_dir = os.path.split(
                        level_to_edit.filename)[0] + os.sep
                    # tilesets should be relative to maps
                    r.filename = r.filename.replace(level_dir, '')
                    r.filename = r.filename.replace('\\', '/')
                    self.level_to_edit.requires.append(('',r))
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
                    self.level_to_edit.requires.append(('',r))
                    self._load_tilesets(r) 
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
        images = []
        images.append(('move',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'transform-move.png'))))
        images.append(('picker',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'color-picker.png'))))
        #images.append(('fill',pyglet.image.load('color-fill.png')))
        images.append(('zoom',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'page-magnifier.png'))))
        images.append(('pencil',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'draw-freehand.png'))))
        images.append(('eraser',pyglet.image.load(
            os.path.join('theme', 'artlibre', 'draw-eraser.png'))))

        options = [[]]
        options.append([])
        options.append([])
        for i, pair in enumerate(images):
            option = PaletteOption(id=pair[0], image=pair[1], padding=4)
            options[i%3].append(option)
            
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
                for column in range(int(v[mh])):
                    col = ElementTree.SubElement(m, 'column')
                    col.tail = '\n'
                    for cell in range(int(v[mw])):
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


def _zoom_in(scale):
    if scale > 4: return scale
    else: return scale * 2.0

def _zoom_out(scale):
    if scale < .01: return scale 
    else: return scale / 2.0
                                    
class TileEditorLayer(tiles.ScrollableLayer):
    is_event_handler = True

    def __init__(self, tiles, tools, level_to_edit=None, filename=None, 
                 map_layers=None,):
                     
        super(TileEditorLayer, self).__init__()
        self.level_to_edit = level_to_edit
        self.filename = filename
        self.highlight = None
        self.tiles = tiles
        self.tools = tools
        self.map_layers = map_layers
        w, h = director.get_window_size()
        
    _space_down = False
    def on_key_press(self, key, modifier):
        # Don't exit on ESC
        if key == pyglet.window.key.ESCAPE:
            return True
        #~ elif key == pyglet.window.key.S:
            #~ self.level_to_edit.save_xml(self.filename)
            
        if modifier & pyglet.window.key.MOD_ACCEL:
            if key == pyglet.window.key.Q:
                director.pop()
            elif key == pyglet.window.key.MINUS:
                self._desired_scale = _zoom_out(self._desired_scale)
                self.parent.set_scale(self._desired_scale)
            elif key == pyglet.window.key.EQUAL:
                self._desired_scale = _zoom_in(self._desired_scale)
                self.parent.set_scale(self._desired_scale)
            elif key == pyglet.window.key.D:
                m = self.map_layers.selected
                m.set_debug(not m.debug)

        if key == pyglet.window.key.SPACE:
            self._space_down = True
            win = director.window
            cursor = win.get_system_mouse_cursor(pyglet.window.Window.CURSOR_SIZE)
            win.set_mouse_cursor(cursor)
            
    def on_key_release(self, key, modifier):
        if key == pyglet.window.key.SPACE:
            self._space_down = False
            win = director.window
            win.set_mouse_cursor()
            return True
        return True

    _desired_scale = 1
    def on_mouse_scroll(self, x, y, dx, dy):
        if dy < 0:
            self._desired_scale = _zoom_out(self._desired_scale)
            #self.parent.set_scale(self._desired_scale)
        elif dy > 0:
            self._desired_scale = _zoom_in(self._desired_scale)
            #self.parent.set_scale(self._desired_scale)
        if dy:
            self.parent.do(actions.ScaleTo(self._desired_scale, .1))
            return True

    def on_text_motion(self, motion):
        fx, fy = self.parent.fx, self.parent.fy
        if motion == pyglet.window.key.MOTION_UP:
            self.parent.set_focus(fx, fy+64/self._desired_scale)
        elif motion == pyglet.window.key.MOTION_DOWN:
            self.parent.set_focus(fx, fy-64/self._desired_scale)
        elif motion == pyglet.window.key.MOTION_LEFT:
            self.parent.set_focus(fx-64/self._desired_scale, fy)
        elif motion == pyglet.window.key.MOTION_RIGHT:
            self.parent.set_focus(fx+64/self._desired_scale, fy)
        else:
            return False
        return True

    _dragging = False
    def on_mouse_press(self, x, y, buttons, modifiers):
        self._drag_start = (x, y)
        self._dragging = False
        if not self._space_down:
            m = self.map_layers.selected
            mx, my = self.parent.pixel_from_screen(x, y)
            cell = m.get_at_pixel(mx, my)
            self._current_cell = cell
            if not cell:
                # click not in map
                return
            cx, cy = sprite_key = cell.origin[:2]
            if modifiers & pyglet.window.key.MOD_ACCEL:
                _on_prop_container_edit(cell, self.tiles)
            elif self.tools.active_tool is 'zoom':
                if buttons & pyglet.window.mouse.LEFT:
                    self._desired_scale = _zoom_in(self._desired_scale)
                elif buttons & pyglet.window.mouse.RIGHT:
                    self._desired_scale = _zoom_out(self._desired_scale)
                self.parent.set_scale(self._desired_scale)
            elif self.tools.active_tool is 'pencil': 
                if buttons & pyglet.window.mouse.LEFT:
                    cell.tile = self.tiles.selected
                    # Set dirty is not dirty enough for performance
                    m._sprites[sprite_key] = pyglet.sprite.Sprite(
                        cell.tile.image, x=cx, y=cy, batch=m.batch)
                    #m.set_dirty()
                elif buttons & pyglet.window.mouse.RIGHT:
                    # picker
                    if cell.tile is not None:
                        self.tiles.select_tile(cell.tile.id)
            elif self.tools.active_tool is 'eraser':
                if cell.tile is not None:
                    cell.tile = None
                    # clear properties
                    del m._sprites[sprite_key]
            elif self.tools.active_tool is 'picker':
                if cell.tile is not None:
                    self.tiles.select_tile(cell.tile.id)

            return True
            
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if not self._dragging and self._drag_start:
            _x, _y = self._drag_start
            if abs(x - _x) + abs(y - _y) < 6:
                return False
        self._dragging = True 
        if self._space_down or self.tools.active_tool is 'move':
            self.parent.set_focus(
                self.parent.fx-(dx/self._desired_scale),
                self.parent.fy-(dy/self._desired_scale))
            return True
        if self.tools.active_tool is 'pencil' or 'eraser':
            m = self.map_layers.selected
            mx, my = self.parent.pixel_from_screen(x, y)
            cell = m.get_at_pixel(mx, my)
            
            #don't update if we haven't moved to a new cell
            if cell == self._current_cell or not cell:
                return
            cx, cy = sprite_key = cell.origin[:2]
            self._current_cell = cell
            x = cell.x 
            y = cell.y 
            self.highlight = (x, y, x+m.tw, y+m.th)

            if self.tools.active_tool is 'pencil':
                cell.tile = self.tiles.selected
                m._sprites[sprite_key] = pyglet.sprite.Sprite(
                    cell.tile.image, x=cx, y=cy, batch=m.batch)
                #m.set_dirty()
            elif self.tools.active_tool is 'eraser':
                if cell.tile is not None:
                    cell.tile = None
                    del m._sprites[sprite_key]
        return True

    def on_mouse_release(self, x, y, buttons, modifiers):
        if self._dragging:
            self._dragging = False
            return False

    def on_mouse_motion(self, x, y, dx, dy):
        m = self.map_layers.selected
        w = director.window
        x, y = w._mouse_x, w._mouse_y


        cell = m.get_at_pixel(*self.parent.pixel_from_screen(x, y))
        if not cell:
            self.highlight = None
            return True
        x = cell.x 
        y = cell.y 
        self.highlight = (x, y, x+m.tw, y+m.th)

        return True

    def draw(self):
        if self.highlight is None:
            return
        if self.map_layers is not None:
            glPushMatrix()
            self.transform()
            glPushAttrib(GL_CURRENT_BIT | GL_ENABLE_BIT)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(1, 1, 0, .3)
            glRectf(*self.highlight)
            glPopAttrib()
            glPopMatrix()


class ScrollableColorLayer(cocos.layer.util_layers.ColorLayer, 
                           tiles.ScrollableLayer):
    def __init__(self, r,g,b,a, width=None, height=None):
        super(ScrollableColorLayer, self).__init__(
            r,g,b,a, width, height)
        self.px_width, self.px_height = width, height

class EditorScene(cocos.scene.Scene):
    def __init__(self):
        super(EditorScene, self).__init__()
        self.manager = tiles.ScrollingManager()
        self.add(self.manager)
        self.map_layers = []
        self.dialog_layer = DialogLayer()
        self.editor_layer = None
        self.tool_dialog = ToolMenuDialog(director.window, 
                                          on_open=self.open)
        self.tile_dialog = None
        self.dialog_layer.add_dialog(self.tool_dialog)
        self.add(self.dialog_layer)

    def open(self, edit_level_xml):
        # Clean up old dialogs
        self.remove(self.manager)
        self.manager = tiles.ScrollingManager()
        if self.tile_dialog is not None:
            self.tile_dialog.delete()
        self.tool_dialog.delete()
        self.remove(self.dialog_layer)
        
        # Load level
        #~ try:
        level_to_edit = tiles.load(edit_level_xml)
        #~ except:
            #~ self.tool_dialog = ToolMenuDialog(director.window, 
                                              #~ on_open=self.open)
            #~ return
            
        # Setup new dialogs and layers   
        director.window.set_caption(edit_level_xml + ' - ' + VERSION)
        self.selected = level_to_edit.find(tiles.MapLayer).next()[1]
        self.tile_dialog = TilesetDialog(director.window, level_to_edit) 
        def on_save():
            level_to_edit.save_xml(edit_level_xml)
        def on_edit():
            _on_prop_container_edit(self.selected, self.tool_dialog)
        self.tool_dialog = ToolMenuDialog(director.window, 
            on_open=self.open, on_save=on_save, on_edit=on_edit)
        
        bg_layer = ScrollableColorLayer(255, 255, 255, 255, 
            width=self.selected.px_width, 
            height=self.selected.px_height)
        self.manager.add(bg_layer, z=-1)
        mz = 0
        for id, layer in level_to_edit.find(tiles.MapLayer):
            self.map_layers.append(layer)
            self.manager.add(layer, z=layer.origin_z)
            mz = max(layer.origin_z, mz)

        self.editor_layer = TileEditorLayer(
            level_to_edit=level_to_edit, tiles=self.tile_dialog, 
            map_layers=self, tools=self.tool_dialog, 
            filename=edit_level_xml)
            
        self.manager.add(self.editor_layer, z=mz+1)
        self.add(self.manager)
        self.dialog_layer.add_dialog(self.tile_dialog)
        self.dialog_layer.add_dialog(self.tool_dialog)
        
        # XXX if I don't remove and add the dlayer event handling is 
        # messed up...why?
        self.add(self.dialog_layer, z=mz+2) 
        
    def edit_complete(self, layer):
        pyglet.app.exit()


if __name__ == '__main__':
    import sys
    
    try:
        edit_level_xml = sys.argv[1]
    except IndexError:
        edit_level_xml = None
    except:
        print 'Usage: %s <level.xml>'%sys.argv[0]
        sys.exit(0)

    director.init(width=800, height=600, resizable=True, 
                  do_not_scale=True, caption=VERSION)
    director.show_FPS = True
    pyglet.gl.glClearColor(.3, .3, .3, 1)
    e = EditorScene()
    director.run(e)
    if edit_level_xml is not None:
        e.open(edit_level_xml)
    
    


