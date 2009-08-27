import os
import pyglet
import kytten
from kytten import *
from kytten.widgets import Control, Widget
from kytten.layout import *
from kytten.dialog import Dialog
from kytten.frame import *
from kytten.button import *
from kytten.menu import *


class PaletteOption(Control):
    """
    PaletteOption is a choice within a palette.  It is similar to 
    MenuOption but contains an image/id instead of label/text. When 
    selected, it becomes highlighted to indicate it has been chosen.
    """
    def __init__(self, id, image, scale_size=None, anchor=ANCHOR_CENTER, 
                 palette=None, disabled=False, padding=0):
        Control.__init__(self, disabled=disabled)
        self.id = id
        self.image = image
        self.scale_size = scale_size
        self.anchor = anchor
        self.palette = palette
        self.sprite = None
        self.background = None
        self.highlight = None
        self.is_selected = False
        self.padding = padding
        
    def delete(self):
        if self.sprite is not None:
            self.sprite.delete()
            self.sprite = None
        if self.background is not None:
            self.background.delete()
            self.background = None
        if self.highlight is not None:
            self.highlight.delete()
            self.highlight = None
            
    #~ def expand(self, width, height):
        #~ self.width = width
        #~ self.height = height

    #~ def is_expandable(self):
        #~ return False

    def layout(self, x, y):
        self.x, self.y = x, y
        if self.background is not None:
            self.background.update(x, y, self.width, self.height)
        if self.highlight is not None:
            self.highlight.update(x, y, self.width, self.height)
        #height = 32 #self.tile_height
        w, h = self.sprite.width, self.sprite.height
        x, y = GetRelativePoint(self, self.anchor,
                                Widget(w, h),
                                self.anchor, (0, 0))
        self.sprite.x = x #+ self.padding / 2
        self.sprite.y = y #+ self.padding / 2
        
    #~ def on_gain_highlight(self):
        #~ Control.on_gain_highlight(self)

    #~ def on_lose_highlight(self):
        #~ Control.on_lose_highlight(self)

    def on_mouse_release(self, x, y, button, modifiers):
        self.palette.select(self.id)#(self.text)

    def select(self):
        if self.is_disabled():
            return  # disabled options can't be selected
        self.is_selected = True
        self.size(self.saved_dialog)  # to set up the highlight
        if self.highlight is not None:
            self.highlight.update(self.x, self.y,
                                  self.width, self.height)
        if self.saved_dialog is not None:
            self.saved_dialog.set_needs_layout()

    def size(self, dialog):
        if dialog is None:
            return
        Control.size(self, dialog)
        if self.is_selected:
            path = ['menuoption', 'selection']
        else:
            path = ['menuoption']
        if self.sprite is None:
            if self.is_disabled():
                opacity = 50
                color = dialog.theme[path]['disabled_color']
            else:
                opacity = 255
                color = dialog.theme[path]['text_color']
            self.sprite = pyglet.sprite.Sprite( 
                self.image, batch=dialog.batch, group=dialog.fg_group)#, y=y, x=x, batch=self.tiles_batch)
            self.sprite.opacity = opacity
            if self.scale_size is not None:
                self.sprite.scale = self.scale_size / float(self.sprite.width)
            self.width = self.sprite.width + self.padding * 2
            self.height = self.sprite.height + self.padding * 2

        #~ if self.background is None:
            #~ if self.is_selected:
                #~ self.background = \
                    #~ dialog.theme[path]['highlight']['image'].generate(
                        #~ dialog.theme[path]['gui_color'],
                        #~ dialog.batch,
                        #~ dialog.bg_group)

        if self.highlight is None:
            if self.is_selected:
                self.highlight = \
                    dialog.theme[path]['palette']['image'].generate(
                        dialog.theme[path]['input']['gui_color'],
                        dialog.batch,
                        dialog.highlight_group)

    def unselect(self):
        self.is_selected = False
        if self.highlight is not None:
            self.highlight.delete()
            self.highlight = None
        if self.background is not None:
            self.background.delete()
            self.background = None
        if self.saved_dialog is not None:
            self.saved_dialog.set_needs_layout()

    def teardown(self):
        self.palette = None
        self.image = None
        Control.teardown(self)
    
class TilePaletteOption(PaletteOption):
    def __init__(self, id, image, scale_size=None, anchor=ANCHOR_CENTER, 
                 palette=None, disabled=False, on_edit=None):
        self.on_edit = on_edit
        PaletteOption.__init__(self, id=id, image=image, 
                               scale_size=scale_size, anchor=anchor, 
                               palette=palette, disabled=disabled)
                               
    def on_mouse_release(self, x, y, button, modifiers):
        if modifiers & pyglet.window.key.MOD_ACCEL:
            if self.palette is not None:
                self.on_edit(self.id)
        PaletteOption.on_mouse_release(self, x, y, button, modifiers)
        return True
                               
