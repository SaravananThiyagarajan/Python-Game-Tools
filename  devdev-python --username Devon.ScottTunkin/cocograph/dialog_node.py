import pyglet

import cocos
from cocos.director import director

import kytten


class DialogNode(cocos.batch.BatchableNode):
    def __init__(self, dialog=None):
        super(DialogNode, self).__init__()
        self.dialog = dialog
        
    def set_batch(self, batch, group):
        super(DialogNode, self).set_batch(batch, group)
        if self.dialog is not None:
            self.dialog.batch = self.batch
            self.dialog.group = self.group
            
    def delete(self, dialog=None):
        super(DialogNode, self).on_exit()
        self.parent.remove(self)
        self.dialog.teardown()
              
    def draw(self):
        pass
        
        
class DialogLayer(cocos.layer.Layer):
    is_event_handler = True
    def __init__(self, dialog=None):
        super(DialogLayer, self).__init__()
        self.batchnode = cocos.batch.BatchNode()
        #self.batchnode.position = 50,100
        self.add(self.batchnode)
        #self.batch = pyglet.graphics.Batch()
        #self.group = pyglet.graphics.OrderedGroup(0)
        director.window.register_event_type('on_update')        
        def update(dt):
            director.window.dispatch_event('on_update', dt)
        self.schedule(update)

    def add_dialog(self, dialog_node):
        if dialog_node is not None:
            self.batchnode.add(dialog_node)
        
    def on_key_press(self, symbol, modifiers):
        for c in self.batchnode.get_children():
            if c.dialog.focus and hasattr(c.dialog.focus, 
                                          'on_key_press'):
                return True 

    def on_key_release(self, symbol, modifiers):
        for c in self.batchnode.get_children():
            if c.dialog.on_key_release(symbol, modifiers):
                return True

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        for c in self.batchnode.get_children():
            if c.dialog.on_mouse_drag(x, y, dx, dy, buttons, modifiers) \
            or c.dialog.focus != None:
                return True 

    def on_mouse_motion(self, x, y, dx, dy):
        for c in self.batchnode.get_children():
            c.dialog.on_mouse_motion(x, y, dx, dy)
            if c.dialog.hover is not None:
                return True
            else:
                c.dialog.set_focus(None)

    def on_mouse_press(self, x, y, button, modifiers):
        was_handled = False
        for c in self.batchnode.get_children():
            if c.dialog.on_mouse_press(x, y, button, modifiers):
                was_handled = True
        return was_handled
            #~ c.dialog.set_wheel_hint(None)
            #~ c.dialog.set_wheel_target(None)

    def on_mouse_release(self, x, y, button, modifiers):
        was_handled = False
        for c in self.batchnode.get_children():
            if c.dialog.on_mouse_release(x, y, button, modifiers):
                was_handled = True  
        return was_handled

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        for c in self.batchnode.get_children():
            if c.dialog.on_mouse_scroll(x, y, scroll_x, scroll_y):
                return True

    def on_text(self, text):
         for c in self.batchnode.get_children():
            if c.dialog.focus and hasattr(c.dialog.focus, 'on_text'):
                return True 

    def on_text_motion(self, motion):
        for c in self.batchnode.get_children():
            if c.dialog.focus and hasattr(c.dialog.focus, 
                                          'on_text_motion'):
                return True

    def on_text_motion_select(self, motion):
        for c in self.batchnode.get_children():
            if c.dialog.focus and hasattr(c.dialog.focus, 
                                          'on_text_motion_select'):
                return True  
