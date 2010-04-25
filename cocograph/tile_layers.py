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

from cocos.director import director
from tile_dialogs import *


VERSION = 'Cocograph 0.2.0'

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
            self.parent.force_focus(fx, fy+64/self._desired_scale)
        elif motion == pyglet.window.key.MOTION_DOWN:
            self.parent.force_focus(fx, fy-64/self._desired_scale)
        elif motion == pyglet.window.key.MOTION_LEFT:
            self.parent.force_focus(fx-64/self._desired_scale, fy)
        elif motion == pyglet.window.key.MOTION_RIGHT:
            self.parent.force_focus(fx+64/self._desired_scale, fy)
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
            if not cell:
                # click not in map
                return
            self._current_cell = cell
            cx, cy = sprite_key = cell.origin[:2]
            
            # ctrl-click edit tile properties
            if modifiers & pyglet.window.key.MOD_ACCEL:
                on_prop_container_edit(cell, self.tiles)
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
                    m._sprites[sprite_key].opacity = m.opacity
                    #m.set_dirty()
                    
                # Picker    
                elif buttons & pyglet.window.mouse.RIGHT: 
                    if cell.tile is not None:
                        self.tiles.select_tile(cell.tile.id)
            elif self.tools.active_tool is 'eraser':
                if cell.tile is not None:
                    cell.tile = None
                    del m._sprites[sprite_key] # Clear properties
            elif self.tools.active_tool is 'picker':
                if cell.tile is not None:
                    self.tiles.select_tile(cell.tile.id)
            elif self.tools.active_tool is 'fill':
                if self.tiles.selected is cell.tile:
                    return True
                old_tile = cell.tile
                cells_to_fill = []
                cells_to_fill.append(cell)
                while len(cells_to_fill):
                    c = cells_to_fill.pop()
                    c.tile = self.tiles.selected
                    next_c = m.get_neighbor(c, m.RIGHT)
                    if next_c and next_c.tile is old_tile:
                        cells_to_fill.append(next_c)
                    next_c = m.get_neighbor(c, m.LEFT)
                    if next_c and next_c.tile is old_tile:
                        cells_to_fill.append(next_c)
                    next_c = m.get_neighbor(c, m.UP)
                    if next_c and next_c.tile is old_tile:
                        cells_to_fill.append(next_c)
                    next_c = m.get_neighbor(c, m.DOWN)
                    if next_c and next_c.tile is old_tile:
                        cells_to_fill.append(next_c)
                m.set_dirty()
                
            return True
            
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if not self._dragging and self._drag_start:
            _x, _y = self._drag_start
            if abs(x - _x) + abs(y - _y) < 6:
                return False
        self._dragging = True 
        if self._space_down or self.tools.active_tool is 'move':
            self.parent.force_focus(
                self.parent.fx-(dx/self._desired_scale),
                self.parent.fy-(dy/self._desired_scale))
            return True
        if self.tools.active_tool is 'pencil' or 'eraser':
            m = self.map_layers.selected
            mx, my = self.parent.pixel_from_screen(x, y)
            cell = m.get_at_pixel(mx, my)
            
            #don't update if we haven't moved to a new cell
            if cell is None or cell == self._current_cell:
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
                m._sprites[sprite_key].opacity = m.opacity
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
        
class Selector(list):
    def __init__(self, lst):
        super(Selector, self).__init__(lst)
        self.selected = self[0]

    def select(self, i):
        self.selected = self[i]

class EditorScene(cocos.scene.Scene):
    def __init__(self):
        super(EditorScene, self).__init__()
        self.manager = tiles.ScrollingManager()
        self.add(self.manager)
        self.dialog_layer = DialogLayer()
        #self.scrollbar_layer = DialogLayer()
        #self.dialog_layer.add_dialog(DialogNode(kytten.Dialog(kytten.Frame(kytten.Scrollable(kytten.Spacer(100, 100), width=50, height=50)))))
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
        #self.remove(self.scrollbar_layer)
        self.remove(self.dialog_layer)
        
        # Load level
        #~ try:
        level_to_edit = tiles.load(edit_level_xml)
        #~ except:
            #~ self.tool_dialog = ToolMenuDialog(director.window, 
                                              #~ on_open=self.open)
            #~ return
        #self.map_layers = level_to_edit.findall(tiles.MapLayer)
        director.window.set_caption(edit_level_xml + " - " + VERSION)
        
        # Setup map layers
        mz = 0
        for id, layer in level_to_edit.find(tiles.MapLayer):
            self.manager.add(layer, z=layer.origin_z)
            mz = max(layer.origin_z, mz)
        
        # Copy z-sorted manager.children to selector
        self.layer_selector = Selector(self.manager.get_children()[:])
            
        bg_layer = ScrollableColorLayer(
            255, 255, 255, 255, 
            width=self.layer_selector.selected.px_width, 
            height=self.layer_selector.selected.px_height)
        self.manager.add(bg_layer, z=-999999)

        # Setup new dialogs  
        self.tile_dialog = TilesetDialog(director.window, level_to_edit) 
        def on_resize(width, height):
            self.tile_dialog.scrollable.max_height = height - 48
        self.dialog_layer.on_resize = on_resize
        def on_save():
            level_to_edit.save_xml(edit_level_xml)
        self.tool_dialog = ToolMenuDialog(
            director.window, 
            on_open=self.open, 
            on_save=on_save,
            map_layers=self.layer_selector,
            level_to_edit=level_to_edit)
        self.dialog_layer.add_dialog(self.tile_dialog)
        self.dialog_layer.add_dialog(self.tool_dialog)

        self.editor_layer = TileEditorLayer(
            level_to_edit=level_to_edit, 
            tiles=self.tile_dialog, 
            map_layers=self.layer_selector, 
            tools=self.tool_dialog, 
            filename=edit_level_xml)
        self.manager.add(self.editor_layer, z=mz+1)
        
        self.add(self.manager)
        
        # XXX if I don't remove and add the dlayer event handling is 
        # messed up...why?
        #self.add(self.scrollbar_layer, z=mz+2)
        self.add(self.dialog_layer, z=mz+3) 
        
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
    
    


