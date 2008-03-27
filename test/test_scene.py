# This code is so you can run the samples without installing the package
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
#


import cocos
from cocos.director import director
from cocos.actions import ActionSprite
from cocos.layer import *
import pyglet
from cocos.test_actions import *

class TestLayer(cocos.layer.Layer):
    def __init__(self):
        super( TestLayer, self ).__init__()
        
        x,y = director.get_window_size()
        
        image = pyglet.resource.image('grossini.png')
        image.anchor_x = image.width / 2
        image.anchor_y = image.height / 2
        sprite1 = ActionSprite( image )

        image = pyglet.resource.image('grossinis_sister1.png')
        image.anchor_x = image.width / 2
        image.anchor_y = image.height / 2
        sprite2 = ActionSprite( image )

        image = pyglet.resource.image('grossinis_sister2.png')
        image.anchor_x = image.width / 2
        image.anchor_y = image.height / 2
        sprite3 = ActionSprite( image )


        self.add( sprite2, (x/4, y/2) )
        self.add( sprite1, (x/2, y/2) )
        self.add( sprite3, (x/(4/3.0), y/2) )

        sprite1.do( Rotate( 360 * 8, 8 ) )

if __name__ == "__main__":
    director.init()
    test_layer = TestLayer ()
    main_scene = cocos.scene.Scene( ColorLayer( 0.0,0.0,1.0,1.0 ), test_layer)
#    main_scene.do( MoveBy( (200,200), 2 ) )
    main_scene.do( Rotate( 360, 2 ) )
    main_scene.do( ScaleTo( 0.5, 1 ) )
    director.run (main_scene)