class Palette(GridLayout):
    """
    Palette is a GridLayout of PaletteOptions.  Clicking a PaletteOption
    selects it and causes Palette to send an on_click event.
    """
    def __init__(self, options=[[]], padding=2, on_select=None ):
        #~ menu_options = self._make_options(options)

        GridLayout.__init__(self, options, padding=padding)
        self.on_select = on_select
        self.selected = None
        self.options = {}
        for row in options:
            for option in row:
                self.options[option.id] = option
                if option is not None:
                    option.palette = self
        if options[0][0] is not None:
            self.select(options[0][0].id)
        #self.on_select(self.get(0, 0).id)
        #print self.selected


    #~ def _make_options(self, options):
        #~ menu_options = []
        #~ for option in options:
            #~ if option.startswith('-'):
                #~ disabled = True
                #~ option = option[1:]
            #~ else:
                #~ disabled = False
            #~ menu_options.append(MenuOption(option,
                                           #~ anchor=(VALIGN_CENTER, self.align),
                                           #~ menu=self,
                                           #~ disabled=disabled))
        #~ return menu_options

    def get_value(self):
        return self.selected

    def is_input(self):
        return True

    def select(self, id):
        if self.selected is not None:
            self.selected.unselect()
        self.selected = self.options[id]
        self.selected.select()
        if self.on_select is not None:
            self.on_select(id)
        #print self.selected

    def set_options(self, options):
        self.delete()
        self.selected = None
        #menu_options = self._make_options(options)
        #self.options = dict(zip(options, menu_options))
        
        #~ i = 0
        #~ for row in option:
            #~ j = 0
            #~ for cell in row:
                #~ self.set(cell)
                #~ j++
            #~ i++
        #~ self.set(menu_options)
        self.saved_dialog.set_needs_layout()

    def teardown(self):
        self.on_select = None
        GridLayout.teardown(self)
        
class HorizontalMenuOption(MenuOption):
    def __init__(self, text="", anchor=ANCHOR_CENTER, menu=None,
                 disabled=False):
        MenuOption.__init__(self, text=text, anchor=anchor, menu=menu,
                            disabled=disabled)
                        
    def on_gain_highlight(self):
        Control.on_gain_highlight(self)
        self.size(self.saved_dialog)  # to set up the highlight
        if self.highlight is not None:
            self.highlight.update(self.x-self.menu.padding/2, 
                                  self.y,
                                  self.width+self.menu.padding,
                                  self.height)
    def layout(self, x, y):
        self.x, self.y = x, y
        if self.background is not None:
            self.background.update(x-self.menu.padding/2, y,
                self.width+self.menu.padding, self.height)
        if self.highlight is not None:
            self.highlight.update(x-self.menu.padding/2, y,
                self.width+self.menu.padding, self.height)
        font = self.label.document.get_font()
        height = font.ascent - font.descent
        x, y = GetRelativePoint(self, self.anchor,
                                Widget(self.label.content_width, height),
                                self.anchor, (0, 0))
        self.label.x = x
        self.label.y = y - font.descent
        
        
    def is_expandable(self):
        return False
        
    def select(self):
        if self.is_disabled():
            return  # disabled options can't be selected

        self.is_selected = True
        if self.label is not None:
            self.label.delete()
            self.label = None
        if self.saved_dialog is not None:
            self.saved_dialog.set_needs_layout()

class HorizontalMenu(HorizontalLayout, Menu):
    def __init__(self, options=[], align=VALIGN_CENTER, padding=8,
                 on_select=None):
        Menu.__init__(self, options, padding=padding, on_select=on_select)
        HorizontalLayout.__init__(self, self.content,
                                  align=align, padding=padding)
                                  
    def _make_options(self, options):
        menu_options = []
        for option in options:
            if option.startswith('-'):
                disabled = True
                option = option[1:]
            else:
                disabled = False
            menu_options.append(HorizontalMenuOption(option,
                anchor=(VALIGN_CENTER, self.align),
                menu=self, 
                disabled=disabled))
        return menu_options
        
    def layout(self, x, y):
        """
        Lays out the child Widgets, in order from left to right.

        @param x X coordinate of the lower left corner
        @param y Y coordinate of the lower left corner
        """
        Widget.layout(self, x, y)

        # Expand any expandable content to our height
        for item in self.content:
            if item.is_expandable() and item.height < self.height:
                item.expand(item.width, self.height)

        left = x+self.padding/2
        if self.align == VALIGN_TOP:
            for item in self.content:
                item.layout(left, y + self.height - item.height)
                left += item.width + self.padding
        elif self.align == VALIGN_CENTER:
            for item in self.content:
                item.layout(left, y + self.height/2 - item.height/2)
                left += item.width + self.padding
        else: # VALIGN_BOTTOM
            for item in self.content:
                item.layout(left, y)
                left += item.width + self.padding
                
    def size(self, dialog):
        """
        Calculates size of the layout, based on its children.

        @param dialog The Dialog which contains the layout
        """
        if dialog is None:
            return
        Widget.size(self, dialog)
        height = 0
        if len(self.content) < 2:
            width = 0
        else:
            width = -self.padding
        for item in self.content:
            item.size(dialog)
            height = max(height, item.height)
            width += item.width + self.padding
        self.width, self.height = width+self.padding, height
        self.expandable = [x for x in self.content if x.is_expandable()]
                
