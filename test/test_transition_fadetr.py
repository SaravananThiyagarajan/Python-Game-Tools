# This code is so you can run the samples without installing the package
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
#


import cocos
from cocos.director import director
from cocos.actions import *
from cocos.layer import *
from cocos.scenes import *
from cocos.sprite import *
import pyglet

class BackgroundLayer( cocos.layer.Layer ):
    def __init__(self):
        super( BackgroundLayer, self ).__init__()
        self.img = pyglet.resource.image('background_image.png')

    def on_draw( self ):
        self.img.blit(0,0)


if __name__ == "__main__":
    director.init( resizable=True )
    scene1 = cocos.scene.Scene()
    scene2 = cocos.scene.Scene()

    colorl = ColorLayer(32,32,255,255)
    sprite = ActionSprite( 'grossini.png', (320,240) )
    colorl.add( sprite )

    scene1.add( BackgroundLayer(), z=0 )
    scene2.add( colorl, z=0 )

    director.run( FadeTRTransition( scene2, scene1, 2) )
