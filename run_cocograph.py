import pyglet
# Disable error checking for increased performance
pyglet.options['debug_gl'] = False
from pyglet.gl import *


import cocos
from cocos import tiles, actions
from cocos.director import director

import kytten

import cocograph
from cocograph import tile_layers

#~ pyglet.resource.path.append('maps/dungeon/data')
#~ pyglet.resource.reindex()

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
                  do_not_scale=True, caption=tile_layers.VERSION)
    director.show_FPS = True
    pyglet.gl.glClearColor(.3, .3, .3, 1)
    e = tile_layers.EditorScene()
    director.run(e)
    if edit_level_xml is not None:
        e.open(edit_level_xml)