class NoSelectMenu(Menu):
    """
    A menu that does not stay selected.
    """
    def __init__(self, options=[], align=HALIGN_CENTER, padding=4,
                 on_select=None):
        Menu.__init__(self, options=options, align=align, 
                      padding=padding, on_select=on_select)

    def select(self, text):
        if not text in self.options:
            return

        if self.selected is not None:
            self.options[self.selected].unselect()
        self.selected = text
        menu_option = self.options[text]
        #menu_option.select()

        if self.on_select is not None:
            self.on_select(text)
        
class PropertyDialog(Dialog):
    """
    An ok/cancel-style dialog for editing properties. Options must be a
    dictionary of name/values. Escape defaults to cancel.
    
    @ has_remove allows for deleting options and returns
    @ _REMOVE_PRE+option id = True for get_values()
    """
    _id_count = 0
    REMOVE_PRE = '_X!'
    TYPE_PRE = '_T!'
    ADD_NAME_PRE = '_N!'
    ADD_VALUE_PRE = '_V!'
    INPUT_W = 12
    def __init__(self, title="", properties={}, ok="Ok", cancel="Cancel",
                 window=None, batch=None, group=None, theme=None,
                 on_ok=None, on_cancel=None, has_remove=False, 
                 remove="x", has_add=False, add="+", on_add=None):
                     
        def on_ok_click(dialog=None):
            if on_ok is not None:
                on_ok(self)
            self.teardown()

        def on_cancel_click(dialog=None):
            if on_cancel is not None:
                on_cancel(self)
            self.teardown()
            
        self.remove = remove
        self._has_remove = has_remove
        self._has_add = has_add
        property_table = self._make_properties(properties)
        grid = GridLayout(property_table, padding=8)
        
        def on_type_select(id, choice):
            item = Checkbox() if choice is 'bool' else Input(length=self.INPUT_W)
            for i, row in enumerate(grid.content):
                for cell in row:
                    if isinstance(cell, Dropdown):
                        if cell.id == id:
                            item_id = grid.get(1,i).id
                            item.id = item_id
                            grid.set(row=i, column=1, item=item)
                            break
                            
        def on_add_click(dialog=None):
            if on_add is not None:
                on_add(self)
            else:
                pd = PropertyDialog
                pd._id_count += 1
                grid.add_row([
                    Input(id=pd.ADD_NAME_PRE+str(pd._id_count), 
                        length=self.INPUT_W), 
                    Input(id=pd.ADD_VALUE_PRE+str(pd._id_count),
                        length=self.INPUT_W), 
                    Dropdown(['unicode', 'bool', 'int', 'float'], 
                              id=pd.TYPE_PRE+str(pd._id_count),
                              on_select=on_type_select)
                ])
        
        if self._has_add:
            add_content = (ANCHOR_TOP_LEFT, 0, 0, Button(add, on_click=on_add_click))
            Dialog.__init__(self, content=Frame(Scrollable(
                VerticalLayout([
                    SectionHeader(title, align=HALIGN_LEFT),
                    grid,
                    FreeLayout(content=[add_content]),
                    Spacer(height=30),
                    HorizontalLayout([
                        Button(ok, on_click=on_ok_click),
                        Button(cancel, on_click=on_cancel_click)])
                ]),height=window.height)),
                window=window, batch=batch, group=group,
                theme=theme, movable=True,
                on_enter=on_ok_click, on_escape=on_cancel_click)
        else:
            Dialog.__init__(self, content=Frame(Scrollable(
                VerticalLayout([
                    SectionHeader(title, align=HALIGN_LEFT),
                    grid,
                    Spacer(height=30),
                    HorizontalLayout([
                        Button(ok, on_click=on_ok_click),
                        Button(cancel, on_click=on_cancel_click)])
                ]),height=window.height)),
                window=window, batch=batch, group=group,
                theme=theme, movable=True,
                on_enter=on_ok_click, on_escape=on_cancel_click)
                    
    def _make_properties(self, properties):    
        property_table = [[]]
        for name, value in properties:
            if isinstance(value, bool):
                property = Checkbox(is_checked=value, id=name)
            else:
                property = Input(name, unicode(value), length=self.INPUT_W)   
            if self._has_remove:
                property_table.append([Label(name), property,
                    Checkbox(self.remove, 
                        id=PropertyDialog.REMOVE_PRE+name)])
            else:
                property_table.append([Label(name), property])
        return property_table


